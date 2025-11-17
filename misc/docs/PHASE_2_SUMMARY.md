# Phase 2 Implementation Summary: Conventions & Type Registry

## Overview

Phase 2 adds powerful convention-over-configuration features and a flexible type registry to qh, making it even easier to create HTTP services from Python functions.

## What's New in v0.3.0

### 1. Convention-Based Routing (`qh/conventions.py`)

Automatically infer HTTP paths and methods from function names following RESTful conventions:

```python
from qh import mk_app

def get_user(user_id: str) -> dict:
    return {'user_id': user_id, 'name': 'John'}

def list_users(limit: int = 10) -> list:
    return [...]

def create_user(name: str) -> dict:
    return {'user_id': '123', 'name': name}

# Enable conventions with one parameter
app = mk_app([get_user, list_users, create_user], use_conventions=True)

# Automatically creates:
# GET    /users/{user_id}  (get_user)
# GET    /users            (list_users)
# POST   /users            (create_user)
```

**Features:**
- ✅ Verb recognition: get, list, create, update, delete, etc.
- ✅ Resource pluralization: user → users
- ✅ Path parameter inference: `user_id` → `{user_id}` in path
- ✅ Query parameter support: GET request params come from query string
- ✅ Automatic type conversion: query params converted from strings
- ✅ HTTP method inference: get→GET, create→POST, update→PUT, delete→DELETE

### 2. Type Registry (`qh/types.py`)

Register custom types for automatic serialization/deserialization:

```python
from qh import mk_app, register_type
import numpy as np

# Register a custom type
register_type(
    np.ndarray,
    to_json=lambda arr: arr.tolist(),
    from_json=lambda data: np.array(data)
)

def process_array(data: np.ndarray) -> np.ndarray:
    return data * 2

app = mk_app([process_array])
# NumPy arrays automatically converted to/from JSON!
```

**Built-in Support:**
- ✅ Python builtins (str, int, float, bool, list, dict)
- ✅ NumPy arrays (if NumPy installed)
- ✅ Pandas DataFrames and Series (if Pandas installed)

**Custom Type Registration:**

```python
# Method 1: Explicit registration
from qh.types import register_type

register_type(
    MyClass,
    to_json=lambda obj: obj.to_dict(),
    from_json=lambda data: MyClass.from_dict(data)
)

# Method 2: Decorator (auto-detects to_dict/from_dict methods)
from qh.types import register_json_type

@register_json_type
class Point:
    def __init__(self, x, y):
        self.x = x
        self.y = y

    def to_dict(self):
        return {'x': self.x, 'y': self.y}

    @classmethod
    def from_dict(cls, data):
        return cls(data['x'], data['y'])
```

### 3. Enhanced Path Parameter Handling

Automatic detection and extraction of path parameters:

```python
def get_order(user_id: str, order_id: str) -> dict:
    # ...

app = mk_app(
    {get_order: {'path': '/users/{user_id}/orders/{order_id}'}},
)

# Path parameters automatically extracted from URL
# No manual configuration needed!
```

### 4. Query Parameter Support for GET

GET request parameters automatically come from query strings:

```python
def search_products(query: str, category: str = None, limit: int = 10) -> list:
    # ...

app = mk_app([search_products], use_conventions=True)

# GET /products?query=laptop&category=electronics&limit=20
# Parameters automatically extracted and type-converted!
```

## New Files

- **qh/conventions.py** (356 lines) - Convention-based routing system
- **qh/types.py** (333 lines) - Type registry with NumPy/Pandas support
- **qh/tests/test_conventions.py** (298 lines) - Comprehensive convention tests
- **examples/conventions_demo.py** - Full CRUD example with conventions
- **examples/custom_types_demo.py** - Custom type registration examples

## Modified Files

- **qh/app.py** - Added `use_conventions` parameter to `mk_app()`
- **qh/config.py** - Support dict-to-RouteConfig conversion
- **qh/endpoint.py** - Automatic path parameter detection
- **qh/rules.py** - Integrated type registry into resolution chain
- **qh/__init__.py** - Export new features, bump version to 0.3.0

## Test Results

```
20 tests passing:
- 12 core mk_app tests (from Phase 1)
- 8 new convention tests

✅ test_parse_function_name
✅ test_infer_http_method
✅ test_singularize_pluralize
✅ test_infer_path
✅ test_conventions_in_mk_app
✅ test_conventions_with_client
✅ test_conventions_override
✅ test_crud_operations
```

## Usage Examples

### Example 1: Simple Convention-Based API

```python
from qh import mk_app

def get_product(product_id: str) -> dict:
    return {'product_id': product_id, 'name': 'Widget'}

def list_products(category: str = None) -> list:
    return [{'product_id': '1', 'name': 'Widget'}]

app = mk_app([get_product, list_products], use_conventions=True)

# Creates:
# GET /products/{product_id}
# GET /products?category=...
```

### Example 2: Custom Types with NumPy

```python
from qh import mk_app, register_type
import numpy as np

register_type(
    np.ndarray,
    to_json=lambda arr: arr.tolist(),
    from_json=lambda lst: np.array(lst)
)

def add_arrays(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    return a + b

app = mk_app([add_arrays])

# POST /add_arrays
# Request: {"a": [1,2,3], "b": [4,5,6]}
# Response: [5,7,9]
```

### Example 3: Mix Conventions with Custom Config

```python
from qh import mk_app

def get_user(user_id: str) -> dict:
    return {'user_id': user_id}

def special_endpoint(data: dict) -> dict:
    return {'processed': True}

app = mk_app(
    {
        get_user: {},  # Use conventions
        special_endpoint: {'path': '/custom', 'methods': ['POST']},  # Override
    },
    use_conventions=True
)

# GET /users/{user_id}  (from conventions)
# POST /custom           (explicit config)
```

## Key Benefits

1. **Less Boilerplate**: Convention-based routing eliminates repetitive path/method configuration
2. **Type Safety**: Automatic type conversion for query params and custom types
3. **RESTful by Default**: Follows REST conventions automatically
4. **Flexible**: Easy to override conventions when needed
5. **Extensible**: Register any custom type for automatic handling

## What's Next (Phase 3 - Pending)

- Enhanced OpenAPI generation with round-trip metadata
- Python client generation from OpenAPI specs
- JavaScript/TypeScript client support
- Refactored store/object dispatch using new system

## Migration from v0.2.0 (Phase 1)

No breaking changes! All Phase 1 code continues to work.

New features are opt-in:
- Add `use_conventions=True` to enable convention-based routing
- Use `register_type()` to add custom type support
- Everything else works exactly as before

## Performance

- Negligible overhead for convention inference (done once at app creation)
- Type conversions only applied when needed
- All transformations cached and reused

---

**Phase 2 Complete** ✅
All core convention and type registry features implemented and tested.
