"""Opt-in 415 for a body that is not application/json (#31)."""

from fastapi.testclient import TestClient

from qh import mk_app
from qh.config import AppConfig, RouteConfig


def start(query: str):
    return {"query": query}


BODY = '{"query": "x"}'


def _post(c, ctype):
    return c.post("/start", content=BODY, headers={"Content-Type": ctype})


def test_default_accepts_any_content_type():
    c = TestClient(mk_app([start]))
    assert _post(c, "text/plain").status_code == 200


def test_app_flag_rejects_non_json_bodies():
    c = TestClient(mk_app([start], config=AppConfig(require_json_content_type=True)))
    assert _post(c, "text/plain").status_code == 415
    assert _post(c, "application/x-www-form-urlencoded").status_code == 415
    assert _post(c, "application/json").json() == {"query": "x"}
    assert _post(c, "application/json; charset=utf-8").status_code == 200
    assert c.post("/start", json={"query": "y"}).status_code == 200


def test_route_setting_overrides_app():
    app = mk_app(
        {start: RouteConfig(require_json_content_type=True)},
    )
    assert _post(TestClient(app), "text/plain").status_code == 415
    app = mk_app(
        {start: RouteConfig(require_json_content_type=False)},
        config=AppConfig(require_json_content_type=True),
    )
    assert _post(TestClient(app), "text/plain").status_code == 200
