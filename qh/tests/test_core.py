"""Test core.py functionality."""

import pytest
from fastapi.testclient import TestClient
from qh.base import mk_fastapi_app  # Adjust import based on your package structure
import asyncio


# Sample functions for testing
def sync_greeter(greeting: str, name: str = 'world') -> str:
    """A synchronous greeter function."""
    return f"{greeting}, {name}!"


async def async_greeter(greeting: str, name: str = 'world') -> str:
    """An asynchronous greeter function."""
    await asyncio.sleep(0.1)  # Simulate async operation
    return f"{greeting}, {name}!"


def no_args_func() -> str:
    """A function with no arguments."""
    return "No arguments needed"


def error_prone_func():
    """A function that raises an exception."""
    raise ValueError("Something went wrong")


# Fixtures
@pytest.fixture
def app_sync():
    """Fixture for a FastAPI app with a synchronous function."""
    return mk_fastapi_app([sync_greeter])


@pytest.fixture
def client_sync(app_sync):
    """Test client for the synchronous app."""
    return TestClient(app_sync)


@pytest.fixture
def app_async():
    """Fixture for a FastAPI app with an asynchronous function."""
    return mk_fastapi_app([async_greeter])


@pytest.fixture
def client_async(app_async):
    """Test client for the asynchronous app."""
    return TestClient(app_async)


@pytest.fixture
def app_no_args():
    """Fixture for a FastAPI app with a no-args function."""
    return mk_fastapi_app([no_args_func])


@pytest.fixture
def client_no_args(app_no_args):
    """Test client for the no-args app."""
    return TestClient(app_no_args)


@pytest.fixture
def app_error():
    """Fixture for a FastAPI app with an error-prone function."""
    return mk_fastapi_app([error_prone_func])


@pytest.fixture
def client_error(app_error):
    """Test client for the error-prone app."""
    return TestClient(app_error)


# Test Functions
def test_configuration_merging(client_sync):
    """Test that default configurations are applied correctly."""
    response = client_sync.post(
        "/sync_greeter", json={"greeting": "Hello", "name": "Alice"}
    )
    assert response.status_code == 200
    assert response.json() == "Hello, Alice!"


def test_default_input_mapper(client_sync):
    """Test that the default input mapper extracts arguments from the request body."""
    response = client_sync.post("/sync_greeter", json={"greeting": "Hi", "name": "Bob"})
    assert response.status_code == 200
    assert response.json() == "Hi, Bob!"


def test_default_output_mapper(client_sync):
    """Test that the default output mapper serializes the output to JSON."""
    response = client_sync.post("/sync_greeter", json={"greeting": "Bonjour"})
    assert response.status_code == 200
    assert response.json() == "Bonjour, world!"


def test_sync_function_wrapping(client_sync):
    """Test wrapping of a synchronous function."""
    response = client_sync.post("/sync_greeter", json={"greeting": "Hola"})
    assert response.status_code == 200
    assert response.json() == "Hola, world!"


def test_async_function_wrapping(client_async):
    """Test wrapping of an asynchronous function."""
    response = client_async.post("/async_greeter", json={"greeting": "Hola"})
    assert response.status_code == 200
    assert response.json() == "Hola, world!"


def test_route_creation(app_sync):
    """Test that routes are created with the correct paths."""
    routes = [route.path for route in app_sync.routes]
    assert "/sync_greeter" in routes


def test_error_handling(client_error):
    """Test that errors are handled correctly."""
    response = client_error.post("/error_prone_func", json={})
    assert response.status_code == 500
    assert "Something went wrong" in response.text


def test_no_args_function(client_no_args):
    """Test a function with no arguments."""
    response = client_no_args.post("/no_args_func", json={})
    assert response.status_code == 200
    assert response.json() == "No arguments needed"


# Optional: Run pytest directly if this file is executed
if __name__ == "__main__":
    pytest.main([__file__])
