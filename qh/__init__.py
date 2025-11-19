"""
qh: Quick HTTP service for Python

Convention-over-configuration tool for exposing Python functions as HTTP services.
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
from qh.openapi import export_openapi, enhance_openapi_schema
from qh.client import mk_client_from_openapi, mk_client_from_url, mk_client_from_app, HttpClient
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
from qh.testing import AppRunner, run_app, test_app, serve_app, quick_test

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

__version__ = '0.5.0'  # Phase 4: Async Task Processing
__all__ = [
    # Primary API
    'mk_app',
    'inspect_routes',
    'print_routes',
    # Configuration
    'AppConfig',
    'RouteConfig',
    'ConfigBuilder',
    # Rules
    'RuleChain',
    'TransformSpec',
    'HttpLocation',
    'TypeRule',
    'NameRule',
    'FuncRule',
    'FuncNameRule',
    # Type Registry
    'register_type',
    'register_json_type',
    'TypeRegistry',
    # OpenAPI & Client (Phase 3)
    'export_openapi',
    'enhance_openapi_schema',
    'mk_client_from_openapi',
    'mk_client_from_url',
    'mk_client_from_app',
    'HttpClient',
    'export_js_client',
    'export_ts_client',
    # Async Tasks (Phase 4)
    'TaskConfig',
    'TaskStatus',
    'TaskInfo',
    'TaskStore',
    'InMemoryTaskStore',
    'TaskExecutor',
    'ThreadPoolTaskExecutor',
    'ProcessPoolTaskExecutor',
    'TaskManager',
    # Testing utilities
    'AppRunner',
    'run_app',
    'test_app',
    'serve_app',
    'quick_test',
]
