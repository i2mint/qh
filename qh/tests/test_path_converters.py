"""Path parameters declared with a converter (``{name:path}``) bind (qh#26).

Also the round trips through every consumer of a route template: the OpenAPI
export, the Python client built from it, and the JS/TS clients.
"""

import json
import shutil
import subprocess
import uuid

import pytest
from fastapi.testclient import TestClient

from qh import export_openapi, export_ts_client, mk_app
from qh.client import mk_client_from_app
from qh.jsclient import export_js_client
from qh.paths import fill_path_params, path_format, path_param_names


def make_ambient(environment: str, seconds: int = 5) -> dict:
    return {"environment": environment, "seconds": seconds}


def lookup(character: str) -> str:
    return character


def _client():
    app = mk_app(
        {
            make_ambient: {
                "path": "/environments/{environment:path}/ambient",
                "methods": ["POST"],
            },
            lookup: {"path": "/characters/{character:path}", "methods": ["GET"]},
        }
    )
    return TestClient(app)


def test_post_route_with_a_path_converter_mid_path_receives_slashes():
    client = _client()
    for name in ["Diner", "Back Room", "INT./EXT. DINER"]:
        r = client.post(f"/environments/{name}/ambient", json={"seconds": 7})
        assert r.status_code == 200, (name, r.text)
        assert r.json() == {"environment": name, "seconds": 7}


def test_percent_encoded_slash_reaches_the_handler_decoded():
    r = _client().post("/environments/INT.%2FEXT.%20DINER/ambient", json={})
    assert r.status_code == 200, r.text
    assert r.json()["environment"] == "INT./EXT. DINER"


def test_get_route_with_a_trailing_path_converter():
    r = _client().get("/characters/AC/DC")
    assert r.status_code == 200, r.text
    assert r.json() == "AC/DC"


def test_path_helpers_understand_converters():
    assert path_param_names("/a/{x:path}/b/{y}") == ["x", "y"]
    assert path_param_names("") == []
    assert fill_path_params("/a/{x:path}/{y}", {"x": "p/q"}) == "/a/p/q/{y}"
    assert path_format("/a/{x:int}") == "/a/{x}"


def test_path_helpers_treat_none_and_empty_alike():
    for empty in (None, ""):
        assert path_param_names(empty) == []
        assert path_format(empty) == ""
        assert fill_path_params(empty, {"x": 1}) == ""


def test_path_helpers_reject_what_the_router_rejects():
    with pytest.raises(ValueError):
        path_param_names("/a/{x:nonsense}")
    with pytest.raises(ValueError):
        path_param_names("/a/{x}/{x}")


def test_fill_path_params_encodes_reserved_characters():
    value = "a?b#c/d$&e f"
    assert fill_path_params("/s/{s}", {"s": value}) == "/s/a%3Fb%23c%2Fd%24%26e%20f"
    assert fill_path_params("/s/{s:path}", {"s": value}) == "/s/a%3Fb%23c/d%24%26e%20f"
    assert fill_path_params("/s/{s}", {"s": value}, quote=False) == "/s/" + value


# --- round trips through the OpenAPI export and the generated clients -----------

AWKWARD = "a?b#c/d$&e f"


def square(n: int) -> int:
    return n * n


def ident(u: uuid.UUID) -> str:
    return str(u)


def echo(s: str) -> str:
    return s


def _converter_app():
    return mk_app(
        {
            square: {"path": "/n/{n:int}", "methods": ["GET"]},
            ident: {"path": "/u/{u:uuid}", "methods": ["GET"]},
            echo: {"path": "/s/{s:path}", "methods": ["GET"]},
        }
    )


def test_openapi_keys_converter_routes_by_their_converter_free_path():
    spec = export_openapi(_converter_app(), include_python_metadata=True)
    paths = spec["paths"]
    assert {"/n/{n}", "/u/{u}", "/s/{s}"} <= set(paths)
    assert not [p for p in paths if ":" in p], list(paths)
    for path, name in [("/n/{n}", "square"), ("/u/{u}", "ident"), ("/s/{s}", "echo")]:
        assert paths[path]["get"]["x-python-signature"]["name"] == name


def test_python_client_round_trips_converter_routes():
    client = mk_client_from_app(_converter_app())
    assert client.square(n=7) == 49
    u = uuid.uuid4()
    assert client.ident(u=u) == str(u)
    assert client.echo(s=AWKWARD) == AWKWARD


def test_ts_client_takes_the_path_parameter_and_encodes_it():
    spec = export_openapi(_converter_app(), include_python_metadata=True)
    ts = export_ts_client(spec)
    assert "async square(n: number): Promise<number>" in ts
    assert "url.replace('{n}', () => encodeURIComponent(String(n)))" in ts
    assert "url.replace('{s}', () => encodeURIComponent(String(s)))" in ts
    assert ":int}" not in ts and ":path}" not in ts


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_js_client_url_reaches_the_handler_intact(tmp_path):
    """Run the generated JS: its URL, sent to the app, returns the value unchanged."""
    app = _converter_app()
    js = export_js_client(
        export_openapi(app, include_python_metadata=True), base_url=""
    )
    script = tmp_path / "client.mjs"
    script.write_text(
        js
        + "\nconst urls = [];\n"
        + "globalThis.fetch = async (url) => {"
        + " urls.push(url); return { ok: true, json: async () => null }; };\n"
        + "const c = new ApiClient('');\n"
        + f"await c.echo({json.dumps(AWKWARD)});\n"
        + "await c.square(7);\n"
        + "console.log(JSON.stringify(urls));\n"
    )
    out = subprocess.run(
        ["node", str(script)], capture_output=True, text=True, check=True
    ).stdout
    echo_url, square_url = json.loads(out)
    client = TestClient(app)
    assert client.get(echo_url).json() == AWKWARD
    assert client.get(square_url).json() == 49
