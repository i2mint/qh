# Async Tracking ID Implementation Analysis

## Current State of Async Support

The qh codebase has **comprehensive async support** already in place:

### What's Already Implemented
1. **Async endpoint handlers** - All endpoints are async
2. **Async function detection** - `inspect.iscoroutinefunction()` used
3. **Async parameter extraction** - `extract_http_params()` is async
4. **Natural await handling** - Async functions work seamlessly
5. **TestClient compatibility** - Works with FastAPI's TestClient

### Code Examples Showing Current Async Support

**From endpoint.py**:
```python
async def endpoint(request: Request) -> Response:
    # Async parameter extraction
    http_params = await extract_http_params(request, param_specs)
    # ...
    # Natural async/sync function handling
    if is_async:
        result = await func(**transformed_params)
    else:
        result = func(**transformed_params)
```

**From base.py**:
```python
async def endpoint(request: Request):
    data = await request.json()
    # ...
    result = func(**data)
    if inspect.iscoroutine(result):
        result = await result
```

## What's Missing for Request Tracking IDs

### Identified Gaps

1. **No Request Context Management**
   - FastAPI Request object is not preserved across async boundaries
   - No async context variables (contextvars) used
   - No automatic tracking ID injection

2. **No Built-in Request ID Generation**
   - No UUID generation for requests
   - No header inspection for existing trace IDs
   - No ID propagation mechanism

3. **No Background Task Support**
   - Background tasks not integrated into framework
   - No async task queue or job management
   - No task-to-request correlation

4. **No Middleware for Request Correlation**
   - No automatic header injection
   - No request/response ID decoration
   - No logging integration points

## Recommended Patterns for Async Tracking IDs

### Pattern 1: Using TransformSpec for Request ID Parameter

**Approach**: Inject tracking ID as a special parameter via the rules system

```python
from qh.rules import TransformSpec, HttpLocation
from qh.config import AppConfig, RouteConfig
import uuid

# Create ingress function that extracts or generates tracking ID
def extract_tracking_id(request_value):
    # Value comes from X-Request-ID header
    return request_value or str(uuid.uuid4())

# Global rule that matches any 'request_id' parameter
tracking_id_rule = NameRule({
    'request_id': TransformSpec(
        http_location=HttpLocation.HEADER,
        http_name='X-Request-ID',
        ingress=extract_tracking_id
    )
})

# Apply globally
app_config = AppConfig(
    rule_chain=RuleChain([tracking_id_rule])
)

app = mk_app(funcs, config=app_config)

# Now any function with a 'request_id' parameter gets it automatically
def process_data(request_id: str, data: dict):
    print(f"Processing {request_id}: {data}")
```

### Pattern 2: Using FastAPI's BackgroundTasks

**Approach**: Leverage FastAPI's native background task support through Depends

```python
from fastapi import BackgroundTasks, Depends
from qh import mk_app
import asyncio

async def log_request(request_id: str, task_name: str):
    """Log task in background"""
    await asyncio.sleep(1)
    print(f"Completed task {task_name} for request {request_id}")

def process_with_background(
    data: dict,
    request_id: str = Header('X-Request-ID'),
    background_tasks: BackgroundTasks = Depends()
):
    """Process and log in background"""
    # Process
    result = {'processed': data}
    
    # Add background task
    background_tasks.add_task(log_request, request_id, "process_with_background")
    
    return result

app = mk_app([process_with_background])
```

### Pattern 3: Contextvars for Async Context

**Approach**: Use Python's contextvars for request-local storage

```python
from contextvars import ContextVar
from qh import mk_app
from qh.rules import TransformSpec, HttpLocation, NameRule
import uuid

# Create context variable for tracking ID
tracking_id_context: ContextVar[str] = ContextVar('tracking_id', default=None)

def set_tracking_id(header_value: str = None):
    """Set tracking ID in context"""
    tid = header_value or str(uuid.uuid4())
    tracking_id_context.set(tid)
    return tid

# Rule that sets context
tracking_rule = NameRule({
    'request_id': TransformSpec(
        http_location=HttpLocation.HEADER,
        http_name='X-Request-ID',
        ingress=set_tracking_id
    )
})

# Now any function can access tracking ID
def get_tracking_id():
    return tracking_id_context.get()

async def async_process(request_id: str, data: dict):
    """Async function that can access tracking ID"""
    tid = get_tracking_id()
    print(f"Request ID: {request_id}, Context ID: {tid}")
    # Both are the same ID
    return {'result': data, 'request_id': tid}

app = mk_app([async_process], config=AppConfig(rule_chain=RuleChain([tracking_rule])))
```

### Pattern 4: Custom Middleware with Header Injection

**Approach**: Add middleware to inject and manage tracking IDs

```python
from fastapi import FastAPI, Request
from qh import mk_app
import uuid
from starlette.middleware.base import BaseHTTPMiddleware

class TrackingIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Extract or generate tracking ID
        tracking_id = request.headers.get('X-Request-ID', str(uuid.uuid4()))
        
        # Add to request state for access in handlers
        request.state.tracking_id = tracking_id
        
        # Call next handler
        response = await call_next(request)
        
        # Add tracking ID to response headers
        response.headers['X-Request-ID'] = tracking_id
        
        return response

def func_with_tracking(data: dict):
    # In a real scenario, would access from request context
    return {'processed': data}

# Create app and add middleware
app = mk_app([func_with_tracking])
app.add_middleware(TrackingIDMiddleware)
```

### Pattern 5: Structured Parameters for Tracking Context

**Approach**: Create a dedicated tracking context parameter type

```python
from dataclasses import dataclass
from qh import mk_app, register_json_type
from qh.rules import TransformSpec, HttpLocation, NameRule
import uuid

@dataclass
class TrackingContext:
    request_id: str
    user_id: str = None
    session_id: str = None
    
    @classmethod
    def from_headers(cls, request_id_header: str = None, **kwargs):
        return cls(
            request_id=request_id_header or str(uuid.uuid4()),
            user_id=kwargs.get('user_id'),
            session_id=kwargs.get('session_id')
        )

# Register custom type
register_json_type(
    TrackingContext,
    to_json=lambda ctx: {
        'request_id': ctx.request_id,
        'user_id': ctx.user_id,
        'session_id': ctx.session_id
    },
    from_json=lambda data: TrackingContext(**data)
)

# Rule to extract from headers
tracking_context_rule = NameRule({
    'tracking': TransformSpec(
        http_location=HttpLocation.HEADER,
        http_name='X-Tracking-Context',
        ingress=TrackingContext.from_headers
    )
})

async def process_tracked(data: dict, tracking: TrackingContext):
    """Handler with full tracking context"""
    print(f"Request {tracking.request_id} from user {tracking.user_id}")
    return {'processed': data, 'request_id': tracking.request_id}

app = mk_app(
    [process_tracked],
    config=AppConfig(rule_chain=RuleChain([tracking_context_rule]))
)
```

## Recommended Implementation Approach

### Phase 1: Core Tracking ID Support

**Best pattern**: Pattern 1 + 3 (TransformSpec + contextvars)

**Advantages**:
- Uses existing qh architecture
- No changes to core framework
- Works with all function types
- Context available to async functions
- Simple to test

**Implementation**:
```python
# qh/tracking.py (new module)
from contextvars import ContextVar
from qh.rules import NameRule, TransformSpec, HttpLocation
from uuid import uuid4

# Context variable for request-local tracking ID
REQUEST_ID_CONTEXT: ContextVar[str] = ContextVar('request_id', default=None)

def get_request_id() -> str:
    """Get current request ID from context"""
    return REQUEST_ID_CONTEXT.get()

def set_request_id(header_value: str = None) -> str:
    """Set and return request ID"""
    tid = header_value or str(uuid4())
    REQUEST_ID_CONTEXT.set(tid)
    return tid

# Predefined rule for automatic tracking ID injection
TRACKING_ID_RULE = NameRule({
    'request_id': TransformSpec(
        http_location=HttpLocation.HEADER,
        http_name='X-Request-ID',
        ingress=set_request_id
    )
})
```

### Phase 2: Background Task Integration

**Pattern**: FastAPI's BackgroundTasks + tracking ID propagation

**Features**:
- Automatic background task creation
- Request ID passed to background tasks
- Task status tracking

### Phase 3: Distributed Tracing

**Pattern**: OpenTelemetry integration

**Features**:
- Span creation per request
- Automatic span propagation
- Integration with observability platforms

## Design Principles for qh Tracking IDs

1. **Non-Invasive**: Works without modifying user functions
2. **Opt-In**: Can be enabled selectively per-function
3. **Configurable**: Multiple header names, ID generation strategies
4. **Async-Native**: Uses contextvars, not thread-local storage
5. **Framework-Aligned**: Uses FastAPI patterns, not custom middleware

## Code Quality Considerations

### Type Safety
- Use `ContextVar[str]` with proper typing
- TransformSpec definitions are typed

### Error Handling
- Missing header → auto-generate ID
- Invalid ID format → use default generator
- Context not set → graceful fallback

### Performance
- Context variable lookup is O(1)
- No allocations in hot path
- Rule evaluation happens at app creation time

### Testing
- Existing TestClient works unchanged
- Can override tracking IDs in tests
- Context isolation between test cases

## Summary

The qh framework is **well-positioned for async tracking ID implementation** because:

1. ✅ Already async-native with proper endpoint handlers
2. ✅ Has rule-based parameter transformation system
3. ✅ Supports custom configurations per function
4. ✅ Can leverage FastAPI's Request object
5. ✅ Type-safe configuration system

**Recommended next step**: Implement Pattern 1 + 3 (TransformSpec + contextvars) as a new optional module `qh/tracking.py` that integrates cleanly with existing architecture.
