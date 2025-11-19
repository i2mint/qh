"""
Core API for creating FastAPI applications from Python functions.

This is the primary entry point for qh: mk_app()
"""

from typing import Any, Callable, Dict, List, Optional, Union
from fastapi import FastAPI

from qh.config import (
    AppConfig,
    RouteConfig,
    DEFAULT_APP_CONFIG,
    normalize_funcs_input,
    resolve_route_config,
)
from qh.endpoint import make_endpoint, validate_route_config
from qh.rules import RuleChain
from qh.conventions import (
    apply_conventions_to_funcs,
    merge_convention_config,
)


def mk_app(
    funcs: Union[Callable, List[Callable], Dict[Callable, Union[Dict[str, Any], RouteConfig]]],
    *,
    app: Optional[FastAPI] = None,
    config: Optional[Union[Dict[str, Any], AppConfig]] = None,
    use_conventions: bool = False,
    async_funcs: Optional[List[Union[str, Callable]]] = None,
    async_config: Optional[Union[Dict[str, Any], 'TaskConfig']] = None,
    **kwargs,
) -> FastAPI:
    """
    Create a FastAPI application from Python functions.

    This is the primary API for qh. It supports multiple input formats for maximum
    flexibility while maintaining simplicity for common cases.

    Args:
        funcs: Functions to expose as HTTP endpoints. Can be:
            - A single callable
            - A list of callables
            - A dict mapping callables to their route configurations

        app: Optional existing FastAPI app to add routes to.
             If None, creates a new app.

        config: Optional app-level configuration. Can be:
            - AppConfig object
            - Dict that will be converted to AppConfig
            - None (uses defaults)

        use_conventions: Whether to use convention-based routing.
            If True, infers paths and methods from function names:
            - get_user(user_id) → GET /users/{user_id}
            - list_users() → GET /users
            - create_user(user) → POST /users

        async_funcs: List of functions (by name or reference) that should support
            async task execution. When enabled, clients can add ?async=true to
            get a task ID instead of blocking for the result.

        async_config: Configuration for async task processing. Can be:
            - None (uses default TaskConfig for functions in async_funcs)
            - TaskConfig object (applies to all async_funcs)
            - Dict mapping function names to TaskConfig objects

        **kwargs: Additional FastAPI() constructor kwargs (if creating new app)

    Returns:
        FastAPI application with routes added

    Examples:
        Simple case - just functions:
        >>> def add(x: int, y: int) -> int:
        ...     return x + y
        >>> app = mk_app([add])

        With conventions:
        >>> def get_user(user_id: str): ...
        >>> def list_users(): ...
        >>> app = mk_app([get_user, list_users], use_conventions=True)

        With configuration:
        >>> app = mk_app(
        ...     [add],
        ...     config={'path_prefix': '/api', 'default_methods': ['POST']}
        ... )

        Per-function configuration:
        >>> app = mk_app({
        ...     add: {'methods': ['GET', 'POST'], 'path': '/calculate/add'},
        ... })

        With async support:
        >>> def expensive_task(n: int) -> int:
        ...     import time
        ...     time.sleep(5)
        ...     return n * 2
        >>> app = mk_app([expensive_task], async_funcs=['expensive_task'])
        # Now: POST /expensive_task?async=true returns {"task_id": "..."}
        #      GET /tasks/{task_id}/result returns the result when ready
    """
    # Normalize input formats
    func_configs = normalize_funcs_input(funcs)

    # Process async configuration
    if async_funcs:
        from qh.async_tasks import TaskConfig

        # Normalize async_config
        if async_config is None:
            # Use default config for all async functions
            default_task_config = TaskConfig()
            async_config_map = {}
        elif isinstance(async_config, dict):
            # Dict mapping function names to configs
            async_config_map = async_config
            default_task_config = TaskConfig()
        else:
            # Single TaskConfig for all functions
            default_task_config = async_config
            async_config_map = {}

        # Apply async config to specified functions
        async_func_names = set()
        for func_ref in async_funcs:
            if callable(func_ref):
                async_func_names.add(func_ref.__name__)
            else:
                async_func_names.add(str(func_ref))

        for func, route_config in func_configs.items():
            if func.__name__ in async_func_names:
                # Get function-specific config or use default
                task_config = async_config_map.get(func.__name__, default_task_config)

                # Update route config with async config
                if isinstance(route_config, RouteConfig):
                    route_config.async_config = task_config
                else:
                    # It's a dict, convert to RouteConfig
                    route_dict = route_config or {}
                    route_dict['async_config'] = task_config
                    func_configs[func] = route_dict

    # Apply conventions if requested
    if use_conventions:
        # Get list of functions
        func_list = list(func_configs.keys())

        # Infer convention-based configs
        convention_configs = apply_conventions_to_funcs(func_list, use_conventions=True)

        # Merge with explicit configs (explicit takes precedence)
        for func, convention_config in convention_configs.items():
            if func in func_configs:
                explicit_config = func_configs[func]
                # Convert RouteConfig to dict if necessary
                if isinstance(explicit_config, RouteConfig):
                    explicit_dict = {
                        k: getattr(explicit_config, k)
                        for k in ['path', 'methods', 'summary', 'tags']
                        if getattr(explicit_config, k, None) is not None
                    }
                else:
                    explicit_dict = explicit_config or {}

                merged = merge_convention_config(convention_config, explicit_dict)
                func_configs[func] = merged

    # Resolve app configuration
    if config is None:
        app_config = DEFAULT_APP_CONFIG
    elif isinstance(config, AppConfig):
        app_config = config
    elif isinstance(config, dict):
        app_config = AppConfig(**{
            k: v for k, v in config.items()
            if k in AppConfig.__dataclass_fields__
        })
    else:
        raise TypeError(f"Invalid config type: {type(config)}")

    # Create or use existing FastAPI app
    if app is None:
        fastapi_kwargs = app_config.to_fastapi_kwargs()
        fastapi_kwargs.update(kwargs)
        app = FastAPI(**fastapi_kwargs)

    # Process each function
    for func, route_config in func_configs.items():
        # Resolve complete configuration for this route
        resolved_config = resolve_route_config(func, app_config, route_config)

        # Validate configuration
        validate_route_config(func, resolved_config)

        # Create endpoint
        endpoint = make_endpoint(func, resolved_config)

        # Compute full path
        full_path = app_config.path_prefix + resolved_config.path

        # Prepare route kwargs
        route_kwargs = {
            'path': full_path,
            'endpoint': endpoint,
            'methods': resolved_config.methods,
            'name': func.__name__,
        }

        # Add optional metadata
        if resolved_config.summary:
            route_kwargs['summary'] = resolved_config.summary
        if resolved_config.description:
            route_kwargs['description'] = resolved_config.description
        if resolved_config.tags:
            route_kwargs['tags'] = resolved_config.tags
        if resolved_config.response_model:
            route_kwargs['response_model'] = resolved_config.response_model

        route_kwargs['include_in_schema'] = resolved_config.include_in_schema
        route_kwargs['deprecated'] = resolved_config.deprecated

        # Add route to app
        app.add_api_route(**route_kwargs)

    # Add task management endpoints if any async functions were configured
    if async_funcs:
        from qh.async_endpoints import add_global_task_endpoints

        # Add global task endpoints (list all tasks)
        add_global_task_endpoints(app)

        # Add per-function task endpoints
        for func in func_configs.keys():
            if func.__name__ in async_func_names:
                from qh.async_endpoints import add_task_endpoints

                # Get the task config to check if we should create endpoints
                route_config = func_configs[func]
                if isinstance(route_config, RouteConfig):
                    task_config = route_config.async_config
                elif isinstance(route_config, dict):
                    task_config = route_config.get('async_config')
                else:
                    task_config = None

                if task_config and getattr(task_config, 'create_task_endpoints', True):
                    add_task_endpoints(app, func.__name__)

    return app


def inspect_routes(app: FastAPI) -> List[Dict[str, Any]]:
    """
    Inspect routes in a FastAPI app.

    Args:
        app: FastAPI application

    Returns:
        List of route information dicts
    """
    routes = []

    for route in app.routes:
        if hasattr(route, 'methods'):
            route_info = {
                'path': route.path,
                'methods': list(route.methods),
                'name': route.name,
                'endpoint': route.endpoint,
            }
            # Include original function if available (for OpenAPI/client generation)
            if hasattr(route.endpoint, '_qh_original_func'):
                route_info['function'] = route.endpoint._qh_original_func
            routes.append(route_info)

    return routes


def print_routes(app: FastAPI) -> None:
    """
    Print formatted route table for a FastAPI app.

    Args:
        app: FastAPI application
    """
    routes = inspect_routes(app)

    if not routes:
        print("No routes found")
        return

    # Find max widths for formatting
    max_methods = max(len(', '.join(r['methods'])) for r in routes)
    max_path = max(len(r['path']) for r in routes)

    # Print header
    print(f"{'METHODS':<{max_methods}}  {'PATH':<{max_path}}  ENDPOINT")
    print("-" * (max_methods + max_path + 50))

    # Print routes
    for route in routes:
        methods = ', '.join(sorted(route['methods']))
        path = route['path']
        name = route['name']

        # Try to get endpoint signature
        endpoint = route['endpoint']
        if hasattr(endpoint, '__wrapped__'):
            endpoint = endpoint.__wrapped__

        print(f"{methods:<{max_methods}}  {path:<{max_path}}  {name}")


# Convenience aliases
create_app = mk_app
make_app = mk_app
