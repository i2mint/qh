"""Custom ``methods=`` entries of ``add_store_access`` (any name beyond the six dunders)."""

from fastapi.testclient import TestClient

from qh.stores_qh import add_store_access

SECRET = "/srv/secret/path"


class _Store(dict):
    def get(self, key=None):
        if key is None:
            return "no key"
        return super().__getitem__(key)

    def boom(self):
        raise ValueError(SECRET)

    def pair(self, a):
        return [a]


def _client(base_path, path_params=None, **methods):
    stores = {("u", "s"): _Store(a=1), ("u",): _Store(a=1)}
    dispatch = {"path_params": path_params} if path_params else None
    app = add_store_access(
        lambda *ids: stores[tuple(ids)],
        methods=methods,
        get_obj_dispatch=dispatch,
        base_path=base_path,
    )
    return TestClient(app)


def test_custom_method_with_optional_item_key_query():
    c = _client("/users/{user_id}/s", get=dict(path="/get"))
    assert c.get("/users/u/s/get").json() == {"value": "no key"}
    assert c.get("/users/u/s/get", params={"item_key": "a"}).json() == {"value": 1}


def test_custom_method_honours_two_path_params():
    c = _client(
        "/users/{user_id}/mall/{store_key}",
        path_params=["user_id", "store_key"],
        get=dict(path="/get"),
    )
    assert c.get("/users/u/mall/s/get", params={"item_key": "a"}).json() == {"value": 1}


def test_custom_method_with_route_param():
    c = _client("/users/{user_id}/s", pair=dict(path="/pair/{item_key}"))
    assert c.get("/users/u/s/pair/x").json() == {"value": ["x"]}


def test_custom_method_failures_use_the_error_policy():
    c = _client("/users/{user_id}/s", boom=dict(path="/boom"), get=dict(path="/get"))
    r = c.get("/users/u/s/boom")
    assert r.status_code == 400 and SECRET not in r.text
    assert c.get("/users/u/s/get", params={"item_key": "zz"}).status_code == 404
