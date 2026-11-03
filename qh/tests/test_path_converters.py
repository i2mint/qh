"""Path parameters declared with a converter (``{name:path}``) bind (qh#26)."""

from fastapi.testclient import TestClient

from qh import mk_app
from qh.paths import fill_path_params, path_param_names


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
    assert fill_path_params("/a/{x:int}", lambda n: "{" + n + "}") == "/a/{x}"
