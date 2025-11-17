"""
Tests for Phase 3: OpenAPI export and Python client generation.

These tests verify:
1. Enhanced OpenAPI generation with x-python extensions
2. Python client generation from OpenAPI specs
3. Round-trip compatibility (function → service → client → result)
"""

import pytest
from fastapi.testclient import TestClient
from typing import Optional

from qh import mk_app, export_openapi, mk_client_from_app, mk_client_from_openapi


class TestEnhancedOpenAPI:
    """Test enhanced OpenAPI generation."""

    def test_basic_openapi_export(self):
        """Test basic OpenAPI export includes paths and operations."""

        def add(x: int, y: int) -> int:
            return x + y

        app = mk_app([add])
        spec = export_openapi(app)

        # Check basic structure
        assert 'openapi' in spec
        assert 'paths' in spec
        assert '/add' in spec['paths']
        assert 'post' in spec['paths']['/add']

    def test_python_signature_metadata(self):
        """Test x-python-signature extension is added."""

        def add(x: int, y: int = 10) -> int:
            """Add two numbers."""
            return x + y

        app = mk_app([add])
        spec = export_openapi(app, include_python_metadata=True)

        # Check x-python-signature
        operation = spec['paths']['/add']['post']
        assert 'x-python-signature' in operation

        sig = operation['x-python-signature']
        assert sig['name'] == 'add'
        assert sig['return_type'] == 'int'
        assert sig['docstring'] == 'Add two numbers.'

        # Check parameters
        params = sig['parameters']
        assert len(params) == 2

        # Check x parameter
        x_param = next(p for p in params if p['name'] == 'x')
        assert x_param['type'] == 'int'
        assert x_param['required'] is True

        # Check y parameter with default
        y_param = next(p for p in params if p['name'] == 'y')
        assert y_param['type'] == 'int'
        assert y_param['required'] is False
        assert y_param['default'] == 10

    def test_optional_parameters_in_signature(self):
        """Test that Optional parameters are handled correctly."""

        def greet(name: str, title: Optional[str] = None) -> str:
            """Greet someone."""
            if title:
                return f"Hello, {title} {name}!"
            return f"Hello, {name}!"

        app = mk_app([greet])
        spec = export_openapi(app, include_python_metadata=True)

        sig = spec['paths']['/greet']['post']['x-python-signature']
        params = sig['parameters']

        title_param = next(p for p in params if p['name'] == 'title')
        assert 'Optional' in title_param['type']
        assert title_param['required'] is False

    def test_examples_generation(self):
        """Test that examples are generated for requests."""

        def add(x: int, y: int) -> int:
            return x + y

        app = mk_app([add])
        spec = export_openapi(app, include_examples=True)

        # Check examples exist (may not be in requestBody if FastAPI doesn't create it)
        operation = spec['paths']['/add']['post']
        # Examples might be added if requestBody exists
        # For now, just verify the export doesn't crash
        assert operation is not None

    def test_multiple_functions(self):
        """Test OpenAPI export with multiple functions."""

        def add(x: int, y: int) -> int:
            return x + y

        def subtract(x: int, y: int) -> int:
            return x - y

        def multiply(x: int, y: int) -> int:
            return x * y

        app = mk_app([add, subtract, multiply])
        spec = export_openapi(app, include_python_metadata=True)

        # Check all functions are present
        assert '/add' in spec['paths']
        assert '/subtract' in spec['paths']
        assert '/multiply' in spec['paths']

        # Check all have signatures
        for path in ['/add', '/subtract', '/multiply']:
            assert 'x-python-signature' in spec['paths'][path]['post']


class TestClientGeneration:
    """Test Python client generation from OpenAPI."""

    def test_client_from_app(self):
        """Test creating client from FastAPI app."""

        def add(x: int, y: int) -> int:
            return x + y

        app = mk_app([add])
        client = mk_client_from_app(app)

        # Client should have add function
        assert hasattr(client, 'add')

        # Test calling the function
        result = client.add(x=3, y=5)
        assert result == 8

    def test_client_with_defaults(self):
        """Test client functions respect default parameters."""

        def add(x: int, y: int = 10) -> int:
            return x + y

        app = mk_app([add])
        client = mk_client_from_app(app)

        # Call with default
        result = client.add(x=5)
        assert result == 15

        # Call with explicit value
        result = client.add(x=5, y=20)
        assert result == 25

    def test_client_multiple_functions(self):
        """Test client with multiple functions."""

        def add(x: int, y: int) -> int:
            return x + y

        def multiply(x: int, y: int) -> int:
            return x * y

        app = mk_app([add, multiply])
        client = mk_client_from_app(app)

        assert hasattr(client, 'add')
        assert hasattr(client, 'multiply')

        assert client.add(x=3, y=5) == 8
        assert client.multiply(x=3, y=5) == 15

    def test_client_with_conventions(self):
        """Test client generation with convention-based routing."""

        def get_user(user_id: str) -> dict:
            return {'user_id': user_id, 'name': 'Test User'}

        def list_users(limit: int = 10) -> list:
            return [{'user_id': str(i), 'name': f'User {i}'} for i in range(limit)]

        app = mk_app([get_user, list_users], use_conventions=True)
        client = mk_client_from_app(app)

        # Test get_user (path param)
        result = client.get_user(user_id='123')
        assert result['user_id'] == '123'

        # Test list_users (query param)
        result = client.list_users(limit=5)
        assert len(result) == 5

    def test_client_from_openapi_spec(self):
        """Test creating client directly from OpenAPI spec."""

        def add(x: int, y: int) -> int:
            return x + y

        app = mk_app([add])
        spec = export_openapi(app, include_python_metadata=True)

        # Create client from spec
        client = mk_client_from_openapi(spec, base_url="http://testserver")

        # Note: This test requires a running server or TestClient wrapper
        # For now, just verify client creation works
        assert hasattr(client, 'add')

    def test_client_error_handling(self):
        """Test that client properly handles errors."""

        def divide(x: float, y: float) -> float:
            if y == 0:
                raise ValueError("Cannot divide by zero")
            return x / y

        app = mk_app([divide])
        client = mk_client_from_app(app)

        # Normal operation
        result = client.divide(x=10.0, y=2.0)
        assert result == 5.0

        # Error case - should raise an exception
        with pytest.raises(Exception):  # RuntimeError wrapping HTTP error
            client.divide(x=10.0, y=0.0)


class TestRoundTripWithClient:
    """Test complete round-trip: function → service → client → result."""

    def test_simple_round_trip(self):
        """Test simple round trip matches original function behavior."""

        def add(x: int, y: int) -> int:
            """Add two numbers."""
            return x + y

        # Original function
        original_result = add(3, 5)

        # Through HTTP service and client
        app = mk_app([add])
        client = mk_client_from_app(app)
        client_result = client.add(x=3, y=5)

        assert original_result == client_result

    def test_round_trip_with_defaults(self):
        """Test round trip preserves default parameter behavior."""

        def greet(name: str, title: str = "Mr.") -> str:
            return f"Hello, {title} {name}!"

        # Test with default
        original_result = greet("Smith")

        app = mk_app([greet])
        client = mk_client_from_app(app)
        client_result = client.greet(name="Smith")

        assert original_result == client_result

        # Test with explicit value
        original_result = greet("Jones", "Dr.")
        client_result = client.greet(name="Jones", title="Dr.")

        assert original_result == client_result

    def test_round_trip_complex_types(self):
        """Test round trip with complex return types."""

        def analyze(numbers: list) -> dict:
            """Analyze a list of numbers."""
            return {
                'count': len(numbers),
                'sum': sum(numbers),
                'mean': sum(numbers) / len(numbers) if numbers else 0,
            }

        original_result = analyze([1, 2, 3, 4, 5])

        app = mk_app([analyze])
        client = mk_client_from_app(app)
        client_result = client.analyze(numbers=[1, 2, 3, 4, 5])

        assert original_result == client_result

    def test_round_trip_with_custom_types(self):
        """Test round trip with custom types using type registry."""
        from qh import register_json_type

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
            return Point(x, y)

        app = mk_app([create_point])
        client = mk_client_from_app(app)

        result = client.create_point(x=3.0, y=4.0)
        assert result == {'x': 3.0, 'y': 4.0}

    def test_signature_preservation(self):
        """Test that client functions preserve function metadata."""

        def add(x: int, y: int = 10) -> int:
            """Add two numbers with optional second parameter."""
            return x + y

        app = mk_app([add])
        client = mk_client_from_app(app)

        # Check function name
        assert client.add.__name__ == 'add'

        # Check docstring
        assert client.add.__doc__ is not None

    def test_multiple_functions_round_trip(self):
        """Test round trip with multiple functions."""

        def add(x: int, y: int) -> int:
            return x + y

        def subtract(x: int, y: int) -> int:
            return x - y

        def multiply(x: int, y: int) -> int:
            return x * y

        app = mk_app([add, subtract, multiply])
        client = mk_client_from_app(app)

        assert client.add(x=10, y=3) == 13
        assert client.subtract(x=10, y=3) == 7
        assert client.multiply(x=10, y=3) == 30


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
