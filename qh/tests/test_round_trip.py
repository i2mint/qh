"""
Round-trip tests: Python function → HTTP service → Python client function

These tests verify that we can expose a Python function as an HTTP service,
then create a client-side Python function that behaves identically to the original.

This is the foundation for the bidirectional transformation capability.
"""

import pytest
from fastapi.testclient import TestClient
from typing import Any, Callable
import inspect

from qh import mk_app, AppConfig
from qh.types import register_type, register_json_type


def make_client_function(app, func_name: str, client: TestClient) -> Callable:
    """
    Create a client-side function that calls the HTTP endpoint.

    This is a simple version - Phase 3 will generate these automatically from OpenAPI.
    """
    # Find the route for this function
    from qh import inspect_routes
    routes = inspect_routes(app)
    route = next((r for r in routes if r['name'] == func_name), None)

    if not route:
        raise ValueError(f"No route found for function: {func_name}")

    path = route['path']
    methods = route['methods']
    method = methods[0] if methods else 'POST'

    def client_func(**kwargs):
        """Client-side function that makes HTTP request."""
        # Extract path parameters
        import re
        path_params = re.findall(r'\{(\w+)\}', path)

        # Build the actual path
        actual_path = path
        request_data = {}

        for key, value in kwargs.items():
            if key in path_params:
                # Replace in path
                actual_path = actual_path.replace(f'{{{key}}}', str(value))
            else:
                # Add to request data
                request_data[key] = value

        # Make the HTTP request
        if method == 'GET':
            response = client.get(actual_path, params=request_data)
        elif method == 'POST':
            response = client.post(actual_path, json=request_data)
        elif method == 'PUT':
            response = client.put(actual_path, json=request_data)
        elif method == 'DELETE':
            response = client.delete(actual_path)
        else:
            raise ValueError(f"Unsupported method: {method}")

        response.raise_for_status()
        return response.json()

    return client_func


class TestRoundTrip:
    """Test round-trip transformations with various scenarios."""

    def test_simple_builtin_types(self):
        """Test round trip with simple builtin types."""

        # Server-side function
        def add(x: int, y: int) -> int:
            """Add two numbers."""
            return x + y

        # Create service
        app = mk_app([add])
        client = TestClient(app)

        # Create client function
        client_add = make_client_function(app, 'add', client)

        # Test round trip
        result = client_add(x=3, y=5)
        assert result == 8

        # Test with different values
        result = client_add(x=10, y=20)
        assert result == 30

    def test_dict_and_list_types(self):
        """Test round trip with dict and list types."""

        def process_data(data: dict, items: list) -> dict:
            """Process some data."""
            return {
                'data_keys': list(data.keys()),
                'items_count': len(items),
                'combined': {**data, 'items': items}
            }

        app = mk_app([process_data])
        client = TestClient(app)
        client_func = make_client_function(app, 'process_data', client)

        result = client_func(
            data={'a': 1, 'b': 2},
            items=[1, 2, 3]
        )

        assert result['data_keys'] == ['a', 'b']
        assert result['items_count'] == 3
        assert result['combined']['items'] == [1, 2, 3]

    def test_optional_parameters(self):
        """Test round trip with optional parameters."""

        def greet(name: str, title: str = "Mr.") -> str:
            """Greet someone with optional title."""
            return f"Hello, {title} {name}!"

        app = mk_app([greet])
        client = TestClient(app)
        client_func = make_client_function(app, 'greet', client)

        # With default
        result = client_func(name="Smith")
        assert result == "Hello, Mr. Smith!"

        # With explicit title
        result = client_func(name="Jones", title="Dr.")
        assert result == "Hello, Dr. Jones!"

    def test_path_parameters(self):
        """Test round trip with path parameters."""

        def get_item(item_id: str, detail_level: int = 1) -> dict:
            """Get an item by ID."""
            return {
                'item_id': item_id,
                'detail_level': detail_level,
                'name': f'Item {item_id}'
            }

        app = mk_app({
            get_item: {'path': '/items/{item_id}', 'methods': ['GET']}
        })
        client = TestClient(app)
        client_func = make_client_function(app, 'get_item', client)

        result = client_func(item_id='42', detail_level=2)
        assert result['item_id'] == '42'
        assert result['detail_level'] == 2

    def test_custom_type_round_trip(self):
        """Test round trip with custom types."""

        @register_json_type
        class Point:
            def __init__(self, x: float, y: float):
                self.x = x
                self.y = y

            def to_dict(self):
                return {'x': self.x, 'y': self.y}

            @classmethod
            def from_dict(cls, data):
                return cls(data['x'], data['y'])

        def create_point(x: float, y: float) -> Point:
            """Create a point."""
            return Point(x, y)

        def distance(point: Point) -> float:
            """Calculate distance from origin."""
            return (point.x ** 2 + point.y ** 2) ** 0.5

        app = mk_app([create_point, distance])
        client = TestClient(app)

        # Test create_point
        client_create = make_client_function(app, 'create_point', client)
        result = client_create(x=3.0, y=4.0)
        assert result == {'x': 3.0, 'y': 4.0}

        # Test distance (takes Point as input)
        client_distance = make_client_function(app, 'distance', client)
        result = client_distance(point={'x': 3.0, 'y': 4.0})
        assert result == 5.0

    def test_conventions_round_trip(self):
        """Test round trip with convention-based routing."""

        def get_user(user_id: str) -> dict:
            """Get a user."""
            return {
                'user_id': user_id,
                'name': 'Test User',
                'email': f'user{user_id}@example.com'
            }

        def list_users(limit: int = 10) -> list:
            """List users."""
            return [
                {'user_id': str(i), 'name': f'User {i}'}
                for i in range(limit)
            ]

        app = mk_app([get_user, list_users], use_conventions=True)
        client = TestClient(app)

        # Test get_user (GET with path param)
        client_get = make_client_function(app, 'get_user', client)
        result = client_get(user_id='42')
        assert result['user_id'] == '42'
        assert result['name'] == 'Test User'

        # Test list_users (GET with query param)
        client_list = make_client_function(app, 'list_users', client)
        result = client_list(limit=5)
        assert len(result) == 5

    def test_error_propagation(self):
        """Test that errors propagate correctly in round trip."""

        def divide(x: float, y: float) -> float:
            """Divide two numbers."""
            if y == 0:
                raise ValueError("Cannot divide by zero")
            return x / y

        app = mk_app([divide])
        client = TestClient(app)
        client_func = make_client_function(app, 'divide', client)

        # Normal operation
        result = client_func(x=10.0, y=2.0)
        assert result == 5.0

        # Error case
        with pytest.raises(Exception):  # HTTP error
            client_func(x=10.0, y=0.0)

    def test_numpy_round_trip(self):
        """Test round trip with NumPy arrays."""
        try:
            import numpy as np

            def multiply_array(data: np.ndarray, factor: float) -> np.ndarray:
                """Multiply array by factor."""
                return data * factor

            app = mk_app([multiply_array])
            client = TestClient(app)
            client_func = make_client_function(app, 'multiply_array', client)

            result = client_func(data=[1, 2, 3, 4], factor=2.0)
            assert result == [2, 4, 6, 8]

        except ImportError:
            pytest.skip("NumPy not available")

    def test_multiple_return_values(self):
        """Test round trip with complex return values."""

        def analyze(numbers: list) -> dict:
            """Analyze a list of numbers."""
            return {
                'count': len(numbers),
                'sum': sum(numbers),
                'mean': sum(numbers) / len(numbers) if numbers else 0,
                'min': min(numbers) if numbers else None,
                'max': max(numbers) if numbers else None,
            }

        app = mk_app([analyze])
        client = TestClient(app)
        client_func = make_client_function(app, 'analyze', client)

        result = client_func(numbers=[1, 2, 3, 4, 5])
        assert result['count'] == 5
        assert result['sum'] == 15
        assert result['mean'] == 3.0
        assert result['min'] == 1
        assert result['max'] == 5

    def test_nested_data_structures(self):
        """Test round trip with nested data structures."""

        def process_order(order: dict) -> dict:
            """Process an order with nested items."""
            total = sum(item['price'] * item['quantity'] for item in order['items'])
            return {
                'order_id': order['order_id'],
                'customer': order['customer'],
                'total': total,
                'item_count': len(order['items'])
            }

        app = mk_app([process_order])
        client = TestClient(app)
        client_func = make_client_function(app, 'process_order', client)

        result = client_func(order={
            'order_id': '123',
            'customer': 'John Doe',
            'items': [
                {'name': 'Widget', 'price': 10.0, 'quantity': 2},
                {'name': 'Gadget', 'price': 15.0, 'quantity': 1},
            ]
        })

        assert result['order_id'] == '123'
        assert result['customer'] == 'John Doe'
        assert result['total'] == 35.0
        assert result['item_count'] == 2


class TestSignaturePreservation:
    """Test that client functions preserve original function signatures."""

    def test_parameter_names_preserved(self):
        """Test that parameter names match."""

        def original(name: str, age: int, email: str = None) -> dict:
            return {'name': name, 'age': age, 'email': email}

        app = mk_app([original])
        client = TestClient(app)

        # In Phase 3, we'll auto-generate this with proper signature
        # For now, we just verify the concept works
        client_func = make_client_function(app, 'original', client)

        # Should work with same parameter names
        result = client_func(name="Alice", age=30, email="alice@example.com")
        assert result['name'] == 'Alice'
        assert result['age'] == 30
        assert result['email'] == 'alice@example.com'

    def test_defaults_work(self):
        """Test that default values work in client."""

        def original(x: int, y: int = 10, z: int = 20) -> int:
            return x + y + z

        app = mk_app([original])
        client = TestClient(app)
        client_func = make_client_function(app, 'original', client)

        # With all defaults
        result = client_func(x=5)
        assert result == 35  # 5 + 10 + 20

        # Override one default
        result = client_func(x=5, y=15)
        assert result == 40  # 5 + 15 + 20

        # Override all
        result = client_func(x=5, y=15, z=25)
        assert result == 45


class TestMultipleTransformations:
    """Test various transformation scenarios in round trips."""

    def test_mixed_http_locations(self):
        """Test round trip with params from different HTTP locations."""

        def search(
            category: str,  # Will be path param
            query: str,     # Will be query param
            limit: int = 10  # Will be query param
        ) -> list:
            """Search in a category."""
            return [
                {
                    'category': category,
                    'query': query,
                    'id': i,
                    'name': f'Result {i}'
                }
                for i in range(limit)
            ]

        app = mk_app({
            search: {
                'path': '/search/{category}',
                'methods': ['GET']
            }
        })
        client = TestClient(app)
        client_func = make_client_function(app, 'search', client)

        result = client_func(category='books', query='python', limit=3)
        assert len(result) == 3
        assert all(r['category'] == 'books' for r in result)
        assert all(r['query'] == 'python' for r in result)

    def test_type_conversion_chain(self):
        """Test multiple type conversions in a chain."""

        @register_json_type
        class Temperature:
            def __init__(self, celsius: float):
                self.celsius = celsius

            def to_dict(self):
                return {'celsius': self.celsius}

            @classmethod
            def from_dict(cls, data):
                return cls(data['celsius'])

        def celsius_to_fahrenheit(temp: Temperature) -> float:
            """Convert temperature to Fahrenheit."""
            return temp.celsius * 9/5 + 32

        def fahrenheit_to_celsius(fahrenheit: float) -> Temperature:
            """Convert Fahrenheit to temperature object."""
            celsius = (fahrenheit - 32) * 5/9
            return Temperature(celsius)

        app = mk_app([celsius_to_fahrenheit, fahrenheit_to_celsius])
        client = TestClient(app)

        # Forward conversion
        client_c2f = make_client_function(app, 'celsius_to_fahrenheit', client)
        result = client_c2f(temp={'celsius': 0.0})
        assert result == 32.0

        # Reverse conversion
        client_f2c = make_client_function(app, 'fahrenheit_to_celsius', client)
        result = client_f2c(fahrenheit=32.0)
        assert result['celsius'] == 0.0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
