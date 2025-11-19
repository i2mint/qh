# QH Codebase Quick Reference

## Project at a Glance

**qh** = "Quick HTTP" = FastAPI-based function-to-REST-API tool

**Current Status**: Phase 3 complete (v0.4.0) - Full OpenAPI & client generation

## Entry Points (in priority order)

| File | Purpose | Key Classes/Functions |
|------|---------|----------------------|
| `qh/app.py` | **Primary API** | `mk_app()` - creates FastAPI app |
| `qh/config.py` | Configuration system | `AppConfig`, `RouteConfig` |
| `qh/endpoint.py` | Endpoint creation | `make_endpoint()`, async handlers |
| `qh/rules.py` | Parameter transformation | `TransformSpec`, `RuleChain`, `*Rule` |
| `qh/conventions.py` | REST auto-routing | `apply_conventions_to_funcs()` |
| `qh/types.py` | Type serialization | `register_type()`, `TypeRegistry` |

## Core Data Structures

### AppConfig (app-level)
```python
AppConfig(
    default_methods=['POST'],
    path_template='/{func_name}',
    path_prefix='/api',
    rule_chain=DEFAULT_RULE_CHAIN,
    title='My API',
    version='0.1.0'
)
```

### RouteConfig (function-level)
```python
RouteConfig(
    path='/custom/path',
    methods=['GET', 'POST'],
    rule_chain=custom_rules,
    param_overrides={'param': TransformSpec(...)},
    summary='Brief description',
    tags=['tag1', 'tag2']
)
```

### TransformSpec (parameter-level)
```python
TransformSpec(
    http_location=HttpLocation.QUERY,
    ingress=custom_converter,  # HTTP → Python
    egress=custom_serializer,  # Python → HTTP
    http_name='different_name'
)
```

## How mk_app() Works (Pipeline)

```
1. Input Normalization
   ├─ Single callable → Dict[Callable, RouteConfig]
   ├─ List → Dict[Callable, RouteConfig]
   └─ Dict → Keep as-is

2. Convention Application (if use_conventions=True)
   ├─ Parse function name (verb_resource)
   ├─ Infer HTTP method (get→GET, create→POST, etc.)
   └─ Generate RESTful path (/users/{user_id})

3. Configuration Resolution (per function)
   ├─ Start with DEFAULT_ROUTE_CONFIG
   ├─ Apply AppConfig defaults
   ├─ Apply function-specific RouteConfig
   └─ Auto-fill missing fields

4. Endpoint Creation
   ├─ make_endpoint() wraps function
   ├─ Creates async HTTP handler
   ├─ Parameter extraction & transformation
   └─ Stores original function reference

5. Route Registration
   └─ app.add_api_route() to FastAPI app
```

## Key Patterns

### Simple Function
```python
def add(x: int, y: int) -> int:
    return x + y

app = mk_app([add])
# → POST /add with JSON body
```

### With Conventions
```python
def get_user(user_id: str) -> dict:
    return {'user_id': user_id}

def list_users(limit: int = 10) -> list:
    return [...]

app = mk_app([get_user, list_users], use_conventions=True)
# → GET /users/{user_id}
# → GET /users?limit=10
```

### Custom Configuration
```python
app = mk_app(
    {
        func1: RouteConfig(path='/custom', methods=['GET']),
        func2: {'path': '/other', 'methods': ['POST', 'PUT']},
    },
    config=AppConfig(path_prefix='/api/v1')
)
```

### Parameter Transformation
```python
from qh.rules import NameRule, TransformSpec, HttpLocation

my_rule = NameRule({
    'api_key': TransformSpec(
        http_location=HttpLocation.HEADER,
        http_name='Authorization'
    )
})

app = mk_app(
    [func],
    config=AppConfig(rule_chain=RuleChain([my_rule]))
)
```

### Type Registration
```python
import numpy as np
from qh import register_type

register_type(
    np.ndarray,
    to_json=lambda arr: arr.tolist(),
    from_json=lambda lst: np.array(lst)
)

def process(data: np.ndarray) -> np.ndarray:
    return data * 2

app = mk_app([process])
# JSON arrays ↔ NumPy arrays automatically
```

## Async Support

### Current Capabilities
✅ Async functions work automatically
✅ Async parameter extraction
✅ Proper await handling
✅ TestClient compatible

### Example
```python
async def fetch_data(url: str) -> dict:
    # async function works naturally
    response = await some_http_client.get(url)
    return response.json()

app = mk_app([fetch_data])
# Works seamlessly, handler awaits automatically
```

## Testing

```python
from qh.testing import test_app

def add(x: int, y: int) -> int:
    return x + y

app = mk_app([add])

with test_app(app) as client:
    response = client.post('/add', json={'x': 3, 'y': 5})
    assert response.json() == 8
```

## Configuration Hierarchy (Precedence)

```
Parameter-level override (highest)
    ↓
Function-level config (RouteConfig)
    ↓
App-level config (AppConfig)
    ↓
Global defaults (lowest)
```

## Route Inspection

```python
from qh import inspect_routes, print_routes

routes = inspect_routes(app)
print_routes(app)

# Output:
# METHODS  PATH           ENDPOINT
# -------  ----           --------
# POST     /add           add
# GET      /users/{id}    get_user
```

## HTTP Locations (Where Parameters Come From)

| Location | Source | Example |
|----------|--------|---------|
| `PATH` | URL path | `/users/{user_id}` |
| `QUERY` | Query string | `?limit=10&offset=20` |
| `JSON_BODY` | POST/PUT body | `{"x": 3, "y": 5}` |
| `HEADER` | HTTP header | `X-API-Key: secret` |
| `COOKIE` | HTTP cookie | `session_id=abc123` |
| `FORM_DATA` | Multipart form | Uploaded files |
| `BINARY_BODY` | Raw body | Binary data |

## File Structure Reference

```
qh/
├── __init__.py              → Main exports
├── app.py                   → mk_app() and route inspection
├── config.py                → AppConfig, RouteConfig, ConfigBuilder
├── endpoint.py              → make_endpoint(), async handlers
├── rules.py                 → Rule system, TransformSpec
├── conventions.py           → REST conventions (get_user → GET /users/{id})
├── types.py                 → Type registry, custom serialization
├── base.py                  → Lower-level mk_fastapi_app()
├── core.py                  → Core with i2.Wrap composition
├── openapi.py               → OpenAPI spec generation
├── client.py                → Python client generation from specs
├── jsclient.py              → JavaScript/TypeScript code gen
├── stores_qh.py             → Store/object dispatch
├── testing.py               → AppRunner, test utilities
└── tests/                   → Comprehensive test suite
```

## Important Functions

| Function | Location | Purpose |
|----------|----------|---------|
| `mk_app()` | `app.py` | **Main entry point** |
| `make_endpoint()` | `endpoint.py` | Create async HTTP handler |
| `resolve_route_config()` | `config.py` | Merge configs hierarchically |
| `extract_http_params()` | `endpoint.py` | Extract params from request |
| `apply_conventions_to_funcs()` | `conventions.py` | Apply REST patterns |
| `register_type()` | `types.py` | Register custom type handler |
| `resolve_transform()` | `rules.py` | Resolve parameter transformation |
| `inspect_routes()` | `app.py` | Get list of routes |

## Common Issues & Solutions

| Issue | Solution |
|-------|----------|
| Function params not extracted | Check `TransformSpec.http_location` |
| Type conversion failing | Register type with `register_type()` |
| Path parameter not recognized | Use `{param_name}` in path config |
| GET request not working | Params must come from query string or path |
| Async function not awaited | Already handled automatically |
| Missing X-Request-ID header | Use `TransformSpec` with fallback |

## Design Principles

1. **Convention over Configuration** - Smart defaults, explicit overrides
2. **Layered Configuration** - Global → app → function → parameter
3. **Type-Driven** - Type hints drive behavior
4. **Rule-Based** - Flexible parameter matching and transformation
5. **FastAPI-Native** - Direct FastAPI integration, no abstraction
6. **Async-Ready** - Full async/await support
7. **Extensible** - Type registry, custom rules, middleware

## Version & Imports

```python
# Main API (recommended)
from qh import mk_app, AppConfig, RouteConfig

# Rules and configuration
from qh import RuleChain, TransformSpec, HttpLocation
from qh.rules import NameRule, TypeRule, FuncRule

# Type registry
from qh import register_type, register_json_type

# Testing
from qh.testing import test_app, serve_app, quick_test

# Conventions
from qh import mk_app  # use_conventions=True parameter

# Advanced
from qh.config import ConfigBuilder
from qh.endpoint import make_endpoint
from qh.conventions import apply_conventions_to_funcs
```

## Next Steps for Async Tracking IDs

See `async_tracking_analysis.md` for:
- Recommended patterns for request ID handling
- Contextvars-based context management
- Integration points with FastAPI
- Code examples for 5 different approaches

**Recommended approach**: Pattern 1 + 3 (TransformSpec + contextvars)
