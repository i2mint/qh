"""Test add_store_access functionality."""

from fastapi import FastAPI
from fastapi.testclient import TestClient
from qh.stores_qh import add_store_access, StoreValue, DEFAULT_METHODS


def test_add_store_access_basic():
    """Test basic functionality of add_store_access."""
    mock_store = {'key1': 'value1', 'key2': 'value2'}

    def mock_get_obj(user_id: str):
        return mock_store if user_id == "test_user" else None

    app = add_store_access(mock_get_obj, base_path="/users/{user_id}/store")
    client = TestClient(app)

    # Test listing keys
    response = client.get("/users/test_user/store")
    assert response.status_code == 200
    assert sorted(response.json()) == sorted(['key1', 'key2'])

    # Test getting an item
    response = client.get("/users/test_user/store/key1")
    assert response.status_code == 200
    assert response.json() == {"value": "value1"}


def test_add_store_access_write_delete():
    """Test write and delete operations with add_store_access."""
    mock_store = {'key1': 'value1', 'key2': 'value2'}

    def mock_get_obj(user_id: str):
        return mock_store

    # Use methods instead of write/delete flags
    methods = {
        "__iter__": None,
        "__getitem__": None,
        "__setitem__": None,
        "__delitem__": None,
    }

    app = add_store_access(
        mock_get_obj, base_path="/users/{user_id}/store", methods=methods
    )
    client = TestClient(app)

    # Test set item
    response = client.put("/users/test_user/store/key3", json={"value": "value3"})
    assert response.status_code == 200
    assert response.json()["message"] == "Item set successfully"
    assert mock_store['key3'] == "value3"

    # Test update item
    response = client.put("/users/test_user/store/key1", json={"value": "updated"})
    assert response.status_code == 200
    assert mock_store['key1'] == "updated"

    # Test delete item
    response = client.delete("/users/test_user/store/key2")
    assert response.status_code == 200
    assert response.json()["message"] == "Item deleted successfully"
    assert 'key2' not in mock_store


def test_add_store_access_custom_methods():
    """Test add_store_access with custom method configurations."""
    mock_store = {'key1': 'value1', 'key2': 'value2'}

    def mock_get_obj(user_id: str):
        return mock_store

    # Define custom methods
    custom_methods = {
        "__iter__": {
            "path": "/all_keys",
            "method": "get",
            "description": "Get all keys",
        },
        "__getitem__": {
            "path": "/get/{item_key}",
            "method": "get",
            "description": "Get item by key",
        },
    }

    app = add_store_access(
        mock_get_obj, base_path="/api/{user_id}", methods=custom_methods
    )
    client = TestClient(app)

    # Test custom paths
    response = client.get("/api/test_user/all_keys")
    assert response.status_code == 200
    assert sorted(response.json()) == sorted(['key1', 'key2'])

    response = client.get("/api/test_user/get/key1")
    assert response.status_code == 200
    assert response.json() == {"value": "value1"}


def test_add_store_access_error_handling():
    """Test error handling in add_store_access."""
    mock_store = {'key1': 'value1', 'key2': 'value2'}

    def mock_get_obj(user_id: str):
        if user_id != "test_user":
            return None
        return mock_store

    app = add_store_access(mock_get_obj, base_path="/users/{user_id}/store")
    client = TestClient(app)

    # Test non-existent user
    response = client.get("/users/unknown_user/store")
    assert response.status_code == 404

    # Test non-existent key
    response = client.get("/users/test_user/store/unknown_key")
    assert response.status_code == 404


def test_add_store_access_with_existing_app():
    """Test adding store access to an existing FastAPI app."""
    mock_store = {'key1': 'value1'}

    def mock_get_obj(user_id: str):
        return mock_store

    existing_app = FastAPI(title="Test App")

    @existing_app.get("/health")
    def health_check():
        return {"status": "ok"}

    app = add_store_access(
        mock_get_obj, app=existing_app, base_path="/users/{user_id}/store"
    )

    client = TestClient(app)

    # Test existing endpoint
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

    # Test added endpoint
    response = client.get("/users/test_user/store/key1")
    assert response.status_code == 200
    assert response.json() == {"value": "value1"}


def test_contains_and_len_methods():
    """Test __contains__ and __len__ methods in add_store_access."""
    mock_store = {'key1': 'value1', 'key2': 'value2'}

    def mock_get_obj(user_id: str):
        return mock_store

    methods = {
        "__iter__": None,
        "__getitem__": None,
        "__contains__": None,
        "__len__": None,
    }

    app = add_store_access(
        mock_get_obj, base_path="/users/{user_id}/store", methods=methods
    )
    client = TestClient(app)

    # Test __contains__ for existing key
    response = client.get("/users/test_user/store/key1/exists")
    assert response.status_code == 200
    assert response.json() is True

    # Test __contains__ for non-existing key
    response = client.get("/users/test_user/store/nonexistent/exists")
    assert response.status_code == 200
    assert response.json() is False

    # Test __len__
    response = client.get("/users/test_user/store/$count")
    assert response.status_code == 200
    assert response.json() == 2


if __name__ == "__main__":
    import pytest

    pytest.main([__file__])
