# qh API Reference

Complete API reference for qh - the convention-over-configuration HTTP framework.

## Table of Contents

- [Core Functions](#core-functions)
- [Client Generation](#client-generation)
- [OpenAPI Export](#openapi-export)
- [Testing Utilities](#testing-utilities)
- [Type Registration](#type-registration)
- [Transform System](#transform-system)
- [Store/Mall Integration](#storemall-integration)
- [Utilities](#utilities)

## Core Functions

### mk_app

```python
def mk_app(
    functions: Union[List[Callable], Dict[Callable, Dict]],
    *,
    rules: Optional[Dict] = None,
    use_conventions: bool = False,
    title: str = "qh API",
    version: str = "0.1.0",
    **fastapi_kwargs
) -> FastAPI
```

Create a FastAPI application from Python functions.

**Parameters:**
- `functions`: List of functions or dict mapping functions to configs
- `rules`: Optional transform rules (created with `mk_rules()`)
- `use_conventions`: Enable convention-based RESTful routing
- `title`: API title for OpenAPI docs
- `version`: API version
- `**fastapi_kwargs`: Additional FastAPI constructor arguments

**Returns:**
- `FastAPI`: Configured FastAPI application

**Examples:**

```python
# Simple list of functions
from qh import mk_app

def add(x: int, y: int) -> int:
    return x + y

app = mk_app([add])
```

```python
# With custom configuration per function
app = mk_app({
    add: {
        'path': '/calculate/add',
        'methods': ['POST'],
        'tags': ['math']
    }
})
```

```python
# With conventions
def get_user(user_id: str) -> dict:
    return {'user_id': user_id}

app = mk_app([get_user], use_conventions=True)
# Creates: GET /users/{user_id}
```

### Function Configuration

When passing a dict to `mk_app`, each function can have a config dict with:

**Configuration Keys:**
- `path` (str): Custom URL path (default: `/{function_name}`)
- `methods` (List[str]): HTTP methods (default: `['POST']`)
- `tags` (List[str]): OpenAPI tags for grouping
- `name` (str): Custom operation name
- `summary` (str): Short description
- `description` (str): Detailed description
- `response_model`: Pydantic model for response
- `status_code` (int): HTTP status code (default: 200)
- `param_overrides` (Dict): Per-parameter transform specs

**Example:**

```python
app = mk_app({
    get_user: {
        'path': '/users/{user_id}',
        'methods': ['GET'],
        'tags': ['users'],
        'summary': 'Get user by ID',
        'description': 'Retrieve detailed information about a specific user',
        'status_code': 200
    }
})
```

## Client Generation

### mk_client_from_app

```python
def mk_client_from_app(
    app: FastAPI,
    base_url: str = "http://testserver"
) -> HttpClient
```

Create a Python client from a FastAPI app (for testing).

**Parameters:**
- `app`: FastAPI application
- `base_url`: Base URL for requests (default for TestClient)

**Returns:**
- `HttpClient`: Client with callable functions

**Example:**

```python
from qh import mk_app
from qh.client import mk_client_from_app

def add(x: int, y: int) -> int:
    return x + y

app = mk_app([add])
client = mk_client_from_app(app)

# Call like a Python function
result = client.add(x=3, y=5)  # Returns: 8
```

### mk_client_from_openapi

```python
def mk_client_from_openapi(
    openapi_spec: Dict[str, Any],
    base_url: str = "http://localhost:8000",
    session: Optional[requests.Session] = None
) -> HttpClient
```

Create a client from an OpenAPI specification dictionary.

**Parameters:**
- `openapi_spec`: OpenAPI spec dictionary
- `base_url`: Base URL for API requests
- `session`: Optional requests Session for connection pooling

**Returns:**
- `HttpClient`: Client with callable functions

**Example:**

```python
from qh.client import mk_client_from_openapi
import json

with open('openapi.json') as f:
    spec = json.load(f)

client = mk_client_from_openapi(spec, 'http://localhost:8000')
result = client.add(x=10, y=20)
```

### mk_client_from_url

```python
def mk_client_from_url(
    openapi_url: str,
    base_url: Optional[str] = None,
    session: Optional[requests.Session] = None
) -> HttpClient
```

Create a client by fetching OpenAPI spec from a URL.

**Parameters:**
- `openapi_url`: URL to OpenAPI JSON (e.g., `http://localhost:8000/openapi.json`)
- `base_url`: Base URL for requests (inferred from `openapi_url` if not provided)
- `session`: Optional requests Session

**Returns:**
- `HttpClient`: Client with callable functions

**Example:**

```python
from qh.client import mk_client_from_url

# Connect to running server
client = mk_client_from_url('http://localhost:8000/openapi.json')
result = client.add(x=5, y=7)
```

### HttpClient

```python
class HttpClient:
    def __init__(self, base_url: str, session: Optional[requests.Session] = None)
    def add_function(self, name: str, path: str, method: str,
                     signature_info: Optional[Dict] = None)
```

HTTP client that provides Python function interface to HTTP endpoints.

**Methods:**
- `__init__(base_url, session=None)`: Initialize client
- `add_function(name, path, method, signature_info=None)`: Add callable function
- Functions are accessible as attributes: `client.function_name(**kwargs)`

**Example:**

```python
from qh.client import HttpClient

client = HttpClient('http://localhost:8000')
client.add_function('add', '/add', 'POST')

result = client.add(x=3, y=5)
```

## OpenAPI Export

### export_openapi

```python
def export_openapi(
    app: FastAPI,
    *,
    include_examples: bool = True,
    include_python_metadata: bool = True,
    include_transformers: bool = False,
    output_file: Optional[str] = None
) -> Dict[str, Any]
```

Export enhanced OpenAPI schema with Python-specific extensions.

**Parameters:**
- `app`: FastAPI application
- `include_examples`: Include request/response examples
- `include_python_metadata`: Include `x-python-signature` extensions
- `include_transformers`: Include transformer information (advanced)
- `output_file`: Optional path to save JSON file

**Returns:**
- `Dict[str, Any]`: OpenAPI specification dictionary

**Example:**

```python
from qh import mk_app, export_openapi

app = mk_app([add, multiply])

# Get spec as dict
spec = export_openapi(app, include_python_metadata=True)

# Or save to file
export_openapi(app, output_file='api-spec.json')
```

**x-python-signature Extension:**

When `include_python_metadata=True`, each operation includes:

```json
{
  "x-python-signature": {
    "name": "add",
    "module": "__main__",
    "parameters": [
      {
        "name": "x",
        "type": "int",
        "required": true
      },
      {
        "name": "y",
        "type": "int",
        "required": false,
        "default": 10
      }
    ],
    "return_type": "int",
    "docstring": "Add two numbers."
  }
}
```

### export_js_client

```python
def export_js_client(
    openapi_spec: Dict[str, Any],
    *,
    class_name: str = "ApiClient",
    use_axios: bool = False,
    base_url: str = "http://localhost:8000"
) -> str
```

Generate JavaScript client class from OpenAPI spec.

**Parameters:**
- `openapi_spec`: OpenAPI specification dictionary
- `class_name`: Name for generated class
- `use_axios`: Use axios instead of fetch
- `base_url`: Default base URL

**Returns:**
- `str`: JavaScript code

**Example:**

```python
from qh import mk_app, export_openapi
from qh.jsclient import export_js_client

app = mk_app([add])
spec = export_openapi(app, include_python_metadata=True)

js_code = export_js_client(spec, class_name="MathClient", use_axios=True)

with open('client.js', 'w') as f:
    f.write(js_code)
```

### export_ts_client

```python
def export_ts_client(
    openapi_spec: Dict[str, Any],
    *,
    class_name: str = "ApiClient",
    use_axios: bool = False,
    base_url: str = "http://localhost:8000"
) -> str
```

Generate TypeScript client class from OpenAPI spec.

**Parameters:**
- `openapi_spec`: OpenAPI specification dictionary
- `class_name`: Name for generated class
- `use_axios`: Use axios instead of fetch
- `base_url`: Default base URL

**Returns:**
- `str`: TypeScript code with type annotations

**Example:**

```python
from qh.jsclient import export_ts_client

ts_code = export_ts_client(
    spec,
    class_name="MathClient",
    use_axios=True
)

with open('client.ts', 'w') as f:
    f.write(ts_code)
```

## Testing Utilities

### test_app

```python
@contextmanager
def test_app(app: FastAPI)
```

Context manager for testing with TestClient (fast, synchronous).

**Parameters:**
- `app`: FastAPI application

**Yields:**
- `TestClient`: FastAPI TestClient instance

**Example:**

```python
from qh import mk_app
from qh.testing import test_app

app = mk_app([add])

with test_app(app) as client:
    response = client.post('/add', json={'x': 3, 'y': 5})
    assert response.status_code == 200
    assert response.json() == 8
```

### serve_app

```python
@contextmanager
def serve_app(
    app: FastAPI,
    port: int = 8000,
    host: str = "127.0.0.1"
)
```

Context manager for integration testing with real uvicorn server.

**Parameters:**
- `app`: FastAPI application
- `port`: Port to bind to
- `host`: Host to bind to

**Yields:**
- `str`: Base URL (e.g., "http://127.0.0.1:8000")

**Example:**

```python
from qh.testing import serve_app
import requests

app = mk_app([add])

with serve_app(app, port=8001) as url:
    response = requests.post(f'{url}/add', json={'x': 3, 'y': 5})
    assert response.json() == 8
# Server automatically stops after context
```

### run_app

```python
@contextmanager
def run_app(
    app: FastAPI,
    *,
    use_server: bool = False,
    **kwargs
)
```

Flexible context manager that can use TestClient or real server.

**Parameters:**
- `app`: FastAPI application
- `use_server`: If True, runs real server; if False, uses TestClient
- `**kwargs`: Additional arguments passed to AppRunner

**Yields:**
- `TestClient` if `use_server=False`, or base URL string if `use_server=True`

**Example:**

```python
from qh.testing import run_app

# Fast testing with TestClient
with run_app(app) as client:
    result = client.post('/add', json={'x': 3, 'y': 5})

# Integration testing with real server
with run_app(app, use_server=True, port=8001) as url:
    import requests
    result = requests.post(f'{url}/add', json={'x': 3, 'y': 5})
```

### AppRunner

```python
class AppRunner:
    def __init__(
        self,
        app: FastAPI,
        *,
        use_server: bool = False,
        host: str = "127.0.0.1",
        port: int = 8000,
        server_timeout: float = 2.0
    )
```

Context manager for running FastAPI app in test mode or with real server.

**Parameters:**
- `app`: FastAPI application
- `use_server`: Use real server instead of TestClient
- `host`: Host to bind to (server mode only)
- `port`: Port to bind to (server mode only)
- `server_timeout`: Seconds to wait for server startup

**Example:**

```python
from qh.testing import AppRunner

# TestClient mode
with AppRunner(app) as client:
    response = client.post('/add', json={'x': 3, 'y': 5})

# Server mode
with AppRunner(app, use_server=True, port=9000) as url:
    import requests
    response = requests.post(f'{url}/add', json={'x': 3, 'y': 5})
```

### quick_test

```python
def quick_test(func: Callable, **kwargs) -> Any
```

Quick test helper for a single function.

**Parameters:**
- `func`: Function to test
- `**kwargs`: Arguments to pass to the function

**Returns:**
- Response from calling the function through HTTP

**Example:**

```python
from qh.testing import quick_test

def add(x: int, y: int) -> int:
    return x + y

result = quick_test(add, x=3, y=5)
assert result == 8
```

## Type Registration

### register_type

```python
def register_type(
    type_: Type[T],
    *,
    to_json: Optional[Callable[[T], Any]] = None,
    from_json: Optional[Callable[[Any], T]] = None
)
```

Register a custom type with serialization functions.

**Parameters:**
- `type_`: The type to register
- `to_json`: Function to convert type to JSON-serializable value
- `from_json`: Function to convert JSON value back to type

**Example:**

```python
from qh import register_type
import numpy as np

register_type(
    np.ndarray,
    to_json=lambda arr: arr.tolist(),
    from_json=lambda data: np.array(data)
)

def matrix_op(matrix: np.ndarray) -> np.ndarray:
    return matrix * 2

app = mk_app([matrix_op])
```

### register_json_type

```python
def register_json_type(
    cls: Optional[Type[T]] = None,
    *,
    to_json: Optional[Callable[[T], Any]] = None,
    from_json: Optional[Callable[[Any], T]] = None
)
```

Decorator to register a custom type (auto-detects `to_dict`/`from_dict`).

**Parameters:**
- `cls`: Class to register (when used without parentheses)
- `to_json`: Optional custom serializer
- `from_json`: Optional custom deserializer

**Example:**

```python
from qh import register_json_type

@register_json_type
class Point:
    def __init__(self, x: float, y: float):
        self.x = x
        self.y = y

    def to_dict(self):  # Auto-detected
        return {'x': self.x, 'y': self.y}

    @classmethod
    def from_dict(cls, data):  # Auto-detected
        return cls(data['x'], data['y'])

# Or with custom functions
@register_json_type(
    to_json=lambda p: [p.x, p.y],
    from_json=lambda d: Point(d[0], d[1])
)
class Point2:
    def __init__(self, x: float, y: float):
        self.x = x
        self.y = y
```

## Transform System

### mk_rules

```python
def mk_rules(rules_dict: Dict[str, TransformSpec]) -> Dict
```

Create transform rules for parameter handling.

**Parameters:**
- `rules_dict`: Dict mapping parameter names to TransformSpec objects

**Returns:**
- `Dict`: Rules dict to pass to `mk_app()`

**Example:**

```python
from qh import mk_app, mk_rules
from qh.transform_utils import TransformSpec, HttpLocation

rules = mk_rules({
    'user_id': TransformSpec(http_location=HttpLocation.PATH),
    'api_key': TransformSpec(http_location=HttpLocation.HEADER),
})

def get_data(user_id: str, api_key: str) -> dict:
    return {'user_id': user_id, 'authorized': True}

app = mk_app([get_data], rules=rules)
# user_id from path, api_key from headers
```

### TransformSpec

```python
@dataclass
class TransformSpec:
    http_location: Optional[HttpLocation] = None
    ingress: Optional[Callable] = None
    egress: Optional[Callable] = None
```

Specification for parameter transformation.

**Attributes:**
- `http_location`: Where parameter comes from (PATH, QUERY, HEADER, BODY)
- `ingress`: Function to transform HTTP → Python
- `egress`: Function to transform Python → HTTP

**Example:**

```python
from qh.transform_utils import TransformSpec, HttpLocation

# Custom type conversion
def parse_date(s: str) -> datetime:
    return datetime.fromisoformat(s)

def format_date(d: datetime) -> str:
    return d.isoformat()

spec = TransformSpec(
    http_location=HttpLocation.QUERY,
    ingress=parse_date,
    egress=format_date
)
```

### HttpLocation

```python
class HttpLocation(Enum):
    PATH = "path"
    QUERY = "query"
    HEADER = "header"
    BODY = "body"
```

Enum for specifying where parameters come from in HTTP requests.

## Store/Mall Integration

### mall_to_qh

```python
def mall_to_qh(
    mall_or_store,
    *,
    get_obj: Optional[Callable] = None,
    base_path: str = "/store",
    tags: Optional[List[str]] = None,
    **kwargs
) -> FastAPI
```

Convert a Store or Mall (from `dol`) to HTTP endpoints.

**Parameters:**
- `mall_or_store`: Store or Mall object
- `get_obj`: Function to get object from path parameters
- `base_path`: Base path for endpoints
- `tags`: OpenAPI tags
- `**kwargs`: Additional configuration

**Returns:**
- `FastAPI`: Application with CRUD endpoints

**Example:**

```python
from qh import mall_to_qh

class UserStore:
    def __init__(self):
        self._data = {}

    def __getitem__(self, key):
        return self._data[key]

    def __setitem__(self, key, value):
        self._data[key] = value

    def __delitem__(self, key):
        del self._data[key]

    def __iter__(self):
        return iter(self._data)

store = UserStore()

app = mall_to_qh(
    store,
    get_obj=lambda: store,
    base_path='/users',
    tags=['users']
)

# Creates endpoints:
# GET /users - list all
# GET /users/{key} - get one
# PUT /users/{key} - set value
# DELETE /users/{key} - delete
```

## Utilities

### print_routes

```python
def print_routes(app: FastAPI) -> None
```

Print all routes in the application to console.

**Parameters:**
- `app`: FastAPI application

**Example:**

```python
from qh import mk_app, print_routes

app = mk_app([add, multiply])
print_routes(app)

# Output:
# POST /add -> add
# POST /multiply -> multiply
```

### get_routes

```python
def get_routes(app: FastAPI) -> List[Dict[str, Any]]
```

Get list of all routes in the application.

**Parameters:**
- `app`: FastAPI application

**Returns:**
- `List[Dict]`: List of route information dicts

**Example:**

```python
from qh import mk_app, get_routes

app = mk_app([add])
routes = get_routes(app)

for route in routes:
    print(f"{route['methods']} {route['path']} -> {route['name']}")
```

### python_type_to_ts_type

```python
def python_type_to_ts_type(python_type: str) -> str
```

Convert Python type annotation to TypeScript type.

**Parameters:**
- `python_type`: Python type as string (e.g., "int", "List[str]")

**Returns:**
- `str`: TypeScript type string

**Example:**

```python
from qh.jsclient import python_type_to_ts_type

python_type_to_ts_type("int")  # "number"
python_type_to_ts_type("str")  # "string"
python_type_to_ts_type("list[int]")  # "number[]"
python_type_to_ts_type("Optional[str]")  # "string | null"
python_type_to_ts_type("dict")  # "Record<string, any>"
```

## Constants

### Default Values

```python
DEFAULT_HTTP_METHOD = 'POST'
DEFAULT_PATH_PREFIX = '/'
DEFAULT_STATUS_CODE = 200
```

## Type Aliases

```python
from typing import Callable, Dict, List, Any, Optional, Union

# Common type aliases used throughout qh
FunctionConfig = Dict[str, Any]
OpenAPISpec = Dict[str, Any]
RouteConfig = Dict[str, Any]
TransformRules = Dict[str, Any]
```

## Error Handling

### HTTPException

qh uses FastAPI's `HTTPException` for errors:

```python
from fastapi import HTTPException

def get_user(user_id: str) -> dict:
    if user_id not in users:
        raise HTTPException(status_code=404, detail="User not found")
    return users[user_id]
```

### Automatic Error Handling

Python exceptions are automatically converted to HTTP errors:

```python
def divide(x: float, y: float) -> float:
    if y == 0:
        raise ValueError("Cannot divide by zero")
    return x / y

# ValueError becomes HTTP 500 with error detail
```

## Convention Patterns

When `use_conventions=True`, these patterns are recognized:

| Pattern | HTTP Method | Path | Example |
|---------|-------------|------|---------|
| `get_{resource}(id)` | GET | `/{resource}s/{id}` | `get_user(user_id)` → `GET /users/{user_id}` |
| `list_{resource}()` | GET | `/{resource}s` | `list_users()` → `GET /users` |
| `create_{resource}()` | POST | `/{resource}s` | `create_user(name)` → `POST /users` |
| `update_{resource}(id)` | PUT | `/{resource}s/{id}` | `update_user(user_id)` → `PUT /users/{user_id}` |
| `delete_{resource}(id)` | DELETE | `/{resource}s/{id}` | `delete_user(user_id)` → `DELETE /users/{user_id}` |

## Version Information

```python
import qh

print(qh.__version__)  # Get qh version
```

## See Also

- [Getting Started Guide](GETTING_STARTED.md)
- [Features Guide](FEATURES.md)
- [Testing Guide](TESTING.md)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
