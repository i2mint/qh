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
from qh.client import (
    mk_client_from_openapi,
    mk_client_from_url,
    mk_client_from_app,
    HttpClient,
)
from qh.jsclient import export_js_client, export_ts_client

# Testing utilities
from qh.testing import (
    AppRunner,
    run_app,
    test_app,
    serve_app,
    service_running,
    ServiceInfo,
    quick_test,
)

__version__ = '0.4.0'  # Phase 3: OpenAPI & Client Generation
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
    # Testing utilities
    'AppRunner',
    'run_app',
    'test_app',
    'serve_app',
    'service_running',
    'ServiceInfo',
    'quick_test',
]
