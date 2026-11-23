"""Optional query params are converted (#29); sync funcs don't block the loop (#30)."""

import threading
import time
from typing import Optional

from fastapi.testclient import TestClient

from qh import mk_app


def test_optional_int_query_converted():
    def get_f(line: int | None = None, k: Optional[float] = None):
        return {"line": type(line).__name__, "k": type(k).__name__}

    c = TestClient(mk_app({get_f: {"path": "/f", "methods": ["GET"]}}))
    r = c.get("/f", params={"line": "0", "k": "1.5"})
    assert r.json() == {"line": "int", "k": "float"}
    assert c.get("/f").json() == {"line": "NoneType", "k": "NoneType"}
    assert c.get("/f", params={"line": "abc"}).status_code == 422


def test_sync_func_runs_off_event_loop():
    main = threading.get_ident()

    def get_where():
        return {"same": threading.get_ident() == main}

    assert TestClient(mk_app({get_where: {"path": "/where", "methods": ["GET"]}})).get("/where").json() == {"same": False}


def test_client_url_join_and_dot_values():
    from qh.paths import fill_path_params

    assert fill_path_params("/items/{x}", {"x": ".."}) == "/items/%2E%2E"
    assert fill_path_params("/items/{x}", {"x": "."}) == "/items/%2E"
    assert fill_path_params("/items/{x}", {"x": "a.b"}) == "/items/a.b"


def test_dot_segments_inside_a_path_value_are_escaped():
    """A path value's own '.'/'..' segments, not only a whole-value one (qh#39)."""
    from qh.paths import fill_path_params

    assert fill_path_params("/files/{p:path}", {"p": "a/../b"}) == "/files/a/%2E%2E/b"
    assert fill_path_params("/files/{p:path}", {"p": "./x"}) == "/files/%2E/x"
    assert fill_path_params("/files/{p:path}", {"p": "a/b.c/..d"}) == "/files/a/b.c/..d"
