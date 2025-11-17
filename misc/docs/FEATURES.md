# qh Features Guide

Comprehensive guide to all features in qh - the convention-over-configuration HTTP API framework.

## Table of Contents

- [Quick Start](#quick-start)
- [Core Features](#core-features)
- [Convention-Based Routing](#convention-based-routing)
- [Custom Configuration](#custom-configuration)
- [Type System](#type-system)
- [Client Generation](#client-generation)
- [OpenAPI Integration](#openapi-integration)
- [Store/Mall Pattern](#storemall-pattern)
- [Testing](#testing)
- [Advanced Features](#advanced-features)

## Quick Start

The fastest way to create an HTTP API:

```python
from qh import mk_app

def add(x: int, y: int) -> int:
    """Add two numbers."""
    return x + y

app = mk_app([add])
```

That's it! You now have:
- HTTP endpoint at `POST /add`
- Automatic JSON serialization/deserialization
- Type validation
- OpenAPI documentation at `/docs`
- Automatic error handling

## Core Features

### 1. Zero Configuration

Create APIs from plain Python functions with no decorators or boilerplate:

```python
from qh import mk_app

def multiply(x: int, y: int) -> int:
    return x * y

def greet(name: str = "World") -> str:
    return f"Hello, {name}!"

app = mk_app([multiply, greet])
```

**What you get:**
- `POST /multiply` - accepts `{"x": 3, "y": 5}`, returns `15`
- `POST /greet` - accepts `{"name": "Alice"}`, returns `"Hello, Alice!"`
- Full type validation on inputs and outputs
- Automatic OpenAPI docs

### 2. Automatic Type Handling

qh automatically handles type conversion between Python and JSON:

```python
from typing import List, Dict, Optional
from datetime import datetime

def process_data(
    values: List[int],
    metadata: Dict[str, str],
    timestamp: Optional[datetime] = None
) -> dict:
    return {
        'sum': sum(values),
        'count': len(values),
        'metadata': metadata,
        'processed_at': timestamp or datetime.now()
    }

app = mk_app([process_data])
```

**Request:**
```json
{
    "values": [1, 2, 3, 4, 5],
    "metadata": {"source": "api", "version": "1.0"}
}
```

**Response:**
```json
{
    "sum": 15,
    "count": 5,
    "metadata": {"source": "api", "version": "1.0"},
    "processed_at": "2025-01-15T10:30:00"
}
```

### 3. Multiple HTTP Methods

Control which HTTP methods are supported:

```python
from qh import mk_app

def get_status() -> dict:
    return {'status': 'running', 'uptime': 3600}

def create_item(name: str, value: int) -> dict:
    return {'id': 123, 'name': name, 'value': value}

app = mk_app({
    get_status: {'methods': ['GET']},
    create_item: {'methods': ['POST']},
})
```

### 4. Path Parameters

Use path parameters for RESTful URLs:

```python
def get_item(item_id: str) -> dict:
    return {'item_id': item_id, 'name': f'Item {item_id}'}

app = mk_app({
    get_item: {
        'path': '/items/{item_id}',
        'methods': ['GET']
    }
})
```

**Usage:**
```bash
curl http://localhost:8000/items/42
# Returns: {"item_id": "42", "name": "Item 42"}
```

### 5. Query Parameters

GET requests automatically use query parameters:

```python
def search(query: str, limit: int = 10, offset: int = 0) -> dict:
    return {
        'query': query,
        'limit': limit,
        'offset': offset,
        'results': []
    }

app = mk_app({
    search: {
        'path': '/search',
        'methods': ['GET']
    }
})
```

**Usage:**
```bash
curl "http://localhost:8000/search?query=python&limit=20"
```

## Convention-Based Routing

Enable automatic RESTful routing based on function names:

```python
from qh import mk_app

# Function names follow patterns: {action}_{resource}
def get_user(user_id: str) -> dict:
    return {'user_id': user_id, 'name': 'John'}

def list_users(limit: int = 10) -> list:
    return [{'user_id': str(i)} for i in range(limit)]

def create_user(name: str, email: str) -> dict:
    return {'user_id': '123', 'name': name, 'email': email}

def update_user(user_id: str, name: str) -> dict:
    return {'user_id': user_id, 'name': name}

def delete_user(user_id: str) -> dict:
    return {'user_id': user_id, 'deleted': True}

app = mk_app([get_user, list_users, create_user, update_user, delete_user],
             use_conventions=True)
```

**Automatic routes created:**
- `GET /users/{user_id}` → `get_user(user_id)`
- `GET /users?limit=10` → `list_users(limit=10)`
- `POST /users` → `create_user(name, email)`
- `PUT /users/{user_id}` → `update_user(user_id, name)`
- `DELETE /users/{user_id}` → `delete_user(user_id)`

**Convention patterns:**
- `get_{resource}(id)` → GET `/{resource}s/{id}`
- `list_{resource}()` → GET `/{resource}s`
- `create_{resource}()` → POST `/{resource}s`
- `update_{resource}(id)` → PUT `/{resource}s/{id}`
- `delete_{resource}(id)` → DELETE `/{resource}s/{id}`

## Custom Configuration

### Per-Function Configuration

Customize individual functions:

```python
from qh import mk_app

def health_check() -> dict:
    return {'status': 'healthy'}

def analyze_text(text: str) -> dict:
    return {'length': len(text), 'words': len(text.split())}

app = mk_app({
    health_check: {
        'path': '/health',
        'methods': ['GET'],
        'tags': ['monitoring']
    },
    analyze_text: {
        'path': '/analyze',
        'methods': ['POST'],
        'tags': ['text-processing']
    }
})
```

### Transform Rules

Control how parameters are handled with multi-dimensional rules:

```python
from qh import mk_app, mk_rules
from qh.transform_utils import TransformSpec, HttpLocation

# Global rules apply to all functions
rules = mk_rules({
    'user_id': TransformSpec(http_location=HttpLocation.PATH),
    'api_key': TransformSpec(http_location=HttpLocation.HEADER),
})

def get_user_data(user_id: str, api_key: str) -> dict:
    return {'user_id': user_id, 'authorized': True}

app = mk_app([get_user_data], rules=rules)
```

Now `user_id` comes from the URL path and `api_key` from headers automatically.

## Type System

### Built-in Types

qh handles all standard Python types:

```python
from typing import List, Dict, Optional, Union
from datetime import datetime, date, time
from enum import Enum

class Status(Enum):
    PENDING = "pending"
    ACTIVE = "active"
    COMPLETED = "completed"

def complex_function(
    integers: List[int],
    mapping: Dict[str, float],
    optional_date: Optional[date],
    status: Status,
    union_type: Union[int, str]
) -> dict:
    return {
        'sum': sum(integers),
        'avg_value': sum(mapping.values()) / len(mapping),
        'status': status.value
    }

app = mk_app([complex_function])
```

### Custom Types

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

    def distance_from_origin(self):
        return (self.x ** 2 + self.y ** 2) ** 0.5

def create_point(x: float, y: float) -> Point:
    return Point(x, y)

def calculate_distance(point: Point) -> float:
    return point.distance_from_origin()

app = mk_app([create_point, calculate_distance])
```

**Usage:**
```bash
# Create point
curl -X POST http://localhost:8000/create_point \
  -H 'Content-Type: application/json' \
  -d '{"x": 3.0, "y": 4.0}'
# Returns: {"x": 3.0, "y": 4.0}

# Calculate distance
curl -X POST http://localhost:8000/calculate_distance \
  -H 'Content-Type: application/json' \
  -d '{"point": {"x": 3.0, "y": 4.0}}'
# Returns: 5.0
```

### Custom Serializers

Use custom serialization logic:

```python
from qh import register_type
import numpy as np

# Custom serializer for numpy arrays
register_type(
    np.ndarray,
    to_json=lambda arr: arr.tolist(),
    from_json=lambda data: np.array(data)
)

def matrix_multiply(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    return np.matmul(a, b)

app = mk_app([matrix_multiply])
```

## Client Generation

### Python Clients

Generate Python clients from your API:

```python
from qh import mk_app, export_openapi
from qh.client import mk_client_from_app

# Create the API
def add(x: int, y: int) -> int:
    return x + y

def multiply(x: int, y: int) -> int:
    return x * y

app = mk_app([add, multiply])

# Generate client
client = mk_client_from_app(app)

# Use the client (looks like calling Python functions!)
result = client.add(x=3, y=5)
print(result)  # 8

result = client.multiply(x=4, y=7)
print(result)  # 28
```

**From a running server:**
```python
from qh.client import mk_client_from_url

# Connect to running API
client = mk_client_from_url('http://localhost:8000/openapi.json')
result = client.add(x=10, y=20)
```

### TypeScript Clients

Generate TypeScript clients with full type safety:

```python
from qh import mk_app, export_openapi
from qh.jsclient import export_ts_client

def add(x: int, y: int) -> int:
    """Add two numbers."""
    return x + y

app = mk_app([add])
spec = export_openapi(app, include_python_metadata=True)

# Generate TypeScript client
ts_code = export_ts_client(spec, class_name="MathClient", use_axios=True)

# Save to file
with open('client.ts', 'w') as f:
    f.write(ts_code)
```

**Generated TypeScript:**
```typescript
import axios, { AxiosInstance } from 'axios';

export interface AddParams {
  x: number;
  y: number;
}

/**
 * Generated API client
 */
export class MathClient {
  private baseUrl: string;
  private axios: AxiosInstance;

  constructor(baseUrl: string = 'http://localhost:8000') {
    this.baseUrl = baseUrl;
    this.axios = axios.create({ baseURL: baseUrl });
  }

  /**
   * Add two numbers.
   */
  async add(x: number, y: number): Promise<number> {
    const data = { x, y };
    const response = await this.axios.post<number>('/add', data);
    return response.data;
  }
}
```

**Usage in TypeScript:**
```typescript
const client = new MathClient('http://localhost:8000');
const result = await client.add(3, 5);  // Type-safe!
```

### JavaScript Clients

Generate JavaScript clients (with or without axios):

```python
from qh.jsclient import export_js_client

js_code = export_js_client(
    spec,
    class_name="ApiClient",
    use_axios=False  # Use fetch instead
)
```

## OpenAPI Integration

### Enhanced OpenAPI Export

Export OpenAPI specs with Python-specific metadata:

```python
from qh import mk_app, export_openapi

def add(x: int, y: int = 10) -> int:
    """Add two numbers together."""
    return x + y

app = mk_app([add])

# Export with Python metadata
spec = export_openapi(
    app,
    include_python_metadata=True,
    include_examples=True
)

# Save to file
export_openapi(app, output_file='openapi.json')
```

**The spec includes:**
- Standard OpenAPI 3.0 schema
- `x-python-signature` extensions with:
  - Function names
  - Parameter types and defaults
  - Return types
  - Docstrings
- Request/response examples
- Full type information

### Accessing OpenAPI

Every qh app automatically provides:

- `/openapi.json` - OpenAPI specification
- `/docs` - Swagger UI interactive documentation
- `/redoc` - ReDoc documentation

## Store/Mall Pattern

qh includes built-in support for the Store/Mall pattern from the `dol` library:

```python
from qh import mall_to_qh

# Create a mall (multi-level store)
class UserPreferences:
    def __init__(self):
        self._data = {}

    def __getitem__(self, user_id):
        if user_id not in self._data:
            self._data[user_id] = {}
        return self._data[user_id]

    def __setitem__(self, user_id, value):
        self._data[user_id] = value

    def __delitem__(self, user_id):
        del self._data[user_id]

    def __iter__(self):
        return iter(self._data)

mall = UserPreferences()

# Convert to HTTP endpoints
app = mall_to_qh(
    mall,
    get_obj=lambda user_id: mall[user_id],
    base_path='/users/{user_id}/preferences',
    tags=['user-preferences']
)
```

**Automatic endpoints:**
- `GET /users/{user_id}/preferences` - List all preferences for user
- `GET /users/{user_id}/preferences/{key}` - Get specific preference
- `PUT /users/{user_id}/preferences/{key}` - Set preference
- `DELETE /users/{user_id}/preferences/{key}` - Delete preference

## Testing

### Quick Testing

Test a single function instantly:

```python
from qh.testing import quick_test

def add(x: int, y: int) -> int:
    return x + y

result = quick_test(add, x=3, y=5)
assert result == 8
```

### TestClient

Use FastAPI's TestClient for fast unit tests:

```python
from qh import mk_app
from qh.testing import test_app

def add(x: int, y: int) -> int:
    return x + y

app = mk_app([add])

with test_app(app) as client:
    response = client.post('/add', json={'x': 3, 'y': 5})
    assert response.status_code == 200
    assert response.json() == 8
```

### Integration Testing

Test with a real uvicorn server:

```python
from qh.testing import serve_app
import requests

app = mk_app([add])

with serve_app(app, port=8001) as url:
    response = requests.post(f'{url}/add', json={'x': 3, 'y': 5})
    assert response.json() == 8
```

### Round-Trip Testing

Verify functions work identically through HTTP:

```python
from qh import mk_app, mk_client_from_app

def calculate(x: int, y: int) -> int:
    return x * y + x

# Direct call
direct = calculate(3, 5)

# HTTP call
app = mk_app([calculate])
client = mk_client_from_app(app)
http_result = client.calculate(x=3, y=5)

assert direct == http_result  # Perfect fidelity!
```

## Advanced Features

### Error Handling

qh automatically handles errors and returns appropriate HTTP status codes:

```python
def divide(x: float, y: float) -> float:
    if y == 0:
        raise ValueError("Cannot divide by zero")
    return x / y

app = mk_app([divide])
```

**Request with y=0:**
```json
{
    "detail": "Cannot divide by zero"
}
```
Status: 500

### Default Values

Function defaults work as expected:

```python
def greet(name: str = "World", title: str = "Mr.") -> str:
    return f"Hello, {title} {name}!"

app = mk_app([greet])
```

**All valid requests:**
```bash
curl -X POST http://localhost:8000/greet -d '{}'
# "Hello, Mr. World!"

curl -X POST http://localhost:8000/greet -d '{"name": "Alice"}'
# "Hello, Mr. Alice!"

curl -X POST http://localhost:8000/greet -d '{"name": "Alice", "title": "Dr."}'
# "Hello, Dr. Alice!"
```

### Docstrings as Descriptions

Function and parameter docstrings become API documentation:

```python
def analyze_sentiment(text: str) -> dict:
    """
    Analyze the sentiment of the given text.

    Args:
        text: The text to analyze for sentiment

    Returns:
        Dictionary with sentiment score and label
    """
    # ... implementation ...
    return {'score': 0.8, 'label': 'positive'}

app = mk_app([analyze_sentiment])
```

The docstring appears in `/docs` and OpenAPI spec automatically.

### Route Inspection

Inspect created routes:

```python
from qh import mk_app, print_routes, get_routes

app = mk_app([add, multiply, greet])

# Print to console
print_routes(app)

# Get as list
routes = get_routes(app)
for route in routes:
    print(f"{route['methods']} {route['path']} -> {route['name']}")
```

### Middleware and Dependencies

Use FastAPI middleware and dependencies:

```python
from qh import mk_app
from fastapi import Depends, Header

def verify_token(x_api_key: str = Header(...)):
    if x_api_key != "secret":
        raise HTTPException(401, "Invalid API key")
    return x_api_key

def protected_operation(value: int, token: str = Depends(verify_token)) -> int:
    return value * 2

app = mk_app([protected_operation])

# Add middleware
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
)
```

## Best Practices

### 1. Type Annotations

Always use type annotations for best results:

```python
# Good - types are validated
def add(x: int, y: int) -> int:
    return x + y

# Works but no validation
def add(x, y):
    return x + y
```

### 2. Descriptive Names

Use clear function names, especially with conventions:

```python
# Good - clear and follows conventions
def get_user(user_id: str) -> dict:
    pass

def list_orders(user_id: str, limit: int = 10) -> list:
    pass

# Avoid - unclear intent
def fetch(id: str) -> dict:
    pass
```

### 3. Custom Types for Complex Data

Use custom types for domain objects:

```python
from qh import register_json_type

@register_json_type
class Order:
    def __init__(self, order_id: str, items: list, total: float):
        self.order_id = order_id
        self.items = items
        self.total = total

    def to_dict(self):
        return {
            'order_id': self.order_id,
            'items': self.items,
            'total': self.total
        }

    @classmethod
    def from_dict(cls, data):
        return cls(**data)

def create_order(items: list, total: float) -> Order:
    return Order("ORD123", items, total)
```

### 4. Test Round-Trips

Always test that functions work identically through HTTP:

```python
def test_add_roundtrip():
    def add(x: int, y: int) -> int:
        return x + y

    # Direct
    direct = add(3, 5)

    # Through HTTP
    app = mk_app([add])
    client = mk_client_from_app(app)
    http_result = client.add(x=3, y=5)

    assert direct == http_result
```

### 5. Documentation

Add docstrings to all public functions:

```python
def calculate_tax(amount: float, rate: float = 0.08) -> float:
    """
    Calculate tax on a given amount.

    Args:
        amount: The base amount to calculate tax on
        rate: The tax rate as a decimal (default: 0.08 for 8%)

    Returns:
        The calculated tax amount
    """
    return amount * rate
```

## Summary

qh provides:

- **Zero boilerplate** - Plain Python functions become HTTP APIs
- **Convention over configuration** - Smart defaults with full customization
- **Full type safety** - From Python through HTTP back to Python/TypeScript
- **Client generation** - Automatic Python, JavaScript, TypeScript clients
- **Testing utilities** - Fast unit tests and integration tests
- **OpenAPI integration** - Automatic documentation and metadata
- **Extensible** - Custom types, transforms, middleware

Perfect for:
- Rapid prototyping
- Microservices
- Internal APIs
- API-first development
- Python-to-web transformations
