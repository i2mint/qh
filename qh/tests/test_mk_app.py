"""
Tests for the new qh.mk_app API.
"""

import pytest
from fastapi.testclient import TestClient

from qh import mk_app, AppConfig, RouteConfig, inspect_routes


def test_simple_function():
    """Test exposing a simple function."""

    def add(x: int, y: int) -> int:
        """Add two numbers."""
        return x + y

    app = mk_app([add])
    client = TestClient(app)

    # Test the endpoint
    response = client.post('/add', json={'x': 3, 'y': 5})
    assert response.status_code == 200
    assert response.json() == 8


def test_single_function():
    """Test exposing a single function (not in a list)."""

    def greet(name: str = "World") -> str:
        return f"Hello, {name}!"

    app = mk_app(greet)
    client = TestClient(app)

    # Test with default
    response = client.post('/greet', json={})
    assert response.status_code == 200
    assert response.json() == "Hello, World!"

    # Test with parameter
    response = client.post('/greet', json={'name': 'qh'})
    assert response.status_code == 200
    assert response.json() == "Hello, qh!"


def test_multiple_functions():
    """Test exposing multiple functions."""

    def add(x: int, y: int) -> int:
        return x + y

    def multiply(x: int, y: int) -> int:
        return x * y

    def greet(name: str) -> str:
        return f"Hello, {name}!"

    app = mk_app([add, multiply, greet])
    client = TestClient(app)

    # Test all endpoints
    response = client.post('/add', json={'x': 3, 'y': 5})
    assert response.json() == 8

    response = client.post('/multiply', json={'x': 3, 'y': 5})
    assert response.json() == 15

    response = client.post('/greet', json={'name': 'qh'})
    assert response.json() == "Hello, qh!"


def test_with_app_config():
    """Test with custom app configuration."""

    def add(x: int, y: int) -> int:
        return x + y

    config = AppConfig(
        path_prefix='/api',
        default_methods=['GET', 'POST'],
    )

    app = mk_app([add], config=config)
    client = TestClient(app)

    # Test POST method (GET with JSON body not standard HTTP)
    response = client.post('/api/add', json={'x': 3, 'y': 5})
    assert response.status_code == 200
    assert response.json() == 8

    # Verify path prefix is applied
    assert '/api/add' in [r['path'] for r in inspect_routes(app)]


def test_with_route_config():
    """Test with per-function route configuration."""

    def add(x: int, y: int) -> int:
        return x + y

    app = mk_app({
        add: {'path': '/calculate/add', 'methods': ['POST']},
    })
    client = TestClient(app)

    # Test custom path
    response = client.post('/calculate/add', json={'x': 3, 'y': 5})
    assert response.status_code == 200
    assert response.json() == 8


def test_with_route_config_object():
    """Test with RouteConfig object."""

    def add(x: int, y: int) -> int:
        return x + y

    app = mk_app({
        add: RouteConfig(
            path='/math/add',
            methods=['POST', 'PUT'],
            summary='Add two integers',
        ),
    })
    client = TestClient(app)

    # Test POST
    response = client.post('/math/add', json={'x': 3, 'y': 5})
    assert response.status_code == 200
    assert response.json() == 8

    # Test PUT
    response = client.put('/math/add', json={'x': 3, 'y': 5})
    assert response.status_code == 200
    assert response.json() == 8


def test_missing_required_param():
    """Test that missing required parameters are caught."""

    def add(x: int, y: int) -> int:
        return x + y

    app = mk_app([add])
    client = TestClient(app)

    # Missing parameter
    response = client.post('/add', json={'x': 3})
    assert response.status_code == 422
    assert 'required parameter' in response.json()['detail'].lower()


def test_docstring_extraction():
    """Test that docstrings are used for OpenAPI docs."""

    def add(x: int, y: int) -> int:
        """
        Add two numbers together.

        This is a longer description.
        """
        return x + y

    app = mk_app([add])

    # Check OpenAPI schema
    openapi = app.openapi()
    assert 'Add two numbers together.' in openapi['paths']['/add']['post']['summary']


def test_inspect_routes():
    """Test route inspection."""

    def add(x: int, y: int) -> int:
        return x + y

    def multiply(x: int, y: int) -> int:
        return x * y

    app = mk_app([add, multiply])
    routes = inspect_routes(app)

    # Check we have the routes (plus OpenAPI routes)
    route_paths = [r['path'] for r in routes]
    assert '/add' in route_paths
    assert '/multiply' in route_paths


def test_dict_return():
    """Test returning dictionaries."""

    def get_user(user_id: str) -> dict:
        return {'user_id': user_id, 'name': 'Test User', 'active': True}

    app = mk_app([get_user])
    client = TestClient(app)

    response = client.post('/get_user', json={'user_id': '123'})
    assert response.status_code == 200
    assert response.json() == {
        'user_id': '123',
        'name': 'Test User',
        'active': True,
    }


def test_list_return():
    """Test returning lists."""

    def get_numbers(count: int) -> list:
        return list(range(count))

    app = mk_app([get_numbers])
    client = TestClient(app)

    response = client.post('/get_numbers', json={'count': 5})
    assert response.status_code == 200
    assert response.json() == [0, 1, 2, 3, 4]


def test_none_config():
    """Test that None config values work."""

    def add(x: int, y: int) -> int:
        return x + y

    app = mk_app({add: None})
    client = TestClient(app)

    response = client.post('/add', json={'x': 3, 'y': 5})
    assert response.status_code == 200
    assert response.json() == 8


def test_response_passthrough_returns_unchanged():
    """A function that returns a fastapi.Response bypasses JSON encoding.

    This is the seam reelee uses for PDF export (chunk 9): the endpoint
    returns a Response with raw bytes and a content-type header, qh
    passes it through verbatim.
    """
    from fastapi import Response

    PDF_BYTES = b"%PDF-1.4 fake but valid header"

    def export_pdf() -> Response:
        return Response(
            content=PDF_BYTES,
            media_type="application/pdf",
            headers={
                "content-disposition": 'attachment; filename="picture-book.pdf"'
            },
        )

    app = mk_app([export_pdf])
    client = TestClient(app)
    response = client.post("/export_pdf")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert (
        response.headers["content-disposition"]
        == 'attachment; filename="picture-book.pdf"'
    )
    assert response.content == PDF_BYTES


def test_response_passthrough_supports_streaming():
    """StreamingResponse subclasses also pass through."""
    from fastapi.responses import StreamingResponse

    def stream_text() -> StreamingResponse:
        def gen():
            for chunk in ("hello ", "from ", "qh"):
                yield chunk.encode()

        return StreamingResponse(gen(), media_type="text/plain")

    app = mk_app([stream_text])
    client = TestClient(app)
    response = client.post("/stream_text")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    assert response.text == "hello from qh"


def test_dataclass_return_serializes():
    """A function returning a dataclass serializes (via jsonable_encoder).

    Regression for i2mint/qh#6: JSONResponse uses the stdlib json encoder,
    which only handles dict/list/scalar — a dataclass instance raised
    ``Object of type ... is not JSON serializable`` and 500'd.
    """
    from dataclasses import dataclass

    @dataclass(frozen=True)
    class Point:
        x: int
        y: int

    def make_point(x: int, y: int) -> Point:
        return Point(x=x, y=y)

    app = mk_app([make_point])
    client = TestClient(app)

    response = client.post('/make_point', json={'x': 3, 'y': 5})
    assert response.status_code == 200
    assert response.json() == {'x': 3, 'y': 5}


def test_list_of_dataclasses_serializes():
    """A list of dataclasses serializes — the ef.EfService.search() shape."""
    from dataclasses import dataclass

    @dataclass(frozen=True)
    class Hit:
        label: str
        score: float

    def top_hits() -> list[Hit]:
        return [Hit(label='a', score=0.9), Hit(label='b', score=0.5)]

    app = mk_app([top_hits])
    client = TestClient(app)

    response = client.post('/top_hits', json={})
    assert response.status_code == 200
    assert response.json() == [
        {'label': 'a', 'score': 0.9},
        {'label': 'b', 'score': 0.5},
    ]


def test_rich_types_serialize():
    """datetime and Enum returns also serialize through jsonable_encoder."""
    from datetime import datetime
    from enum import Enum

    class Color(Enum):
        RED = 'red'

    def info() -> dict:
        return {'when': datetime(2026, 5, 21, 12, 0, 0), 'color': Color.RED}

    app = mk_app([info])
    client = TestClient(app)

    response = client.post('/info', json={})
    assert response.status_code == 200
    assert response.json() == {'when': '2026-05-21T12:00:00', 'color': 'red'}


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
