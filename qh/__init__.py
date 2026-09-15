"""Quick HTTP: expose Python functions as a FastAPI web service with one call.

Give ``mk_app`` a function, a list of functions, or a dict of functions to route
configs, and get back a FastAPI app whose routes call those functions. Type
hints drive request validation and the OpenAPI document; an optional
convention layer infers RESTful paths and methods from function names; a rule
chain and a type registry decide where each parameter lives in the HTTP
request and how it is (de)serialized. The same app can be tested in-process,
served, turned into a Python, JavaScript or TypeScript client, and given
background-task endpoints for long-running functions.

Main entry points:

- ``mk_app``: functions in, FastAPI app out (``qh.app``)
- ``RouteConfig`` / ``AppConfig``: per-route and app-wide configuration (``qh.config``)
- ``test_app`` / ``quick_test`` / ``service_running``: in-process and live testing (``qh.testing``)
- ``mk_client_from_app`` / ``export_openapi``: clients and the OpenAPI document (``qh.client``, ``qh.openapi``)
- ``TaskConfig``: background execution for functions named in ``async_funcs`` (``qh.async_tasks``)

>>> from qh import mk_app, test_app
>>> def add(x: int, y: int) -> int:
...     return x + y
>>> app = mk_app([add])
>>> with test_app(app) as client:
...     client.post('/add', json={'x': 3, 'y': 5}).json()
8
"""

# New primary API
from qh.app import mk_app, inspect_routes, print_routes

# Configuration and rules
from qh.config import AppConfig, RouteConfig, ConfigBuilder
from qh.rules import (
    RuleChain,
    TransformSpec,
    HttpLocation,
    TypeRule,
    NameRule,
    FuncRule,
    FuncNameRule,
)

# Type registry
from qh.types import register_type, register_json_type, TypeRegistry

# OpenAPI and client generation (Phase 3)
from qh.openapi import (
    export_openapi,
    enhance_openapi_schema,
    install_enhanced_openapi,
    python_type_to_json_schema,
)
from qh.client import (
    mk_client_from_openapi,
    mk_client_from_url,
    mk_client_from_app,
    HttpClient,
)
from qh.jsclient import export_js_client, export_ts_client

# Async task processing
from qh.async_tasks import (
    TaskConfig,
    TaskStatus,
    TaskInfo,
    TaskStore,
    InMemoryTaskStore,
    TaskExecutor,
    ThreadPoolTaskExecutor,
    ProcessPoolTaskExecutor,
    TaskManager,
)

# Testing utilities
from qh.testing import (
    AppRunner,
    run_app,
    test_app,
    serve_app,
    quick_test,
    service_running,
    ServiceInfo,
)

# au integration (optional)
try:
    from qh.au_integration import (
        use_au_backend,
        use_au_thread_backend,
        use_au_process_backend,
        use_au_redis_backend,
        AuTaskStore,
        AuTaskExecutor,
    )

    __all_au__ = [
        "use_au_backend",
        "use_au_thread_backend",
        "use_au_process_backend",
        "use_au_redis_backend",
        "AuTaskStore",
        "AuTaskExecutor",
    ]
except ImportError:
    __all_au__ = []

# Legacy API (for backward compatibility)
try:
    from py2http.service import run_app as legacy_run_app
    from py2http.decorators import mk_flat, handle_json_req
    from qh.trans import (
        transform_mapping_vals_with_name_func_map,
        mk_json_handler_from_name_mapping,
    )
    from qh.util import flat_callable_for
    from qh.main import mk_http_service_app
except ImportError:
    # py2http not available, skip legacy imports
    pass

__version__ = "0.5.0"  # Phase 4: Async Task Processing
__all__ = [
    # Primary API
    "mk_app",
    "inspect_routes",
    "print_routes",
    # Configuration
    "AppConfig",
    "RouteConfig",
    "ConfigBuilder",
    # Rules
    "RuleChain",
    "TransformSpec",
    "HttpLocation",
    "TypeRule",
    "NameRule",
    "FuncRule",
    "FuncNameRule",
    # Type Registry
    "register_type",
    "register_json_type",
    "TypeRegistry",
    # OpenAPI & Client (Phase 3)
    "export_openapi",
    "enhance_openapi_schema",
    "install_enhanced_openapi",
    "python_type_to_json_schema",
    "mk_client_from_openapi",
    "mk_client_from_url",
    "mk_client_from_app",
    "HttpClient",
    "export_js_client",
    "export_ts_client",
    # Async Tasks (Phase 4)
    "TaskConfig",
    "TaskStatus",
    "TaskInfo",
    "TaskStore",
    "InMemoryTaskStore",
    "TaskExecutor",
    "ThreadPoolTaskExecutor",
    "ProcessPoolTaskExecutor",
    "TaskManager",
    # Testing utilities
    "AppRunner",
    "run_app",
    "test_app",
    "serve_app",
    "quick_test",
    "service_running",
    "ServiceInfo",
] + __all_au__
