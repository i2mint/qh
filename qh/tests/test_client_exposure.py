"""What HTTP clients can see: error text, private attributes, other callers' tasks."""

import time

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from qh import mk_app
from qh.async_tasks import TaskConfig
from qh.base import mk_fastapi_app as base_mk_fastapi_app

SECRET = "postgres://admin:hunter2@db/prod"
POLL_INTERVAL = 0.05
POLL_TIMEOUT = 5


def leaky(x: int) -> int:
    raise RuntimeError(f"cannot connect to {SECRET}")


class User:
    def __init__(self):
        self.name = "alice"
        self._token = "tok"
        self.__password_hash = "hash"


def get_user() -> User:
    return User()


def work(x: int) -> int:
    return x * 2


def failing_work(x: int) -> int:
    raise RuntimeError(f"cannot connect to {SECRET}")


def _owner_from_header(request) -> str:
    user = request.headers.get("X-User")
    if not user:
        raise HTTPException(status_code=401, detail="Who are you?")
    return user


def _wait_done(client, task_id, *, headers=None):
    deadline = time.time() + POLL_TIMEOUT
    while time.time() < deadline:
        info = client.get(f"/tasks/{task_id}/status", headers=headers).json()
        if info["status"] in ("completed", "failed"):
            return info
        time.sleep(POLL_INTERVAL)
    raise TimeoutError(task_id)


# --- error text ---------------------------------------------------------------


def test_exception_text_not_sent_by_default(caplog):
    client = TestClient(mk_app([leaky]))
    response = client.post("/leaky", json={"x": 1})
    assert response.status_code == 500
    detail = response.json()["detail"]
    assert SECRET not in detail and "error id" in detail
    # ... but it is logged server-side, under the same error id
    error_id = detail.split("error id: ")[1].rstrip(")")
    assert any(error_id in r.getMessage() for r in caplog.records)
    assert any(SECRET in str(r.exc_info[1]) for r in caplog.records if r.exc_info)


@pytest.mark.parametrize(
    "kwargs", [dict(expose_errors=True), dict(config={"expose_errors": True})]
)
def test_expose_errors_opt_in(kwargs):
    client = TestClient(mk_app([leaky], **kwargs))
    detail = client.post("/leaky", json={"x": 1}).json()["detail"]
    assert detail == f"Error in leaky: cannot connect to {SECRET}"


def test_base_mk_fastapi_app_error_text():
    response = TestClient(base_mk_fastapi_app([leaky])).post("/leaky", json={"x": 1})
    assert response.status_code == 500 and SECRET not in response.text
    app = base_mk_fastapi_app([leaky], expose_errors=True)
    assert SECRET in TestClient(app).post("/leaky", json={"x": 1}).text


# --- private attributes in the __dict__ fallback --------------------------------


def test_dict_fallback_drops_private_attributes():
    client = TestClient(mk_app([get_user]))
    assert client.post("/get_user", json={}).json() == {"name": "alice"}


# --- tasks ----------------------------------------------------------------------


def test_global_task_listing_is_opt_in():
    client = TestClient(mk_app([work], async_funcs=["work"]))
    assert client.get("/tasks/").status_code in (404, 405)


def test_failed_task_hides_error_and_traceback_by_default():
    client = TestClient(mk_app([failing_work], async_funcs=["failing_work"]))
    task_id = client.post("/failing_work?async=true", json={"x": 1}).json()["task_id"]
    _wait_done(client, task_id)
    for path in (f"/tasks/{task_id}", f"/tasks/{task_id}/result"):
        response = client.get(path)
        assert SECRET not in response.text and "Traceback" not in response.text
        assert "traceback" not in response.json()


def test_global_listing_never_sends_tracebacks():
    app = mk_app(
        [failing_work],
        async_funcs=["failing_work"],
        global_task_endpoints=True,
    )
    client = TestClient(app)
    task_id = client.post("/failing_work?async=true", json={"x": 1}).json()["task_id"]
    _wait_done(client, task_id)
    listing = client.get("/tasks/")
    assert listing.status_code == 200
    assert task_id in {t["task_id"] for t in listing.json()["tasks"]}
    assert SECRET not in listing.text and "Traceback" not in listing.text


def test_task_owner_restricts_every_task_endpoint():
    config = TaskConfig(task_owner=_owner_from_header)
    app = mk_app(
        [work],
        async_funcs=["work"],
        async_config=config,
        global_task_endpoints=True,
    )
    client = TestClient(app)
    alice, bob = {"X-User": "alice"}, {"X-User": "bob"}

    # unauthenticated callers cannot even submit
    assert client.post("/work?async=true", json={"x": 2}).status_code == 401

    task_id = client.post("/work?async=true", json={"x": 2}, headers=alice).json()[
        "task_id"
    ]
    _wait_done(client, task_id, headers=alice)

    for path in ("", "/status", "/result"):
        assert client.get(f"/tasks/{task_id}{path}", headers=bob).status_code == 404
        assert client.get(f"/tasks/{task_id}{path}", headers=alice).status_code == 200
    assert client.get(f"/tasks/{task_id}/result", headers=alice).json()["result"] == 4

    assert client.get("/tasks/", headers=bob).json()["tasks"] == []
    alice_tasks = client.get("/tasks/", headers=alice).json()["tasks"]
    assert [t["task_id"] for t in alice_tasks] == [task_id]
    assert "owner" not in alice_tasks[0]

    assert client.delete(f"/tasks/{task_id}", headers=bob).status_code == 404
    assert client.delete(f"/tasks/{task_id}", headers=alice).status_code == 200
