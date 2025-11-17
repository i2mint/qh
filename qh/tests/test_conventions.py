"""
Tests for convention-based routing.
"""

import pytest
from fastapi.testclient import TestClient

from qh import mk_app, print_routes, inspect_routes
from qh.conventions import (
    parse_function_name,
    infer_http_method,
    infer_path_from_function,
    singularize,
    pluralize,
)


def test_parse_function_name():
    """Test parsing function names."""
    # GET operations
    result = parse_function_name('get_user')
    assert result.verb == 'get'
    assert result.resource == 'user'
    assert not result.is_collection_operation

    # List operations
    result = parse_function_name('list_users')
    assert result.verb == 'list'
    assert result.resource == 'users'
    assert result.is_collection_operation

    # Create operations
    result = parse_function_name('create_order')
    assert result.verb == 'create'
    assert result.resource == 'order'
    assert result.is_collection_operation

    # Update operations
    result = parse_function_name('update_user')
    assert result.verb == 'update'
    assert result.resource == 'user'

    # Delete operations
    result = parse_function_name('delete_item')
    assert result.verb == 'delete'
    assert result.resource == 'item'


def test_infer_http_method():
    """Test HTTP method inference."""
    assert infer_http_method('get_user') == 'GET'
    assert infer_http_method('list_users') == 'GET'
    assert infer_http_method('fetch_data') == 'GET'

    assert infer_http_method('create_user') == 'POST'
    assert infer_http_method('add_item') == 'POST'

    assert infer_http_method('update_user') == 'PUT'
    assert infer_http_method('modify_settings') == 'PUT'

    assert infer_http_method('patch_profile') == 'PATCH'

    assert infer_http_method('delete_user') == 'DELETE'
    assert infer_http_method('remove_item') == 'DELETE'


def test_singularize_pluralize():
    """Test word singularization and pluralization."""
    assert singularize('users') == 'user'
    assert singularize('orders') == 'order'
    assert singularize('categories') == 'category'
    assert singularize('buses') == 'bus'

    assert pluralize('user') == 'users'
    assert pluralize('order') == 'orders'
    assert pluralize('category') == 'categories'
    assert pluralize('bus') == 'buses'


def test_infer_path():
    """Test path inference from functions."""

    def get_user(user_id: str):
        pass

    path = infer_path_from_function(get_user)
    assert path == '/users/{user_id}'

    def list_users():
        pass

    path = infer_path_from_function(list_users)
    assert path == '/users'

    def create_user(name: str):
        pass

    path = infer_path_from_function(create_user)
    assert path == '/users'

    def update_user(user_id: str, name: str):
        pass

    path = infer_path_from_function(update_user)
    assert path == '/users/{user_id}'

    def delete_order(order_id: str):
        pass

    path = infer_path_from_function(delete_order)
    assert path == '/orders/{order_id}'


def test_conventions_in_mk_app():
    """Test using conventions with mk_app."""

    def get_user(user_id: str) -> dict:
        """Get a user by ID."""
        return {'user_id': user_id, 'name': 'Test User'}

    def list_users() -> list:
        """List all users."""
        return [{'user_id': '1', 'name': 'User 1'}]

    def create_user(name: str) -> dict:
        """Create a new user."""
        return {'user_id': '123', 'name': name}

    # Create app with conventions
    app = mk_app([get_user, list_users, create_user], use_conventions=True)

    # Check routes
    routes = inspect_routes(app)
    app_routes = [r for r in routes if not r['path'].startswith('/docs') and not r['path'].startswith('/openapi')]

    # Find specific routes by name
    get_user_route = next((r for r in app_routes if r['name'] == 'get_user'), None)
    list_users_route = next((r for r in app_routes if r['name'] == 'list_users'), None)
    create_user_route = next((r for r in app_routes if r['name'] == 'create_user'), None)

    # get_user should be GET /users/{user_id}
    assert get_user_route is not None
    assert get_user_route['path'] == '/users/{user_id}'
    assert 'GET' in get_user_route['methods']

    # list_users should be GET /users
    assert list_users_route is not None
    assert list_users_route['path'] == '/users'
    assert 'GET' in list_users_route['methods']

    # create_user should be POST /users
    assert create_user_route is not None
    assert create_user_route['path'] == '/users'
    assert 'POST' in create_user_route['methods']


def test_conventions_with_client():
    """Test convention-based routes with actual requests."""

    def get_user(user_id: str) -> dict:
        return {'user_id': user_id, 'name': 'Test User'}

    def list_users(limit: int = 10) -> list:
        return [{'user_id': str(i)} for i in range(limit)]

    def create_user(name: str, email: str) -> dict:
        return {'user_id': '123', 'name': name, 'email': email}

    app = mk_app([get_user, list_users, create_user], use_conventions=True)
    client = TestClient(app)

    # Test GET /users/{user_id}
    response = client.get('/users/42')
    assert response.status_code == 200
    assert response.json()['user_id'] == '42'

    # Test GET /users (list)
    response = client.get('/users', params={'limit': 5})
    assert response.status_code == 200
    assert len(response.json()) == 5

    # Test POST /users (create)
    response = client.post('/users', json={'name': 'John', 'email': 'john@example.com'})
    assert response.status_code == 200
    assert response.json()['name'] == 'John'


def test_conventions_override():
    """Test that explicit config overrides conventions."""

    def get_user(user_id: str) -> dict:
        return {'user_id': user_id}

    # Use conventions but override path
    app = mk_app(
        {get_user: {'path': '/custom/user/{user_id}'}},
        use_conventions=True
    )

    routes = inspect_routes(app)
    route_paths = [r['path'] for r in routes]

    # Should use custom path, not conventional path
    assert '/custom/user/{user_id}' in route_paths
    assert '/users/{user_id}' not in route_paths


def test_crud_operations():
    """Test full CRUD operations with conventions."""

    users_db = {}

    def get_user(user_id: str) -> dict:
        return users_db.get(user_id, {'error': 'not found'})

    def list_users() -> list:
        return list(users_db.values())

    def create_user(user_id: str, name: str) -> dict:
        user = {'user_id': user_id, 'name': name}
        users_db[user_id] = user
        return user

    def update_user(user_id: str, name: str) -> dict:
        if user_id in users_db:
            users_db[user_id]['name'] = name
            return users_db[user_id]
        return {'error': 'not found'}

    def delete_user(user_id: str) -> dict:
        if user_id in users_db:
            user = users_db.pop(user_id)
            return {'deleted': user}
        return {'error': 'not found'}

    app = mk_app(
        [get_user, list_users, create_user, update_user, delete_user],
        use_conventions=True
    )

    client = TestClient(app)

    # Create
    response = client.post('/users', json={'user_id': '1', 'name': 'Alice'})
    assert response.status_code == 200

    # Read (get)
    response = client.get('/users/1')
    assert response.status_code == 200
    assert response.json()['name'] == 'Alice'

    # Update
    response = client.put('/users/1', json={'name': 'Alice Updated'})
    assert response.status_code == 200
    assert response.json()['name'] == 'Alice Updated'

    # List
    response = client.get('/users')
    assert response.status_code == 200
    assert len(response.json()) == 1

    # Delete
    response = client.delete('/users/1')
    assert response.status_code == 200

    # Verify deleted
    response = client.get('/users')
    assert len(response.json()) == 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
