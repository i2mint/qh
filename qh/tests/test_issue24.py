"""Path param conversion, GET on GET+POST routes, and error_map (#24)."""

from fastapi.testclient import TestClient

from qh import mk_app
from qh.config import AppConfig, RouteConfig


def g(item: int, k: int = 3):
    return {"item": item, "t": type(item).__name__, "k": k}


def test_path_param_is_converted_and_bad_value_is_422():
    app = mk_app({g: RouteConfig(path="/g/{item}", methods=["GET"])})
    c = TestClient(app)
    assert c.get("/g/5").json() == {"item": 5, "t": "int", "k": 3}
    assert c.get("/g/zz").status_code == 422
    assert c.get("/g/5?k=zz").status_code == 422


def test_get_on_get_post_route_reads_query():
    app = mk_app({g: RouteConfig(path="/g/{item}", methods=["GET", "POST"])})
    c = TestClient(app)
    assert c.get("/g/5?k=2").json()["k"] == 2
    assert c.post("/g/5", json={"k": 4}).json() == {"item": 5, "t": "int", "k": 4}


def _boom(kind: str):
    if kind == "key":
        raise KeyError("secret-id")
    if kind == "val":
        raise ValueError("bad")
    raise RuntimeError("x")


def test_error_map_app_and_route_level():
    cfg = AppConfig(error_map={KeyError: 404})
    app = mk_app(
        {_boom: RouteConfig(methods=["POST"], error_map={ValueError: 422})},
        config=cfg,
    )
    c = TestClient(app, raise_server_exceptions=False)
    r = c.post("/_boom", json={"kind": "key"})
    assert r.status_code == 404 and "secret-id" not in r.text
    assert c.post("/_boom", json={"kind": "val"}).status_code == 422
    assert c.post("/_boom", json={"kind": "other"}).status_code == 500


def test_error_map_text_only_with_expose_errors():
    app = mk_app(
        {_boom: RouteConfig(methods=["POST"])},
        config=AppConfig(error_map={KeyError: 404}),
        expose_errors=True,
    )
    r = TestClient(app).post("/_boom", json={"kind": "key"})
    assert r.status_code == 404 and "secret-id" in r.text


def test_openapi_documents_get_params_as_query_on_get_post_route():
    from qh.openapi import export_openapi

    app = mk_app({g: RouteConfig(path="/g/{item}", methods=["GET", "POST"])})
    spec = export_openapi(app, include_python_metadata=False)
    get_params = {p["name"]: p["in"] for p in spec["paths"]["/g/{item}"]["get"]["parameters"]}
    assert get_params.get("k") == "query" and get_params.get("item") == "path"
    assert "requestBody" not in spec["paths"]["/g/{item}"]["get"]


def test_unknown_status_in_error_map_does_not_crash():
    app = mk_app(
        {_boom: RouteConfig(methods=["POST"], error_map={KeyError: 499})},
    )
    r = TestClient(app, raise_server_exceptions=False).post("/_boom", json={"kind": "key"})
    assert r.status_code == 499
