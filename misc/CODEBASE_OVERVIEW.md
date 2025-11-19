# QH Codebase Architecture Overview

## 1. Project Purpose and Current State

**qh** ("Quick HTTP") is a convention-over-configuration tool for rapidly creating HTTP services from Python functions using FastAPI as the underlying framework. It transforms Python functions into REST API endpoints with minimal boilerplate.

**Current Phase**: Phase 3 (OpenAPI Export & Client Generation) recently completed
**Version**: 0.4.0
**Status**: All 3 phases complete and tested

## 2. Core Architecture

### 2.1 Main Module Organization

```
qh/
├── __init__.py          # Main API exports
├── app.py              # Primary API: mk_app() - creates FastAPI apps from functions
├── config.py           # Configuration system: AppConfig, RouteConfig, ConfigBuilder
├── endpoint.py         # Endpoint creation: make_endpoint(), extract_http_params()
├── rules.py            # Rule-based transformation system for parameter handling
├── conventions.py      # Convention-based routing (REST patterns)
├── types.py            # Type registry for automatic serialization/deserialization
├── base.py             # Lower-level mk_fastapi_app() and utilities
├── core.py             # Core FastAPI app creation with Wrap-based composition
├── openapi.py          # OpenAPI spec generation and enhancement
├── client.py           # Python client generation from OpenAPI specs
├── jsclient.py         # JavaScript/TypeScript client generation
├── stores_qh.py        # Store/object dispatch for dict-like objects
├── testing.py          # Testing utilities: AppRunner, serve_app, etc.
└── tests/              # Comprehensive test suite
```

## 3. Main Entry Point: mk_app()

**Location**: `qh/app.py`

**Purpose**: Single unified API to create FastAPI applications from Python functions

**Key Features**:
- **Multiple input formats**:
  - Single callable: `mk_app(func)`
  - List of callables: `mk_app([func1, func2, func3])`
  - Dict with per-function config: `mk_app({func1: config1, func2: config2})`

- **Configuration levels** (hierarchy: function → app → global):
  1. Function-level: `RouteConfig` per function
  2. App-level: `AppConfig` for global defaults
  3. Parameter-level: `TransformSpec` for specific parameters

```python
# Example usage
def add(x: int, y: int) -> int:
    return x + y

def list_users(limit: int = 10) -> list:
    return [...]

# Simple case - uses defaults
app = mk_app([add, list_users])

# With conventions (REST patterns)
app = mk_app([add, list_users], use_conventions=True)

# With custom config
app = mk_app(
    {add: {'path': '/math/add', 'methods': ['POST']}},
    config={'path_prefix': '/api/v1'}
)
```

## 4. Configuration System

**Location**: `qh/config.py`

### Four-Tier Hierarchy

1. **Global Defaults** (`DEFAULT_ROUTE_CONFIG`, `DEFAULT_APP_CONFIG`)
2. **App-Level Config** (`AppConfig`)
3. **Function-Level Config** (`RouteConfig`)
4. **Parameter-Level Config** (`param_overrides` in RouteConfig)

### Key Classes

**AppConfig**:
- `default_methods`: HTTP methods for all routes (default: ['POST'])
- `path_template`: Auto-generate paths (default: '/{func_name}')
- `path_prefix`: Prefix all routes (e.g., '/api/v1')
- `rule_chain`: Global transformation rules
- FastAPI kwargs (title, version, docs_url, etc.)

**RouteConfig**:
- `path`: Custom endpoint path
- `methods`: HTTP methods ('GET', 'POST', 'PUT', 'DELETE', 'PATCH')
- `rule_chain`: Custom parameter transformation rules
- `param_overrides`: Per-parameter HTTP location and transformation
- Metadata: `summary`, `description`, `tags`, `response_model`
- Schema options: `include_in_schema`, `deprecated`

## 5. Endpoint Creation Pipeline

**Location**: `qh/endpoint.py`

### make_endpoint() Function

Creates FastAPI-compatible async endpoint functions that:

1. **Extract HTTP Parameters**
   - Path parameters: `{param}` from URL
   - Query parameters: `?key=value` from query string
   - JSON body: Parameters from POST/PUT/PATCH body
   - Headers, cookies, form data

2. **Apply Ingress Transformations**
   - Convert HTTP representation to Python types
   - Type hints used for automatic conversion
   - Custom rules applied via `TransformSpec`

3. **Call Original Function**
   - Validates required parameters
   - Provides defaults for optional parameters
   - Supports both sync and async functions

4. **Apply Egress Transformations**
   - Convert return value to JSON-serializable format
   - Default handler for common types (dict, list, str, int, etc.)

**Key Feature: Async Support**
- `inspect.iscoroutinefunction()` used to detect async functions
- Async functions are awaited naturally
- Sync functions work the same way

## 6. Transformation Rules System

**Location**: `qh/rules.py`

### Rule-Based Parameter Matching

**HttpLocation Enum**:
```python
- JSON_BODY       # Default for POST/PUT/PATCH
- PATH            # URL path parameter
- QUERY           # Query string parameter
- HEADER          # HTTP header
- COOKIE          # HTTP cookie
- BINARY_BODY     # Raw binary payload
- FORM_DATA       # Multipart form data
```

**TransformSpec Dataclass**:
- `http_location`: Where to find/put the parameter
- `ingress`: Transform function (HTTP → Python)
- `egress`: Transform function (Python → HTTP)
- `http_name`: HTTP name (may differ from Python param name)

**Rule Types**:
- `TypeRule`: Match by parameter type
- `NameRule`: Match by parameter name
- `FuncRule`: Match by function object
- `FuncNameRule`: Match by function name pattern
- `DefaultValueRule`: Match by default value
- `CompositeRule`: Combine multiple rules (AND/OR)

**RuleChain**:
- Stores rules with priorities (higher priority evaluated first)
- First-match semantics: returns first matching rule
- `resolve_transform()` function resolves final spec

## 7. Convention-Based Routing

**Location**: `qh/conventions.py`

### Automatic REST Path Generation

**Function Name Parsing**:
```
Verb patterns:
- get, fetch, retrieve, read → GET
- list, find, search, query → GET
- create, add, insert, new → POST
- update, modify, edit, change, set → PUT
- patch → PATCH
- delete, remove, destroy → DELETE

Resource patterns:
- verb_resource: get_user, list_users, create_order_item
- Resource name auto-pluralized for collections
```

**Example Transformations**:
```python
def get_user(user_id: str) → GET /users/{user_id}
def list_users(limit: int = 100) → GET /users?limit=100
def create_user(name: str) → POST /users
def update_user(user_id: str, ...) → PUT /users/{user_id}
def delete_user(user_id: str) → DELETE /users/{user_id}
```

**Implementation Functions**:
- `parse_function_name()`: Extract verb and resource
- `infer_http_method()`: Get HTTP method from verb
- `infer_path_from_function()`: Generate RESTful path
- `apply_conventions_to_funcs()`: Apply to function list

## 8. Type Registry System

**Location**: `qh/types.py`

### Automatic Serialization/Deserialization

**TypeHandler**:
- Maps Python type → JSON representation
- `to_json()`: Python object → JSON
- `from_json()`: JSON → Python object

**TypeRegistry**:
- Global `_global_registry` manages all type handlers
- `register_type()`: Register custom type handler
- `get_transform_spec_for_type()`: Get ingress/egress for type

**Built-in Support**:
- Python builtins: str, int, float, bool, list, dict, None
- NumPy arrays: `.tolist()` / `np.array()`
- Pandas DataFrames: `.to_dict(orient='records')`
- Pandas Series: `.tolist()`

**Custom Type Registration**:
```python
# Method 1: Explicit
register_type(
    MyClass,
    to_json=lambda obj: obj.to_dict(),
    from_json=lambda data: MyClass.from_dict(data)
)

# Method 2: Decorator (auto-detects to_dict/from_dict)
@register_json_type
class Point:
    def to_dict(self): ...
    @classmethod
    def from_dict(cls, data): ...
```

## 9. Async Support in Current Codebase

### Existing Async Capabilities

**Async Functions are Supported**:
- `endpoint.py`: `make_endpoint()` creates async wrapper
- Detects async functions with `inspect.iscoroutinefunction()`
- Awaits async function results: `await func(**params)`
- Async helper functions: `extract_http_params()` is async

**Request Processing is Async**:
- Parameter extraction awaits: `await request.json()`
- Form parsing: `await request.form()`
- Body reading: `await request.body()`

**FastAPI Integration**:
- All endpoints are async handlers
- Compatible with FastAPI's async model
- Can use async dependencies (Depends)

### Async Test Support
```python
# From test_core.py
async def async_greeter(greeting: str, name: str = 'world') -> str:
    await asyncio.sleep(0.1)  # Simulate async operation
    return f"{greeting}, {name}!"

# Works naturally with TestClient
app = mk_fastapi_app([async_greeter])
response = TestClient(app).post("/async_greeter", ...)
```

## 10. Function Registration & Configuration Patterns

### How Functions are Registered

1. **Normalization** (`normalize_funcs_input()`):
   - Converts various input formats to `Dict[Callable, RouteConfig]`
   - Single function → wrapped in dict
   - List → dict with empty configs
   - Dict → preserved, dict configs converted to RouteConfig

2. **Convention Application** (optional):
   - `apply_conventions_to_funcs()` adds path/method inference
   - Explicit config takes precedence over conventions

3. **Configuration Resolution**:
   - `resolve_route_config()` merges defaults with explicit config
   - Fills in missing values from app-level defaults
   - Auto-generates paths/descriptions from function metadata

4. **Endpoint Creation**:
   - `make_endpoint()` wraps function with HTTP handling
   - Stores original function as `_qh_original_func`
   - Sets metadata (`__name__`, `__doc__`)

5. **Route Registration**:
   - `app.add_api_route()` registers with FastAPI
   - Full path = `app_config.path_prefix + resolved_config.path`
   - Methods, summary, description, tags all configured

## 11. Optional Features & Middleware Patterns

### Configuration-Based Optional Features

1. **Custom Transformations** (per-function):
   ```python
   RouteConfig(
       param_overrides={
           'param_name': TransformSpec(
               http_location=HttpLocation.HEADER,
               ingress=custom_decoder,
               egress=custom_encoder
           )
       }
   )
   ```

2. **HTTP Location Overrides**:
   - Path parameters: `HttpLocation.PATH`
   - Query parameters: `HttpLocation.QUERY`
   - Headers: `HttpLocation.HEADER`
   - Cookies: `HttpLocation.COOKIE`
   - Form data: `HttpLocation.FORM_DATA`

3. **Response Customization**:
   - `response_model`: Pydantic model for OpenAPI
   - `include_in_schema`: Toggle OpenAPI documentation
   - `deprecated`: Mark routes as deprecated

4. **Metadata**:
   - `summary`, `description`: OpenAPI docs
   - `tags`: Grouping in OpenAPI UI

### Middleware-Like Patterns

**Rules System as Configuration**:
- Custom `RuleChain` applied globally or per-function
- Rules can modify parameter handling without code changes
- Type registry acts as a global configuration

**Layered Configuration**:
- Global defaults can be set in `AppConfig`
- Per-function overrides in `RouteConfig`
- Per-parameter control via `TransformSpec`

## 12. Store/Object Dispatch

**Location**: `qh/stores_qh.py`

### Specialized Pattern for Objects

Exposes store-like (dict) objects or arbitrary objects as REST APIs:

```python
# Store methods exposed as HTTP endpoints
__iter__ → GET /         (list keys)
__getitem__ → GET /{key}  (get value)
__setitem__ → PUT /{key}  (set value)
__delitem__ → DELETE /{key}
__contains__ → GET /{key}/exists
__len__ → GET /$count
```

### User-Provided Patterns

```python
# Object method dispatch
class DataService:
    def get_data(self, key: str) → GET /data/{key}
    def put_data(self, key: str, data: bytes) → PUT /data/{key}

# Generic method exposure with custom configs
mk_store_dispatcher(
    store_getter=lambda store_id: stores[store_id],
    path_prefix='/stores'
)
```

## 13. Testing Infrastructure

**Location**: `qh/testing.py`

### Testing Utilities

1. **AppRunner**: Context manager for running apps
   - `use_server=False`: FastAPI TestClient (fast, no network)
   - `use_server=True`: Real uvicorn server (integration testing)

2. **Convenience Functions**:
   - `run_app()`: Generic context manager
   - `test_app()`: Simplified for TestClient
   - `serve_app()`: Simplified for real server
   - `quick_test()`: Single-function testing

### Example Usage
```python
from qh import mk_app
from qh.testing import test_app

def add(x: int, y: int) -> int:
    return x + y

app = mk_app([add])

with test_app(app) as client:
    response = client.post('/add', json={'x': 3, 'y': 5})
    assert response.json() == 8
```

## 14. OpenAPI & Client Generation (Phase 3)

**Locations**: `qh/openapi.py`, `qh/client.py`, `qh/jsclient.py`

### OpenAPI Spec Export
- `export_openapi()`: Generate OpenAPI spec from app
- `enhance_openapi_schema()`: Add custom metadata
- Extended with `x-python-*` fields for round-tripping

### Python Client Generation
- `mk_client_from_openapi()`: Generate Python client from spec
- `mk_client_from_url()`: Generate from remote API
- `mk_client_from_app()`: Generate from FastAPI app
- `HttpClient`: Base client class with request methods

### JavaScript/TypeScript Generation
- `export_js_client()`: Generate JavaScript client code
- `export_ts_client()`: Generate TypeScript client code

## 15. Current Async Limitations and Opportunities

### Current State
✅ Async functions work
✅ Async parameter extraction works
✅ Async endpoint handlers work
✅ TestClient supports async functions

### Limitations/Gaps for Tracking IDs
❌ No automatic request tracking/correlation
❌ No built-in request context management
❌ No background task integration
❌ No async context variables used
❌ No request ID propagation across async boundaries
❌ No tracking ID middleware

## 16. Key Design Patterns & Principles

### Convention Over Configuration
- Smart defaults: most functions work with no config
- Escape hatches: override any behavior when needed
- REST conventions inferred from function names

### Layered Configuration
- Global defaults apply to all routes
- App-level config overrides global
- Function-level config overrides app
- Parameter-level control via rules/overrides

### Type-Driven
- Type hints used for validation and conversion
- Custom types registered via registry
- Ingress/egress transformations based on types

### Rule-Based Parameter Handling
- Flexible matching (type, name, function, patterns)
- First-match semantics with priority
- Composable rules for complex scenarios

### FastAPI-Native
- No abstraction layer over FastAPI
- Users get full FastAPI capabilities
- Direct access to Request, Depends, etc.

### Open for Extension
- Custom rules can be added
- Types can be registered
- Stores/objects can be dispatched
- OpenAPI can be enhanced

## Summary

The qh codebase is a well-architected, convention-over-configuration framework for exposing Python functions as HTTP services. It builds directly on FastAPI with:

1. **Clean API**: Single `mk_app()` entry point with multiple input formats
2. **Flexible Configuration**: Four-tier hierarchy (global → app → function → parameter)
3. **Smart Defaults**: REST conventions inferred from function names
4. **Type Safety**: Type hints drive validation and transformation
5. **Async Ready**: Full support for async functions and FastAPI patterns
6. **Extensible**: Type registry, rule system, and custom configurations
7. **Testing Friendly**: Built-in test utilities and app inspection
8. **Production Ready**: OpenAPI generation, client code generation, error handling

The codebase is mature (Phase 3 complete) with comprehensive test coverage and good documentation. The architecture supports adding async tracking ID capabilities through the configuration and rule systems without major refactoring.
