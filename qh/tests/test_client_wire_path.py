"""The path the qh client puts on the wire keeps qh's encoding (qh#41).

``fill_path_params`` escapes a ``.``/``..`` segment as ``%2E``/``%2E%2E``; these
tests check that the escape survives ``requests`` and reaches a real server.
"""

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from qh.client import HttpClient


@pytest.fixture(scope="module")
def recording_server():
    """A local server that records the raw request target of every request."""
    seen = []

    class _Recorder(BaseHTTPRequestHandler):
        def _answer(self):
            seen.append(self.path)
            length = int(self.headers.get("Content-Length") or 0)
            if length:
                self.rfile.read(length)
            body = json.dumps({"ok": True}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        do_GET = do_POST = do_PUT = do_PATCH = do_DELETE = _answer

        def log_message(self, *args):
            pass

    server = HTTPServer(("127.0.0.1", 0), _Recorder)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}", seen
    finally:
        server.shutdown()
        server.server_close()


@pytest.mark.parametrize("method", ["GET", "POST", "PUT", "PATCH", "DELETE"])
@pytest.mark.parametrize(
    "template, value, wire",
    [
        ("/items/{x}", "..", "/api/items/%2E%2E"),
        ("/items/{x}", ".", "/api/items/%2E"),
        ("/files/{p:path}", "a/../b", "/api/files/a/%2E%2E/b"),
        ("/files/{p:path}", "./x", "/api/files/%2E/x"),
    ],
)
def test_dot_segment_escape_reaches_the_wire(
    recording_server, method, template, value, wire
):
    base_url, seen = recording_server
    client = HttpClient(base_url + "/api")
    client.add_function("f", template, method)
    name = template.split("{")[1].split("}")[0].split(":")[0]
    client.f(**{name: value})
    assert seen[-1].split("?")[0] == wire


def test_query_string_and_other_escapes_survive(recording_server):
    base_url, seen = recording_server
    client = HttpClient(base_url + "/api")
    client.add_function("f", "/items/{x}", "GET")
    client.f(x="..", q="a b&c")
    assert seen[-1] == "/api/items/%2E%2E?q=a+b%26c"
    client.f(x="a/b c", q="1")
    assert seen[-1] == "/api/items/a%2Fb%20c?q=1"


def test_ordinary_values_are_sent_as_requests_sends_them(recording_server):
    base_url, seen = recording_server
    client = HttpClient(base_url + "/api")
    client.add_function("f", "/files/{p:path}", "GET")
    client.f(p="a/b.c/..d")
    assert seen[-1] == "/api/files/a/b.c/..d"
