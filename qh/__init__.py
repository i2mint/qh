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

# Legacy API (for backward compatibility)
try:
    from py2http.service import run_app
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

__version__ = '0.2.0'
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
]
