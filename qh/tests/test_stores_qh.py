"""Test stores_qh.py"""

from fastapi import FastAPI
from fastapi.testclient import TestClient
from qh.stores_qh import add_mall_access

"""
Tests for the stores_qh module.
"""


def test_add_mall_access_with_none_app():
    """Test that add_mall_access returns a FastAPI instance with default settings when app=None."""
    mock_mall = {'preferences': {'theme': 'dark'}, 'cart': {'item1': 2}}

    def mock_get_mall(user_id: str):
        return mock_mall if user_id == "test_user" else None

    app = add_mall_access(mock_get_mall)

    client = TestClient(app)
    response = client.get("/")

    # The root endpoint isn't added automatically anymore, so we check for other endpoints
    response = client.get("/users/test_user/mall")
    assert response.status_code == 200


def test_add_mall_access_with_string_app():
    """Test that add_mall_access creates an app with the provided title when app is a string."""
    mock_mall = {'preferences': {'theme': 'dark'}, 'cart': {'item1': 2}}

    def mock_get_mall(user_id: str):
        return mock_mall

    app = add_mall_access(mock_get_mall, "Custom App Title")
    assert app.title == "Custom App Title"
    assert app.version == "1.0.0"


def test_add_mall_access_with_dict_app():
    """Test that add_mall_access creates an app with the provided kwargs when app is a dict."""
    mock_mall = {'preferences': {'theme': 'dark'}, 'cart': {'item1': 2}}

    def mock_get_mall(user_id: str):
        return mock_mall

    app_config = {
        "title": "Dict Config App",
        "version": "2.0.0",
        "description": "Test description",
    }
    app = add_mall_access(mock_get_mall, app_config)

    assert app.title == "Dict Config App"
    assert app.version == "2.0.0"
    assert app.description == "Test description"


def test_add_mall_access_with_existing_app():
    """Test that add_mall_access adds endpoints to an existing FastAPI app."""
    mock_mall = {'preferences': {'theme': 'dark'}, 'cart': {'item1': 2}}

    def mock_get_mall(user_id: str):
        return mock_mall

    existing_app = FastAPI(title="Existing App", version="3.0.0")

    # Add a test endpoint to the existing app
    @existing_app.get("/existing_endpoint")
    def existing_endpoint():
        return {"message": "This is an existing endpoint"}

    app = add_mall_access(mock_get_mall, existing_app)

    # Verify it's the same app instance
    assert app is existing_app
    assert app.title == "Existing App"

    client = TestClient(app)

    # Check that both existing and new endpoints work
    response = client.get("/existing_endpoint")
    assert response.status_code == 200
    assert response.json() == {"message": "This is an existing endpoint"}

    response = client.get("/users/test_user/mall")
    assert response.status_code == 200


def test_read_operations():
    """Test the GET endpoints for reading mall data."""
    mock_mall = {
        'preferences': {'theme': 'dark', 'language': 'en'},
        'cart': {'item1': 2, 'item2': 1},
    }

    def mock_get_mall(user_id: str):
        return mock_mall if user_id == "test_user" else None

    app = add_mall_access(mock_get_mall)
    client = TestClient(app)

    # Test list_mall_keys
    response = client.get("/users/test_user/mall")
    assert response.status_code == 200
    assert sorted(response.json()) == sorted(['preferences', 'cart'])

    # Test list_store_keys
    response = client.get("/users/test_user/mall/preferences")
    assert response.status_code == 200
    assert sorted(response.json()) == sorted(['theme', 'language'])

    # Test get_store_item
    response = client.get("/users/test_user/mall/preferences/theme")
    assert response.status_code == 200
    assert response.json()["value"] == "dark"


def test_write_operations():
    """Test the PUT endpoint for updating mall data."""
    mock_mall = {'preferences': {'theme': 'dark'}}

    def mock_get_mall(user_id: str):
        return mock_mall

    app = add_mall_access(mock_get_mall, write=True)
    client = TestClient(app)

    # Test set_store_item
    response = client.put(
        "/users/test_user/mall/preferences/theme", json={"value": "light"}
    )
    assert response.status_code == 200
    assert response.json()["message"] == "Item set successfully"
    assert mock_mall['preferences']['theme'] == "light"


def test_delete_operations():
    """Test the DELETE endpoint for removing mall data."""
    mock_mall = {'preferences': {'theme': 'dark', 'language': 'en'}}

    def mock_get_mall(user_id: str):
        return mock_mall

    app = add_mall_access(mock_get_mall, delete=True)
    client = TestClient(app)

    # Test delete_store_item
    response = client.delete("/users/test_user/mall/preferences/language")
    assert response.status_code == 200
    assert response.json()["message"] == "Item deleted successfully"
    assert 'language' not in mock_mall['preferences']


def test_write_disabled():
    """Test that write endpoint is not available when write=False."""

    def mock_get_mall(user_id: str):
        return {'preferences': {'theme': 'dark'}}

    app = add_mall_access(mock_get_mall, write=False)
    client = TestClient(app)

    # PUT should not be available
    response = client.put(
        "/users/test_user/mall/preferences/theme", json={"value": "light"}
    )
    assert response.status_code == 405  # Method Not Allowed


def test_delete_disabled():
    """Test that delete endpoint is not available when delete=False."""

    def mock_get_mall(user_id: str):
        return {'preferences': {'theme': 'dark'}}

    app = add_mall_access(mock_get_mall, delete=False)
    client = TestClient(app)

    # DELETE should not be available
    response = client.delete("/users/test_user/mall/preferences/theme")
    assert response.status_code == 405  # Method Not Allowed


def test_both_write_and_delete_enabled():
    """Test that both write and delete endpoints can be enabled independently."""
    mock_mall = {'preferences': {'theme': 'dark', 'language': 'en'}}

    def mock_get_mall(user_id: str):
        return mock_mall

    app = add_mall_access(mock_get_mall, write=True, delete=True)
    client = TestClient(app)

    # Test PUT
    response = client.put(
        "/users/test_user/mall/preferences/theme", json={"value": "light"}
    )
    assert response.status_code == 200

    # Test DELETE
    response = client.delete("/users/test_user/mall/preferences/language")
    assert response.status_code == 200



def test_error_handling():
    """Test error conditions such as non-existent user, store, or item."""
    mock_mall = {'preferences': {'theme': 'dark'}}

    def mock_get_mall(user_id: str):
        return mock_mall if user_id == "test_user" else None

    app = add_mall_access(mock_get_mall)
    client = TestClient(app)

    # Test non-existent user
    response = client.get("/users/unknown_user/mall")
    assert response.status_code == 404

    # Test non-existent store
    response = client.get("/users/test_user/mall/unknown_store")
    assert response.status_code == 404

    # Test non-existent item
    response = client.get("/users/test_user/mall/preferences/unknown_item")
    assert response.status_code == 404


if __name__ == "__main__":
    import pytest

    pytest.main([__file__])
