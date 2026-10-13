"""``GET /tasks/{task_id}/result``: completed, failed, pending and timed-out tasks,
and the legacy name-keyed task routes."""

import threading
import time

from fastapi import FastAPI
from fastapi.testclient import TestClient

from qh import mk_app
from qh.async_endpoints import add_global_task_endpoints, add_task_endpoints
from qh.async_tasks import get_task_manager

POLL_INTERVAL = 0.05
POLL_TIMEOUT = 5


def work(x: int) -> int:
    return x * 2


def failing_work(x: int) -> int:
    raise RuntimeError("cannot connect to postgres://admin:hunter2@db/prod")


_release = threading.Event()


def gated_work(x: int) -> int:
    _release.wait(POLL_TIMEOUT)
    return x


def _submit(client, func_name, x=1):
    return client.post(f"/{func_name}?async=true", json={"x": x}).json()["task_id"]


def _wait_done(client, task_id):
    deadline = time.time() + POLL_TIMEOUT
    while time.time() < deadline:
        status = client.get(f"/tasks/{task_id}/status").json()["status"]
        if status in ("completed", "failed"):
            return status
        time.sleep(POLL_INTERVAL)
    raise TimeoutError(task_id)


def test_completed_result():
    client = TestClient(mk_app([work], async_funcs=["work"]))
    task_id = _submit(client, "work", 21)
    response = client.get(f"/tasks/{task_id}/result", params={"wait": True})
    assert response.status_code == 200
    assert response.json() == {"task_id": task_id, "status": "completed", "result": 42}


def test_failed_result_is_500_without_the_error_text():
    client = TestClient(mk_app([failing_work], async_funcs=["failing_work"]))
    task_id = _submit(client, "failing_work")
    assert _wait_done(client, task_id) == "failed"
    response = client.get(f"/tasks/{task_id}/result")
    assert response.status_code == 500
    assert response.json()["status"] == "failed"
    assert "hunter2" not in response.text


def test_pending_result_is_202_and_wait_can_time_out():
    _release.clear()
    try:
        client = TestClient(mk_app([gated_work], async_funcs=["gated_work"]))
        task_id = _submit(client, "gated_work")
        response = client.get(f"/tasks/{task_id}/result")
        assert response.status_code == 202
        assert response.json()["message"] == "Task not yet completed"
        response = client.get(
            f"/tasks/{task_id}/result", params={"wait": True, "timeout": 0.2}
        )
        assert response.status_code == 408
    finally:
        _release.set()


def test_unknown_task_is_404_everywhere():
    client = TestClient(mk_app([work], async_funcs=["work"]))
    for method, path in [
        ("get", "/tasks/nope/status"),
        ("get", "/tasks/nope/result"),
        ("get", "/tasks/nope"),
        ("delete", "/tasks/nope"),
    ]:
        assert getattr(client, method)(path).status_code == 404


def test_delete_task():
    client = TestClient(mk_app([work], async_funcs=["work"]))
    task_id = _submit(client, "work")
    _wait_done(client, task_id)
    assert client.delete(f"/tasks/{task_id}").json() == {
        "task_id": task_id,
        "status": "deleted",
    }


def test_legacy_name_keyed_task_routes(monkeypatch):
    """``add_task_endpoints`` / ``add_global_task_endpoints`` without configs use the
    process-wide registry (``get_task_manager``), here emptied of other tests' tasks."""
    import qh.async_tasks

    monkeypatch.setattr(qh.async_tasks, "_task_managers", {})
    func_name = "legacy_registry_work"
    manager = get_task_manager(func_name)
    task_id = manager.create_task(work, kwargs={"x": 4})
    manager.get_result(task_id, wait=True, timeout=POLL_TIMEOUT)
    app = FastAPI()
    add_task_endpoints(app, func_name)
    add_global_task_endpoints(app)
    client = TestClient(app)
    assert client.get(f"/tasks/{task_id}/result").json()["result"] == 8
    listed = {t["task_id"]: t for t in client.get("/tasks/").json()["tasks"]}
    assert listed[task_id]["function"] == func_name


def test_waiting_for_a_result_does_not_stall_other_requests():
    """``?wait=true`` used to poll with ``time.sleep`` on the event loop, so every
    other request waited as long as the task did."""
    import asyncio

    import httpx

    _release.clear()
    app = mk_app([gated_work, work], async_funcs=["gated_work"])

    async def go():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://t") as c:
            r = await c.post("/gated_work?async=true", json={"x": 1})
            task_id = r.json()["task_id"]
            started = time.monotonic()
            waiting = asyncio.create_task(
                c.get(f"/tasks/{task_id}/result", params={"wait": True, "timeout": 5})
            )
            await asyncio.sleep(0.2)  # the waiter is now waiting
            other = await c.post("/work", json={"x": 3})
            other_took = time.monotonic() - started
            _release.set()
            return other.json(), other_took, (await waiting).json()

    try:
        other, other_took, waited = asyncio.run(go())
    finally:
        _release.set()
    assert other == 6 and other_took < 2  # the gate would hold it 5s
    assert waited["result"] == 1
