# qh

**Quick HTTP web-service construction** - From Python functions to production-ready HTTP services, with minimal boilerplate.

`qh` (pronounced "quick") is a convention-over-configuration framework for exposing Python functions as HTTP services. Built on FastAPI, it provides a delightfully simple API while giving you escape hatches for advanced use cases.

```bash
pip install qh
```

## Quickstart: From Function to API in 3 Lines

```python
from qh import mk_app

def add(x: int, y: int) -> int:
    return x + y

app = mk_app([add])
```

That's it! You now have a FastAPI app with:
- ✅ Automatic request/response handling
- ✅ Type validation from your annotations
- ✅ OpenAPI documentation at `/docs`
- ✅ Multiple input formats (JSON body, query params, etc.)

Run it:
```bash
uvicorn your_module:app
```

Or test it:
```python
from qh.testing import test_app

with test_app(app) as client:
    response = client.post("/add", json={"x": 3, "y": 5})
    print(response.json())  # 8
```

## What You Can Do From Here

### 🚀 Async Task Processing (NEW in v0.5.0)

Handle long-running operations without blocking:

```python
import time

def expensive_computation(n: int) -> int:
    time.sleep(5)  # Simulate heavy processing
    return n * 2

# Enable async support
app = mk_app(
    [expensive_computation],
    async_funcs=['expensive_computation']
)
```

Now clients can choose sync or async execution:

```python
# Synchronous (blocks for 5 seconds)
POST /expensive_computation?n=10
→ 20

# Asynchronous (returns immediately)
POST /expensive_computation?n=10&async=true
→ {"task_id": "abc-123", "status": "submitted"}

# Check status
GET /tasks/abc-123/status
→ {"status": "running", "started_at": 1234567890}

# Get result (blocks until ready, or returns immediately if done)
GET /tasks/abc-123/result?wait=true&timeout=10
→ {"status": "completed", "result": 20}
```

**Advanced async configuration:**

```python
from qh import mk_app, TaskConfig, ProcessPoolTaskExecutor

app = mk_app(
    [cpu_bound_func, io_bound_func],
    async_funcs=['cpu_bound_func', 'io_bound_func'],
    async_config={
        'cpu_bound_func': TaskConfig(
            executor=ProcessPoolTaskExecutor(max_workers=4),  # Use processes for CPU-bound
            ttl=3600,  # Keep results for 1 hour
        ),
        'io_bound_func': TaskConfig(
            async_mode='always',  # Always async, no query param needed
        ),
    }
)
```

Task management endpoints are automatically created:
- `GET /tasks/` - List all tasks
- `GET /tasks/{id}` - Get complete task info
- `GET /tasks/{id}/status` - Get task status
- `GET /tasks/{id}/result` - Get result (with optional wait)
- `DELETE /tasks/{id}` - Cancel/delete task

### 📝 Convention-Based Routing

```python
def get_user(user_id: str):
    return {"id": user_id, "name": "Alice"}

def list_users():
    return [{"id": "1", "name": "Alice"}]

def create_user(name: str, email: str):
    return {"id": "123", "name": name, "email": email}

app = mk_app(
    [get_user, list_users, create_user],
    use_conventions=True
)
```

This automatically creates RESTful routes:
- `GET /users/{user_id}` → `get_user(user_id)`
- `GET /users` → `list_users()`
- `POST /users` → `create_user(name, email)`

### 🎯 Explicit Configuration

```python
from qh import mk_app, RouteConfig

def add(x: int, y: int) -> int:
    return x + y

app = mk_app({
    add: RouteConfig(
        path="/calculate/sum",
        methods=["GET", "POST"],
        tags=["math"],
        summary="Add two numbers"
    )
})
```

Or use dictionaries:
```python
app = mk_app({
    add: {
        "path": "/calculate/sum",
        "methods": ["GET", "POST"],
    }
})
```

### 🔄 Parameter Transformation

```python
import numpy as np
from qh import mk_app, RouteConfig, TransformSpec, HttpLocation

def add_arrays(a, b):
    return (a + b).tolist()

app = mk_app({
    add_arrays: RouteConfig(
        param_overrides={
            "a": TransformSpec(
                http_location=HttpLocation.JSON_BODY,
                ingress=np.array  # Convert JSON array to numpy
            ),
            "b": TransformSpec(
                http_location=HttpLocation.JSON_BODY,
                ingress=np.array
            )
        }
    )
})
```

Now you can send:
```bash
POST /add_arrays
{"a": [1,2,3], "b": [4,5,6]}
→ [5, 7, 9]
```

### 🌐 OpenAPI & Client Generation

```python
from qh import mk_app, export_openapi, mk_client_from_app

def greet(name: str) -> str:
    return f"Hello, {name}!"

app = mk_app([greet])

# Export OpenAPI spec
export_openapi(app, "api.json")

# Generate Python client
client = mk_client_from_app(app)
result = client.greet(name="World")  # "Hello, World!"

# Generate TypeScript client
from qh import export_ts_client
export_ts_client(app, "client.ts")
```

### 🎨 Custom Types

```python
from qh import register_type
from datetime import datetime

def custom_serializer(dt: datetime) -> str:
    return dt.isoformat()

def custom_deserializer(s: str) -> datetime:
    return datetime.fromisoformat(s)

register_type(
    datetime,
    serialize=custom_serializer,
    deserialize=custom_deserializer
)

def get_event_time(event_id: str) -> datetime:
    return datetime.now()

app = mk_app([get_event_time])
```

### ⚙️ Global Configuration

```python
from qh import mk_app, AppConfig

app = mk_app(
    funcs=[add, multiply, divide],
    config=AppConfig(
        path_prefix="/api/v1",
        default_methods=["POST"],
        title="Math API",
        version="1.0.0",
    )
)
```

### 🧪 Testing Utilities

```python
from qh import test_app, serve_app, quick_test

# Quick inline testing
with test_app(app) as client:
    response = client.post("/add", json={"x": 3, "y": 5})
    assert response.json() == 8

# Serve for external testing
with serve_app(app, port=8001) as url:
    import requests
    response = requests.post(f"{url}/add", json={"x": 3, "y": 5})

# Quick smoke test
quick_test(app)  # Tests all endpoints with example data
```

## Features

### Built-in
- ✅ **Minimal boilerplate** - Define functions, get HTTP service
- ✅ **Type-driven** - Uses Python type hints for validation
- ✅ **FastAPI-powered** - Full async support, high performance
- ✅ **Automatic OpenAPI** - Interactive docs at `/docs`
- ✅ **Client generation** - Python, TypeScript, JavaScript clients
- ✅ **Convention over configuration** - RESTful routing from function names
- ✅ **Flexible parameter handling** - JSON, query, path, headers, forms
- ✅ **Custom transformations** - Transform inputs/outputs as needed
- ✅ **Testing utilities** - Built-in test client and helpers

### Phase 4 (NEW): Async Task Processing
- ✅ **Background tasks** - Long-running operations without blocking
- ✅ **Task tracking** - Status monitoring and result retrieval
- ✅ **Flexible execution** - Thread pools, process pools, or custom executors
- ✅ **Client-controlled** - Let users choose sync vs async
- ✅ **Standard HTTP patterns** - Poll for status, wait for results
- ✅ **Task management** - List, query, cancel tasks via HTTP

## Examples

### Simple CRUD API
```python
from qh import mk_app

# In-memory database
users = {}

def create_user(name: str, email: str) -> dict:
    user_id = str(len(users) + 1)
    users[user_id] = {"id": user_id, "name": name, "email": email}
    return users[user_id]

def get_user(user_id: str) -> dict:
    return users.get(user_id, {})

def list_users() -> list:
    return list(users.values())

app = mk_app(
    [create_user, get_user, list_users],
    use_conventions=True
)
```

### File Processing with Async
```python
from qh import mk_app, TaskConfig
import time

def process_large_file(file_path: str) -> dict:
    time.sleep(10)  # Simulate heavy processing
    return {"status": "processed", "path": file_path}

app = mk_app(
    [process_large_file],
    async_funcs=['process_large_file'],
    async_config=TaskConfig(
        async_mode='always',  # Always async
        ttl=3600,  # Keep results for 1 hour
    )
)

# Client usage:
# POST /process_large_file -> Returns task_id immediately
# GET /tasks/{task_id}/result?wait=true -> Blocks until done
```

### Mixed Sync/Async API
```python
def quick_lookup(key: str) -> str:
    """Fast operation - always synchronous"""
    return cache.get(key)

def expensive_aggregation(days: int) -> dict:
    """Slow operation - supports async"""
    time.sleep(days * 2)
    return {"result": "..."}

app = mk_app(
    [quick_lookup, expensive_aggregation],
    async_funcs=['expensive_aggregation']  # Only expensive_aggregation supports async
)

# quick_lookup is always synchronous
# expensive_aggregation can be called with ?async=true
```

### Data Science API
```python
import numpy as np
import pandas as pd
from qh import mk_app, RouteConfig, TransformSpec

def analyze_data(data: pd.DataFrame) -> dict:
    return {
        "mean": data.mean().to_dict(),
        "std": data.std().to_dict()
    }

app = mk_app({
    analyze_data: RouteConfig(
        param_overrides={
            "data": TransformSpec(ingress=pd.DataFrame)
        }
    )
})

# POST /analyze_data
# {"data": {"col1": [1,2,3], "col2": [4,5,6]}}
```

## Philosophy

**Convention over configuration, but configuration when you need it.**

`qh` follows a layered approach:
1. **Simple case** - Just pass functions, get working HTTP service
2. **Common cases** - Use conventions (RESTful routing, type-driven validation)
3. **Advanced cases** - Explicit configuration for full control

You write Python functions. `qh` handles the HTTP layer.

## Comparison

| Feature | qh | FastAPI | Flask |
|---------|----|---------| ------|
| From functions to HTTP | 1 line | ~10 lines | ~15 lines |
| Type validation | Automatic | Automatic | Manual |
| OpenAPI docs | Automatic | Automatic | Extensions |
| Client generation | ✅ Built-in | ❌ External tools | ❌ Manual |
| Convention routing | ✅ Yes | ❌ No | ❌ No |
| Async tasks | ✅ Built-in | ❌ Manual setup | ❌ Extensions |
| Task tracking | ✅ Automatic | ❌ Manual | ❌ Manual |
| Learning curve | Minutes | Hours | Hours |
| Suitable for production | Yes (it's FastAPI!) | Yes | Yes |

## Under the Hood

`qh` is built on:
- [FastAPI](https://fastapi.tiangolo.com/) - Modern, fast web framework
- [i2](https://github.com/i2mint/i2) - Function signature manipulation
- [Pydantic](https://pydantic-docs.helpmanual.io/) - Data validation

When you create an app with `qh`, you get a fully-featured FastAPI application. All FastAPI features are available.

## Advanced Topics

### Using au Package (External Async Backend)

The built-in async functionality is perfect for most use cases, but if you need distributed task processing, you can integrate with [au](https://github.com/i2mint/au):

```bash
pip install au
```

```python
from au import async_compute, RQBackend
from qh import mk_app, TaskConfig

# Configure au with Redis backend
@async_compute(backend=RQBackend('redis://localhost:6379'))
def heavy_computation(n: int) -> int:
    return n * 2

# Use with qh
app = mk_app([heavy_computation])
# Now heavy_computation can be distributed across multiple workers
```

### Custom Task Executors

```python
from qh import TaskExecutor, TaskConfig
from concurrent.futures import ThreadPoolExecutor

class MyCustomExecutor(TaskExecutor):
    def __init__(self):
        self.pool = ThreadPoolExecutor(max_workers=10)

    def submit_task(self, task_id, func, args, kwargs, callback):
        # Custom task submission logic
        def wrapper():
            try:
                result = func(*args, **kwargs)
                callback(task_id, result, None)
            except Exception as e:
                callback(task_id, None, e)
        self.pool.submit(wrapper)

    def shutdown(self, wait=True):
        self.pool.shutdown(wait=wait)

app = mk_app(
    [my_func],
    async_funcs=['my_func'],
    async_config=TaskConfig(executor=MyCustomExecutor())
)
```

### Middleware and Extensions

Since `qh` creates a FastAPI app, you can use all FastAPI features:

```python
from qh import mk_app
from fastapi.middleware.cors import CORSMiddleware

app = mk_app([my_func])

# Add CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add custom routes
@app.get("/health")
async def health():
    return {"status": "healthy"}
```

## Migration Guide

### From v0.4.0 to v0.5.0

The async task feature is fully backward compatible. Existing apps will work without changes.

To enable async:
```python
# Old (still works)
app = mk_app([my_func])

# New (with async support)
app = mk_app([my_func], async_funcs=['my_func'])
```

## Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

Apache 2.0

## Links

- **Documentation**: https://github.com/i2mint/qh
- **Source Code**: https://github.com/i2mint/qh
- **Issue Tracker**: https://github.com/i2mint/qh/issues
- **Related Projects**:
  - [i2](https://github.com/i2mint/i2) - Function signature manipulation
  - [au](https://github.com/i2mint/au) - Async utilities for distributed computing
  - [FastAPI](https://fastapi.tiangolo.com/) - The underlying web framework

---

Made with ❤️ by the i2mint team
