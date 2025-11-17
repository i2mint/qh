# Testing Guide for qh

This guide covers testing strategies and utilities for qh applications.

## Table of Contents

- [Quick Testing](#quick-testing)
- [Using TestClient](#using-testclient)
- [Integration Testing](#integration-testing)
- [Testing Utilities](#testing-utilities)
- [Round-Trip Testing](#round-trip-testing)
- [Best Practices](#best-practices)

## Quick Testing

The fastest way to test a single function:

```python
from qh.testing import quick_test

def add(x: int, y: int) -> int:
    return x + y

# Test it instantly
result = quick_test(add, x=3, y=5)
assert result == 8
```

## Using TestClient

For more control, use the `test_app` context manager:

```python
from qh import mk_app
from qh.testing import test_app

def add(x: int, y: int) -> int:
    return x + y

def subtract(x: int, y: int) -> int:
    return x - y

app = mk_app([add, subtract])

with test_app(app) as client:
    # Test add
    response = client.post('/add', json={'x': 10, 'y': 3})
    assert response.status_code == 200
    assert response.json() == 13

    # Test subtract
    response = client.post('/subtract', json={'x': 10, 'y': 3})
    assert response.json() == 7
```

### Testing with pytest

```python
import pytest
from qh import mk_app
from qh.testing import test_app

@pytest.fixture
def app():
    """Create test app."""
    def add(x: int, y: int) -> int:
        return x + y

    def multiply(x: int, y: int) -> int:
        return x * y

    return mk_app([add, multiply])

def test_add(app):
    """Test add function."""
    with test_app(app) as client:
        response = client.post('/add', json={'x': 3, 'y': 5})
        assert response.json() == 8

def test_multiply(app):
    """Test multiply function."""
    with test_app(app) as client:
        response = client.post('/multiply', json={'x': 4, 'y': 5})
        assert response.json() == 20
```

## Integration Testing

Test with a real uvicorn server:

```python
from qh import mk_app
from qh.testing import serve_app
import requests

def hello(name: str) -> str:
    return f"Hello, {name}!"

app = mk_app([hello])

with serve_app(app, port=8001) as url:
    # Server is running at http://127.0.0.1:8001
    response = requests.post(f'{url}/hello', json={'name': 'World'})
    assert response.json() == "Hello, World!"

# Server automatically stops after the context
```

### Testing Multiple Services

```python
from qh import mk_app
from qh.testing import serve_app
import requests

# Service 1
def service1_hello(name: str) -> str:
    return f"Service 1: Hello, {name}!"

# Service 2
def service2_hello(name: str) -> str:
    return f"Service 2: Hello, {name}!"

app1 = mk_app([service1_hello])
app2 = mk_app([service2_hello])

# Run multiple services on different ports
with serve_app(app1, port=8001) as url1:
    with serve_app(app2, port=8002) as url2:
        # Both servers running simultaneously
        r1 = requests.post(f'{url1}/service1_hello', json={'name': 'Alice'})
        r2 = requests.post(f'{url2}/service2_hello', json={'name': 'Bob'})

        assert r1.json() == "Service 1: Hello, Alice!"
        assert r2.json() == "Service 2: Hello, Bob!"
```

## Testing Utilities

### AppRunner

The most flexible testing utility:

```python
from qh import mk_app
from qh.testing import AppRunner

def add(x: int, y: int) -> int:
    return x + y

app = mk_app([add])

# Use as context manager
with AppRunner(app) as client:
    response = client.post('/add', json={'x': 3, 'y': 5})
    assert response.json() == 8

# Or with real server
with AppRunner(app, use_server=True, port=8000) as url:
    import requests
    response = requests.post(f'{url}/add', json={'x': 3, 'y': 5})
    assert response.json() == 8
```

### Configuration

```python
from qh.testing import AppRunner

# Custom host and port
with AppRunner(app, use_server=True, host='0.0.0.0', port=9000) as url:
    # Server at http://0.0.0.0:9000
    pass

# Custom timeout for server startup
with AppRunner(app, use_server=True, server_timeout=5.0) as url:
    # Wait up to 5 seconds for server to start
    pass
```

## Round-Trip Testing

Test that functions work identically through HTTP:

```python
from qh import mk_app, mk_client_from_app

def original_function(x: int, y: int) -> int:
    """Original Python function."""
    return x * y + x

# Call directly
direct_result = original_function(3, 5)

# Call through HTTP
app = mk_app([original_function])
client = mk_client_from_app(app)
http_result = client.original_function(x=3, y=5)

# Should be identical
assert direct_result == http_result  # Both are 18
```

### Testing with Custom Types

```python
from qh import mk_app, mk_client_from_app, register_json_type

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

    def distance_from_origin(self):
        return (self.x ** 2 + self.y ** 2) ** 0.5

def create_point(x: float, y: float) -> Point:
    return Point(x, y)

# Test round-trip
app = mk_app([create_point])
client = mk_client_from_app(app)

result = client.create_point(x=3.0, y=4.0)
assert result == {'x': 3.0, 'y': 4.0}
```

## Best Practices

### 1. Use Fixtures

```python
import pytest
from qh import mk_app
from qh.testing import test_app

@pytest.fixture
def math_app():
    """Reusable math API."""
    def add(x: int, y: int) -> int:
        return x + y

    def multiply(x: int, y: int) -> int:
        return x * y

    return mk_app([add, multiply])

def test_operations(math_app):
    """Test multiple operations."""
    with test_app(math_app) as client:
        assert client.post('/add', json={'x': 2, 'y': 3}).json() == 5
        assert client.post('/multiply', json={'x': 2, 'y': 3}).json() == 6
```

### 2. Test Error Cases

```python
def divide(x: float, y: float) -> float:
    if y == 0:
        raise ValueError("Cannot divide by zero")
    return x / y

app = mk_app([divide])

with test_app(app) as client:
    # Test normal case
    response = client.post('/divide', json={'x': 10.0, 'y': 2.0})
    assert response.status_code == 200
    assert response.json() == 5.0

    # Test error case
    response = client.post('/divide', json={'x': 10.0, 'y': 0.0})
    assert response.status_code == 500
    assert "Cannot divide by zero" in response.json()['detail']
```

### 3. Test with Different HTTP Methods

```python
from qh import mk_app

def get_item(item_id: str) -> dict:
    return {'item_id': item_id, 'name': f'Item {item_id}'}

app = mk_app({
    get_item: {'path': '/items/{item_id}', 'methods': ['GET']}
})

with test_app(app) as client:
    # Test GET request
    response = client.get('/items/123')
    assert response.json()['item_id'] == '123'
```

### 4. Test with Query Parameters

```python
def list_items(limit: int = 10, offset: int = 0) -> list:
    return [{'id': i} for i in range(offset, offset + limit)]

app = mk_app({
    list_items: {'path': '/items', 'methods': ['GET']}
})

with test_app(app) as client:
    # Test with query parameters
    response = client.get('/items?limit=5&offset=10')
    items = response.json()
    assert len(items) == 5
    assert items[0]['id'] == 10
```

### 5. Parametrized Testing

```python
import pytest

@pytest.mark.parametrize("x,y,expected", [
    (2, 3, 5),
    (0, 0, 0),
    (-1, 1, 0),
    (10, -5, 5),
])
def test_add_parametrized(x, y, expected):
    """Test add with multiple inputs."""
    from qh.testing import quick_test

    def add(x: int, y: int) -> int:
        return x + y

    result = quick_test(add, x=x, y=y)
    assert result == expected
```

### 6. Testing Conventions

```python
from qh import mk_app
from qh.testing import test_app

def get_user(user_id: str) -> dict:
    return {'user_id': user_id}

def list_users(limit: int = 10) -> list:
    return [{'user_id': str(i)} for i in range(limit)]

app = mk_app([get_user, list_users], use_conventions=True)

with test_app(app) as client:
    # Test GET /users/{user_id}
    response = client.get('/users/123')
    assert response.json()['user_id'] == '123'

    # Test GET /users?limit=5
    response = client.get('/users?limit=5')
    assert len(response.json()) == 5
```

## Automatic Cleanup

All context managers automatically clean up, even on errors:

```python
from qh.testing import serve_app

try:
    with serve_app(app, port=8000) as url:
        # Server is running
        raise RuntimeError("Simulated error")
except RuntimeError:
    pass

# Server has been automatically stopped, even though exception occurred
```

## Performance Testing

```python
import time
from qh import mk_app
from qh.testing import serve_app
import requests

def heavy_computation(n: int) -> int:
    """Simulate heavy computation."""
    time.sleep(0.1)
    return sum(range(n))

app = mk_app([heavy_computation])

with serve_app(app, port=8000) as url:
    start = time.time()

    # Make 10 concurrent requests
    import concurrent.futures
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [
            executor.submit(requests.post, f'{url}/heavy_computation', json={'n': 1000})
            for _ in range(10)
        ]
        results = [f.result() for f in futures]

    elapsed = time.time() - start
    print(f"10 requests completed in {elapsed:.2f} seconds")
    assert all(r.status_code == 200 for r in results)
```

## Summary

qh provides multiple testing utilities:

| Utility | Use Case | Returns |
|---------|----------|---------|
| `quick_test()` | Single function, instant test | Result value |
| `test_app()` | Multiple tests with TestClient | TestClient |
| `serve_app()` | Integration testing with real server | Base URL string |
| `AppRunner` | Full control over test mode | TestClient or URL |
| `run_app()` | Flexible context manager | TestClient or URL |

Choose based on your needs:
- **Development**: Use `quick_test()` or `test_app()`
- **Integration**: Use `serve_app()` for real server testing
- **CI/CD**: Use `test_app()` for fast, reliable tests
- **Full Control**: Use `AppRunner` for custom configurations
