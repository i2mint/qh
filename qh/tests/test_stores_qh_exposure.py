"""What clients of ``qh.stores_qh`` apps see: exception text, and whose mall."""

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from qh.stores_qh import add_mall_access, add_store_access

SECRET = "/srv/secret/path"


class _FailingStore(dict):
    def __setitem__(self, k, v):
        raise ValueError(SECRET)

    def __delitem__(self, k):
        raise ValueError(SECRET)

    def __contains__(self, k):
        raise ValueError(SECRET)

    def __len__(self):
        raise ValueError(SECRET)


def _failing_get_mall(user_id):
    if user_id == "boom":
        raise RuntimeError(SECRET)
    return {"s": _FailingStore()}


def _mall_client(**kwargs):
    return TestClient(
        add_mall_access(_failing_get_mall, write=True, delete=True, **kwargs)
    )


@pytest.mark.parametrize(
    "method, path, kw",
    [
        ("put", "/users/u/mall/s/k", {"json": {"value": 1}}),
        ("delete", "/users/u/mall/s/k", {}),
        ("get", "/users/boom/mall", {}),
        ("get", "/users/boom/mall/s", {}),
    ],
)
def test_mall_errors_hide_exception_text_by_default(method, path, kw):
    r = getattr(_mall_client(), method)(path, **kw)
    assert r.status_code in (400, 404)
    assert SECRET not in r.text


def test_mall_errors_expose_errors_restores_text():
    client = _mall_client(expose_errors=True)
    r = client.put("/users/u/mall/s/k", json={"value": 1})
    assert r.status_code == 400 and SECRET in r.json()["detail"]
    assert SECRET in client.get("/users/boom/mall").json()["detail"]


def test_store_access_hides_get_obj_and_operation_errors():
    def get_obj(user_id):
        if user_id == "boom":
            raise RuntimeError(SECRET)
        return _FailingStore()

    methods = {"__iter__": None, "__contains__": None, "__len__": None}
    client = TestClient(
        add_store_access(get_obj, methods=methods, base_path="/s/{user_id}")
    )
    r = client.get("/s/boom")
    assert r.status_code == 404 and SECRET not in r.text
    assert r.json()["detail"] == "Object not found for: boom"
    for path in ("/s/u/k/exists", "/s/u/$count"):
        r = client.get(path)
        assert r.status_code == 400 and SECRET not in r.text

    client = TestClient(
        add_store_access(
            get_obj, methods=methods, base_path="/s/{user_id}", expose_errors=True
        )
    )
    assert SECRET in client.get("/s/boom").json()["detail"]


def test_not_found_messages_echo_only_the_client_key():
    malls = {"u": {"s": {}}}
    client = TestClient(add_mall_access(malls.get))
    assert client.get("/users/u/mall/s/k").json()["detail"] == "Item not found: k"
    assert (
        client.get("/users/nobody/mall").json()["detail"]
        == "Mall not found for user: nobody"
    )


def _malls():
    return {"alice": {"notes": {"a": 1}}, "bob": {"notes": {"b": 2}}}


@pytest.mark.parametrize("is_async", [False, True])
def test_caller_hook_restricts_every_route_to_own_mall(is_async):
    malls = _malls()
    calls = []

    def get_mall(user_id):
        calls.append(user_id)
        return malls.get(user_id)

    def who(request):
        return request.headers.get("x-user")

    async def awho(request):
        return who(request)

    app = add_mall_access(
        get_mall, write=True, delete=True, caller=awho if is_async else who
    )
    client = TestClient(app)
    alice = {"x-user": "alice"}

    assert client.get("/users/alice/mall/notes/a", headers=alice).json() == {"value": 1}
    calls.clear()
    for method, path, kw in [
        ("get", "/users/bob/mall", {}),
        ("get", "/users/bob/mall/notes", {}),
        ("get", "/users/bob/mall/notes/b", {}),
        ("put", "/users/bob/mall/notes/b", {"json": {"value": 3}}),
        ("delete", "/users/bob/mall/notes/b", {}),
    ]:
        assert getattr(client, method)(path, headers=alice, **kw).status_code == 403
        assert getattr(client, method)(path, **kw).status_code == 401
    assert calls == []  # rejected before the mall was even looked up
    assert malls["bob"]["notes"] == {"b": 2}


def test_caller_may_raise_its_own_http_exception():
    def caller(request):
        raise HTTPException(status_code=401, detail="bad token")

    client = TestClient(add_mall_access(_malls().get, caller=caller))
    r = client.get("/users/alice/mall")
    assert r.status_code == 401 and r.json()["detail"] == "bad token"


def test_no_caller_keeps_open_access():
    client = TestClient(add_mall_access(_malls().get))
    assert client.get("/users/bob/mall/notes/b").json() == {"value": 2}
