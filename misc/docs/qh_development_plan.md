# qh Development Plan: Convention Over Configuration for HTTP Services

## Executive Summary

Transform `qh` into a clean, robust, and boilerplate-free tool for bidirectional Python ↔ HTTP service transformation using FastAPI exclusively. The goal is to provide a superior alternative to py2http with:
- **Convention over configuration**: Smart defaults with escape hatches
- **FastAPI-native**: No framework abstraction, direct FastAPI integration
- **Bidirectional transformation**: Functions → HTTP services → Functions (via OpenAPI)
- **Type-aware**: Leverage Python's type system for automatic validation and serialization
- **Store/Object dispatch**: First-class support for exposing objects and stores as services

---

## Part 1: Core Architecture Refactoring

### 1.1 Unify the API Surface

**Current Problem**: qh has multiple entry points with inconsistent patterns:
- `qh/main.py`: Uses py2http's `mk_app`
- `qh/base.py`: Has `mk_fastapi_app` with `_mk_endpoint`
- `qh/core.py`: Has another `mk_fastapi_app` with Wrap pattern
- `qh/stores_qh.py`: Specialized store dispatching

**Solution**: Create a single, unified API in `qh/app.py`:

```python
# Primary API: qh.app.mk_app
from qh import mk_app

# Simple case: just functions
app = mk_app([foo, bar, baz])

# With configuration
app = mk_app(
    funcs=[foo, bar],
    config={
        'input_trans': {...},
        'output_trans': {...},
        'path_template': '/api/{func_name}',
    }
)

# Dict-based for per-function config
app = mk_app({
    foo: {'methods': ['GET'], 'path': '/foo/{x}'},
    bar: {'methods': ['POST', 'PUT']},
})
```

### 1.2 Configuration Schema

Adopt the wip_qh refactoring pattern with a clear configuration hierarchy:

```python
# Global defaults
DEFAULT_CONFIG = {
    'methods': ['POST'],
    'path_template': '/{func_name}',
    'input_trans': smart_json_ingress,  # Auto-detect types
    'output_trans': smart_json_egress,  # Auto-serialize
    'error_handler': standard_error_handler,
    'tags': None,
    'summary': lambda f: f.__doc__.split('\n')[0] if f.__doc__ else None,
}

# Per-function config overrides
RouteConfig = TypedDict('RouteConfig', {
    'path': str,
    'methods': List[str],
    'input_trans': Callable,
    'output_trans': Callable,
    'defaults': Dict[str, Any],
    'summary': str,
    'tags': List[str],
    'response_model': Type,
})
```

### 1.3 Smart Type Inference

**Current Problem**: Manual input/output transformers required for non-JSON types

**Solution**: Auto-generate transformers from type hints:

```python
from typing import Annotated
import numpy as np
from pathlib import Path

def process_image(
    image: Annotated[np.ndarray, "image/jpeg"],  # Auto-detect from annotation
    threshold: float = 0.5
) -> dict[str, Any]:
    ...

# qh auto-generates:
# - Input transformer: base64 → np.ndarray
# - Output transformer: dict → JSON
# - OpenAPI spec with proper types
```

Implementation in `qh/types.py`:
- Type registry mapping Python types to HTTP representations
- Automatic serializer/deserializer generation
- Support for custom types via registration

---

## Part 2: Convention-Over-Configuration Patterns

### 2.1 Intelligent Path Generation

Learn from function signatures to generate RESTful paths:

```python
def get_user(user_id: str) -> User:
    """Automatically becomes GET /users/{user_id}"""

def list_users(limit: int = 100) -> List[User]:
    """Automatically becomes GET /users?limit=100"""

def create_user(user: User) -> User:
    """Automatically becomes POST /users"""

def update_user(user_id: str, user: User) -> User:
    """Automatically becomes PUT /users/{user_id}"""

def delete_user(user_id: str) -> None:
    """Automatically becomes DELETE /users/{user_id}"""
```

Implementation in `qh/conventions.py`:
- Function name parsing (verb + resource pattern)
- Signature analysis for path vs query parameters
- HTTP method inference from verb (get/list/create/update/delete)

### 2.2 Request Parameter Resolution

Smart parameter binding from multiple sources:

```python
async def endpoint(request: Request):
    params = {}

    # 1. Path parameters (highest priority)
    params.update(request.path_params)

    # 2. Query parameters (for GET)
    if request.method == 'GET':
        params.update(request.query_params)

    # 3. JSON body (for POST/PUT)
    if request.method in ['POST', 'PUT', 'PATCH']:
        params.update(await request.json())

    # 4. Form data (multipart)
    # 5. Headers (for special cases)

    # 6. Apply defaults from signature
    # 7. Apply transformations
    # 8. Validate required parameters
```

### 2.3 Store/Object Dispatch

Elevate the current `stores_qh.py` patterns to first-class citizens:

```python
from qh import mk_store_app, mk_object_app
from dol import Store

# Expose a store factory
app = mk_store_app(
    store_factory=lambda uri: Store(uri),
    methods=['list', 'read', 'write', 'delete'],  # or '__iter__', '__getitem__', etc.
    auth=require_token,
)

# Expose an object's methods
class DataService:
    def get_data(self, key: str) -> bytes: ...
    def put_data(self, key: str, data: bytes): ...

app = mk_object_app(
    obj_factory=lambda user_id: DataService(user_id),
    methods=['get_data', 'put_data'],
    base_path='/users/{user_id}/data',
)
```

---

## Part 3: OpenAPI & Bidirectional Transformation

### 3.1 Enhanced OpenAPI Generation

**Goal**: Generate OpenAPI specs that enable perfect round-tripping

```python
from qh import mk_app, export_openapi

app = mk_app([foo, bar, baz])

# Export with all metadata needed for reconstruction
spec = export_openapi(
    app,
    include_examples=True,
    include_schemas=True,
    x_python_types=True,  # Extension: original Python types
    x_transformers=True,  # Extension: serialization hints
)
```

Extensions to standard OpenAPI:
- `x-python-signature`: Full signature with defaults
- `x-python-module`: Module path for import
- `x-python-transformers`: Type transformation specs
- `x-python-examples`: Generated test cases

### 3.2 HTTP → Python (http2py integration)

Generate client-side Python functions from OpenAPI:

```python
from qh.client import mk_client_from_openapi

# From URL
client = mk_client_from_openapi('http://api.example.com/openapi.json')

# client.foo(x=3) → makes HTTP request → returns result
# Signature matches original function!
assert inspect.signature(client.foo) == inspect.signature(original_foo)
```

Implementation considerations:
- Parse OpenAPI spec
- Generate function wrappers with correct signatures
- Map HTTP responses back to Python types
- Handle errors as exceptions
- Support async variants

### 3.3 JavaScript Client Generation (http2js compatibility)

```python
from qh import export_js_client

js_code = export_js_client(
    app,
    module_name='myApi',
    include_types=True,  # TypeScript definitions
)
```

---

## Part 4: Developer Experience

### 4.1 Testing Support

Built-in test client with enhanced capabilities:

```python
from qh import mk_app
from qh.testing import TestClient

app = mk_app([foo, bar])
client = TestClient(app)

# Call functions directly (not HTTP)
assert client.foo(x=3) == 5

# Or make actual HTTP requests
response = client.post('/foo', json={'x': 3})
assert response.json() == 5

# Test OpenAPI round-tripping
remote_client = client.as_remote_client()
assert remote_client.foo(x=3) == 5  # Uses HTTP internally
```

### 4.2 Debugging & Introspection

```python
from qh import mk_app, inspect_app

app = mk_app([foo, bar, baz])

# Get all routes
routes = inspect_app(app)
# [
#   {'path': '/foo', 'methods': ['POST'], 'function': foo, ...},
#   {'path': '/bar', 'methods': ['POST'], 'function': bar, ...},
# ]

# Visualize routing table
print_routes(app)
# POST   /foo              foo(x: int) -> int
# POST   /bar              bar(name: str = 'world') -> str
# POST   /baz              baz() -> str
```

### 4.3 Error Messages

Clear, actionable error messages:

```python
# Before (cryptic)
422 Unprocessable Entity

# After (helpful)
ValidationError: Missing required parameter 'x' for function foo(x: int) -> int
Expected: POST /foo with JSON body {"x": <int>}
Received: POST /foo with JSON body {}
```

---

## Part 5: Implementation Roadmap

### Phase 1: Foundation (Weeks 1-2)
1. **Clean up codebase**
   - Consolidate `base.py`, `core.py`, `main.py` → `qh/app.py`
   - Remove py2http dependency
   - Establish single `mk_app` entry point

2. **Core configuration system**
   - Implement configuration schema
   - Default resolution logic
   - Per-function overrides

3. **Basic type system**
   - Type registry
   - JSON serialization (dict, list, primitives)
   - NumPy arrays, Pandas DataFrames

### Phase 2: Conventions (Weeks 3-4)
4. **Smart path generation**
   - Function name parsing
   - RESTful conventions
   - Signature-based parameter binding

5. **Store/Object dispatch**
   - Refactor `stores_qh.py` to use new system
   - Generic object method exposure
   - Nested resource patterns

6. **Testing infrastructure**
   - Enhanced TestClient
   - Route introspection
   - Better error messages

### Phase 3: OpenAPI & Bidirectional (Weeks 5-6)
7. **Enhanced OpenAPI export**
   - Extended metadata
   - Python type preservation
   - Examples generation

8. **Client generation**
   - Python client from OpenAPI
   - Signature preservation
   - Error handling

9. **JavaScript/TypeScript support**
   - Client code generation
   - Type definitions

### Phase 4: Polish & Documentation (Weeks 7-8)
10. **Documentation**
    - Comprehensive examples
    - Migration guide from py2http
    - Best practices

11. **Performance optimization**
    - Benchmark vs raw FastAPI
    - Lazy initialization
    - Caching

12. **Production readiness**
    - Security best practices
    - Rate limiting support
    - Monitoring hooks

---

## Part 6: Key Design Principles

### 6.1 Zero Boilerplate for Common Cases

```python
# This should be all you need for simple cases
from qh import mk_app

def add(x: int, y: int) -> int:
    return x + y

app = mk_app([add])
# ✓ POST /add endpoint
# ✓ JSON request/response
# ✓ Type validation
# ✓ OpenAPI docs
# ✓ Error handling
```

### 6.2 Escape Hatches for Complex Cases

```python
# But you can customize everything when needed
app = mk_app({
    add: {
        'path': '/calculator/add',
        'methods': ['POST', 'GET'],
        'input_trans': custom_transformer,
        'rate_limit': '100/hour',
        'auth': require_api_key,
    }
})
```

### 6.3 Stay Close to FastAPI

```python
# Users should still have access to FastAPI primitives
from fastapi import Depends, Header
from qh import mk_app

def get_user(
    user_id: str,
    token: str = Header(...),
    db: Database = Depends(get_db)
) -> User:
    ...

app = mk_app([get_user])  # FastAPI's Depends/Header just work
```

### 6.4 Fail Fast with Clear Errors

- Type mismatches detected at app creation, not runtime
- Configuration errors show exactly what's wrong and how to fix
- Runtime errors include context (function, parameters, request)

---

## Part 7: Migration from py2http

### 7.1 Compatibility Layer (Optional)

For gradual migration:

```python
from qh.compat import mk_app_legacy

# Old py2http code still works
app = mk_app_legacy(
    funcs,
    input_trans=...,
    output_trans=...,
)
```

### 7.2 Migration Guide

Provide clear examples:

```python
# py2http (old)
from py2http import mk_app
from py2http.decorators import mk_flat, handle_json_req

@mk_flat
class Service:
    def method(self, x: int): ...

app = mk_app([Service.method])

# qh (new)
from qh import mk_app, mk_object_app

service = Service()
app = mk_object_app(
    obj=service,
    methods=['method']
)
# Or even simpler:
app = mk_app([service.method])
```

---

## Part 8: Success Metrics

1. **Boilerplate Reduction**: 80% less code for common patterns vs raw FastAPI
2. **Type Safety**: 100% of type hints enforced automatically
3. **OpenAPI Completeness**: Round-trip fidelity (function → service → function)
4. **Performance**: <5% overhead vs hand-written FastAPI
5. **Developer Satisfaction**: Clear errors, good docs, easy debugging

---

## Part 9: Example Gallery

### Example 1: Simple Functions
```python
from qh import mk_app

def greet(name: str = "World") -> str:
    return f"Hello, {name}!"

def add(x: int, y: int) -> int:
    return x + y

app = mk_app([greet, add])
```

### Example 2: With Type Transformations
```python
import numpy as np
from qh import mk_app, register_type

@register_type(np.ndarray)
class NumpyArrayType:
    @staticmethod
    def serialize(arr: np.ndarray) -> list:
        return arr.tolist()

    @staticmethod
    def deserialize(data: list) -> np.ndarray:
        return np.array(data)

def process(data: np.ndarray) -> np.ndarray:
    return data * 2

app = mk_app([process])
```

### Example 3: Store Dispatch
```python
from qh import mk_store_app
from dol import LocalStore

app = mk_store_app(
    store_factory=lambda uri: LocalStore(uri),
    auth=validate_token,
    base_path='/stores/{uri}',
)

# Automatically creates:
# GET    /stores/{uri}           → list keys
# GET    /stores/{uri}/{key}     → get value
# PUT    /stores/{uri}/{key}     → set value
# DELETE /stores/{uri}/{key}     → delete key
```

### Example 4: Bidirectional Transformation
```python
# Server side
from qh import mk_app, export_openapi

def process_data(data: dict, threshold: float = 0.5) -> dict:
    """Process data with threshold."""
    return {'result': data, 'threshold': threshold}

app = mk_app([process_data])
export_openapi(app, 'openapi.json')

# Client side (different machine/process)
from qh.client import mk_client_from_openapi

client = mk_client_from_openapi('http://api.example.com/openapi.json')

# Use exactly like the original function!
result = client.process_data({'x': 1}, threshold=0.7)
```

---

## Conclusion

This plan transforms qh into a convention-over-configuration powerhouse that:
- **Eliminates boilerplate** through smart defaults
- **Preserves flexibility** with configuration overrides
- **Enables bidirectional transformation** for true function-as-a-service
- **Stays FastAPI-native** for ecosystem compatibility
- **Provides excellent DX** with clear errors and great docs

The result will be a tool that makes "from functions to HTTP services and back" feel like magic, while remaining transparent, debuggable, and production-ready.
