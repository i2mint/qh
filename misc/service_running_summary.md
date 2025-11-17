"""
Summary of service_running implementation for qh
"""

# service_running: Context Manager for HTTP Service Testing

## Overview

`service_running` is a flexible context manager in `qh.testing` that ensures an HTTP service is running for testing purposes. It intelligently checks if a service is already running and only launches/tears down services it started itself.

## Key Features

1. **Smart lifecycle management**: Only tears down services it launched
2. **Multiple launch modes**: Works with FastAPI apps, custom launchers, or existing services
3. **Readiness checks**: Polls service until ready with configurable timeout
4. **ServiceInfo return**: Provides comprehensive information about the running service
5. **Thread-based**: Uses threading (not multiprocessing) to avoid serialization issues on macOS

## Design Decisions

### 1. Name: `service_running`
- **Chosen**: `service_running` - reads naturally: `with service_running(...) as info:`
- Rejected: `ensure_service_is_running` (too verbose), `serve` (too generic)

### 2. Return Value: `ServiceInfo` dataclass
```python
@dataclass
class ServiceInfo:
    url: str  # Base URL of the service
    was_already_running: bool  # True if service was pre-existing
    thread: Optional[threading.Thread]  # Thread if launched, None otherwise
    app: Optional[FastAPI]  # The app if provided, None otherwise
```

### 3. Arguments: Explicit keyword-only parameters
```python
def service_running(
    *,
    url: Optional[str] = None,  # Check existing service
    app: Optional[FastAPI] = None,  # Launch FastAPI app
    launcher: Optional[Callable] = None,  # Custom launcher function
    port: int = 8000,
    host: str = '127.0.0.1',
    # ... readiness and timeout params
)
```

**Why explicit parameters?** 
- Clear intent and better type hints
- Good IDE autocomplete
- No ambiguity about which mode to use
- Exactly one of url/app/launcher must be provided

### 4. Threading vs Multiprocessing
**Chose threading** because:
- FastAPI apps can't be pickled for multiprocessing on macOS (spawn context)
- Threading is sufficient for test scenarios
- Daemon threads automatically clean up
- Simpler implementation

### 5. Legacy `serve_app` kept as facade
```python
def serve_app(app, port=8000, host="127.0.0.1"):
    """Simple facade over service_running for common case."""
    with service_running(app=app, port=port, host=host) as info:
        yield info.url
```

**Why keep it?**
- Simple API for the common case
- Already exported in `qh.__init__`
- Backward compatibility (though recently added)
- Just yields URL string (simpler than ServiceInfo)

## Related Tools in Other Packages

Mentioned in docstring for reference:
- **`meshed.tools.launch_webservice`**: Context manager for launching function-based web services
- **`strand.taskrunning.utils.run_process`**: Generic process runner with health checks  
- **`py2http`**: Various service management utilities

## Usage Examples

### Basic: Test a qh app
```python
from qh import mk_app, service_running

app = mk_app([add, multiply])
with service_running(app=app, port=8001) as info:
    response = requests.post(f'{info.url}/add', json={'x': 3, 'y': 5})
    assert response.json() == 8
```

### Check existing service (won't tear down)
```python
with service_running(url='https://api.github.com') as info:
    assert info.was_already_running
    response = requests.get(f'{info.url}/users/octocat')
```

### Custom launcher
```python
def my_launcher():
    # Custom service startup
    ...

with service_running(launcher=my_launcher, port=8002) as info:
    # Test your service
    ...
```

### Use ServiceInfo attributes
```python
with service_running(app=app) as info:
    print(f"URL: {info.url}")
    print(f"Was running: {info.was_already_running}")
    if info.thread:
        print(f"Thread alive: {info.thread.is_alive()}")
```

## Files Modified/Created

1. **`qh/testing.py`**: Main implementation
   - Added `ServiceInfo` dataclass
   - Added `service_running()` context manager
   - Added `_is_service_running()` helper
   - Refactored `serve_app()` to use `service_running()`

2. **`qh/__init__.py`**: Updated exports
   - Added `service_running` to imports and `__all__`
   - Added `ServiceInfo` to imports and `__all__`

3. **`examples/service_running_demo.py`**: Demonstration script
   - Shows all usage patterns
   - Demonstrates ServiceInfo attributes

4. **`qh/tests/test_service_running.py`**: Comprehensive tests
   - Tests all modes (app, url, launcher)
   - Tests validation
   - Tests ServiceInfo return value
   - All tests passing ✅

## Testing

```bash
# Run tests
pytest qh/tests/test_service_running.py -v

# Run demo
python examples/service_running_demo.py
```

All tests passing with no failures.
