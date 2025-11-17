# Getting Started with qh

**qh** (Quick HTTP) is a convention-over-configuration framework for exposing Python functions as HTTP services with bidirectional transformation support.

## Installation

```bash
pip install qh
```

## Quick Start

### 1. Create Your First Service

```python
from qh import mk_app

def add(x: int, y: int) -> int:
    """Add two numbers."""
    return x + y

def greet(name: str, title: str = "Mr.") -> str:
    """Greet someone with optional title."""
    return f"Hello, {title} {name}!"

# Create FastAPI app with automatic endpoints
app = mk_app([add, greet])
```

That's it! You now have a fully functional HTTP service with two endpoints:
- `POST /add` - accepts `{x: int, y: int}` returns `int`
- `POST /greet` - accepts `{name: str, title?: str}` returns `str`

### 2. Test Your Service

```python
from qh.testing import test_app

with test_app(app) as client:
    # Test the add function
    response = client.post('/add', json={'x': 3, 'y': 5})
    assert response.json() == 8

    # Test the greet function
    response = client.post('/greet', json={'name': 'Alice'})
    assert response.json() == "Hello, Mr. Alice!"
```

### 3. Run Your Service

```python
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

Or use the built-in test server:

```python
from qh.testing import serve_app

with serve_app(app, port=8000) as url:
    print(f"Server running at {url}")
    input("Press Enter to stop...")
```

Visit `http://localhost:8000/docs` to see the auto-generated API documentation!

## Convention-Based Routing

Use RESTful conventions for automatic path and method inference:

```python
from qh import mk_app

def get_user(user_id: str) -> dict:
    """Get a user by ID."""
    return {'user_id': user_id, 'name': 'Test User'}

def list_users(limit: int = 10) -> list:
    """List users with pagination."""
    return [{'user_id': str(i), 'name': f'User {i}'} for i in range(limit)]

def create_user(name: str, email: str) -> dict:
    """Create a new user."""
    return {'user_id': '123', 'name': name, 'email': email}

def update_user(user_id: str, name: str) -> dict:
    """Update a user."""
    return {'user_id': user_id, 'name': name}

def delete_user(user_id: str) -> dict:
    """Delete a user."""
    return {'user_id': user_id, 'status': 'deleted'}

# Enable conventions to get RESTful routing
app = mk_app(
    [get_user, list_users, create_user, update_user, delete_user],
    use_conventions=True
)
```

This automatically creates RESTful endpoints:
- `GET /users/{user_id}` → `get_user`
- `GET /users?limit=10` → `list_users`
- `POST /users` → `create_user`
- `PUT /users/{user_id}` → `update_user`
- `DELETE /users/{user_id}` → `delete_user`

## Client Generation

Generate Python, JavaScript, or TypeScript clients automatically:

### Python Client

```python
from qh import export_openapi, mk_client_from_app

# Create client from app
client = mk_client_from_app(app)

# Use it like the original functions!
result = client.add(x=3, y=5)
print(result)  # 8

user = client.get_user(user_id='123')
print(user)  # {'user_id': '123', 'name': 'Test User'}
```

### TypeScript Client

```python
from qh import export_openapi, export_ts_client

spec = export_openapi(app, include_python_metadata=True)
ts_code = export_ts_client(spec, use_axios=True)

# Save to file
with open('api-client.ts', 'w') as f:
    f.write(ts_code)
```

Generated TypeScript:

```typescript
export class ApiClient {
  private axios: AxiosInstance;

  constructor(baseUrl: string = 'http://localhost:8000') {
    this.axios = axios.create({ baseURL: baseUrl });
  }

  /**
   * Add two numbers.
   */
  async add(x: number, y: number): Promise<number> {
    const response = await this.axios.post('/add', { x, y });
    return response.data;
  }

  /**
   * Get a user by ID.
   */
  async get_user(user_id: string): Promise<Record<string, any>> {
    let url = `/users/${user_id}`;
    const response = await this.axios.get(url);
    return response.data;
  }
}
```

## Custom Types

Register custom types for automatic serialization:

```python
from qh import mk_app, register_json_type

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

def distance(point: Point) -> float:
    """Calculate distance from origin."""
    return (point.x ** 2 + point.y ** 2) ** 0.5

app = mk_app([distance])

# Test it
from qh.testing import test_app

with test_app(app) as client:
    response = client.post('/distance', json={'point': {'x': 3.0, 'y': 4.0}})
    assert response.json() == 5.0
```

## Next Steps

- **[Features Guide](FEATURES.md)** - Learn about all qh features
- **[Testing Guide](TESTING.md)** - Comprehensive testing strategies
- **[API Reference](API_REFERENCE.md)** - Complete API documentation
- **[Migration Guide](MIGRATION.md)** - Migrate from py2http

## Common Patterns

### Configuration

```python
from qh import mk_app, AppConfig

config = AppConfig(
    title="My API",
    version="1.0.0",
    path_prefix="/api/v1",
    default_methods=['GET', 'POST']
)

app = mk_app([add, subtract], config=config)
```

### Per-Function Configuration

```python
app = mk_app({
    add: {'path': '/math/add', 'methods': ['GET']},
    subtract: {'path': '/math/subtract', 'methods': ['POST']},
})
```

### Error Handling

```python
def divide(x: float, y: float) -> float:
    """Divide two numbers."""
    if y == 0:
        raise ValueError("Cannot divide by zero")
    return x / y

app = mk_app([divide])

with test_app(app) as client:
    # Normal case
    response = client.post('/divide', json={'x': 10.0, 'y': 2.0})
    assert response.json() == 5.0

    # Error case - returns 500 with error message
    response = client.post('/divide', json={'x': 10.0, 'y': 0.0})
    assert response.status_code == 500
    assert "Cannot divide by zero" in response.json()['detail']
```

## Philosophy

**qh** follows these principles:

1. **Convention over Configuration** - Sensible defaults, minimal boilerplate
2. **Bidirectional Transformation** - Python ↔ HTTP ↔ Python with perfect fidelity
3. **Type Safety** - Leverage Python type hints for automatic validation
4. **Developer Experience** - Fast, intuitive, with excellent tooling

Ready to dive deeper? Check out the [Features Guide](FEATURES.md)!
