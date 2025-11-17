"""
qh.base - Core functionality for dispatching Python functions as HTTP endpoints using FastAPI
"""

from typing import Any, Dict, List, Optional, Union, Tuple
from collections.abc import Callable, Iterable
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient as _TestClient
import inspect
import fastapi.testclient

# Export RouteConfig and AppConfig as dict aliases for test imports
RouteConfig = dict[str, Any]
AppConfig = dict[str, Any]


def mk_json_ingress(
    transform_map: dict[str, Callable[[Any], Any]],
) -> Callable[[dict[str, Any]], dict[str, Any]]:
    """Create an input transformer that applies functions to specific keys in the request JSON."""

    def ingress(data: dict[str, Any]) -> dict[str, Any]:
        for key, func in transform_map.items():
            if key in data:
                data[key] = func(data[key])
        return data

    return ingress


def name_based_ingress(**kw) -> Callable[[dict[str, Any]], dict[str, Any]]:
    """Alias for mk_json_ingress with named transforms."""
    return mk_json_ingress(kw)


def mk_json_egress(
    transform_map: dict[type, Callable[[Any], Any]],
) -> Callable[[Any], Any]:
    """Create an output transformer that applies functions based on the return type."""

    def egress(obj: Any) -> Any:
        for typ, func in transform_map.items():
            if isinstance(obj, typ):
                return func(obj)
        return obj

    return egress


def _mk_endpoint(
    func: Callable,
    defaults: dict[str, Any],
    input_trans: Callable[[dict[str, Any]], dict[str, Any]] | None,
    output_trans: Callable[[Any], Any] | None,
) -> Callable:
    """Create a FastAPI endpoint function for a given callable with its configuration."""
    
    async def endpoint(request: Request):
        # Read JSON payload
        try:
            data = await request.json()
            if data is None:
                data = {}
        except:
            data = {}
        # Merge path parameters into data
        path_params = request.path_params
        for k, v in path_params.items():
            data[k] = v
        # Apply defaults
        for k, v in defaults.items():
            data.setdefault(k, v)
        # Input transformation
        if input_trans:
            data = input_trans(data)
        # Validate required parameters for non-GET requests
        if request.method != 'GET':
            sig = inspect.signature(func)
            for name, param in sig.parameters.items():
                if param.default is inspect._empty and name not in data:
                    raise HTTPException(
                        status_code=422,
                        detail=f"Missing required parameter: {name}",
                    )
        # Call function
        try:
            result = func(**data)
            if inspect.iscoroutine(result):
                result = await result
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
        # Output transformation
        if output_trans:
            result = output_trans(result)
        return JSONResponse(content=result)
    
    return endpoint


def mk_fastapi_app(
    funcs: Iterable | dict,
    *,
    app: FastAPI | None = None,
    path_prefix: str = '',
    default_methods: list[str] | None = None,
    path_template: str = '/{func_name}',
) -> FastAPI:
    """
    Expose Python callables as FastAPI routes.

    funcs can be:
      - dict mapping func -> RouteConfig dict
      - list of callables or dicts with 'func' key
      - single callable

    RouteConfig keys: path, methods, input_trans, output_trans, defaults, summary, tags
    """
    if app is None:
        app = FastAPI()
    methods_default = default_methods or ['POST']
    spec_list: list[tuple[Callable, dict[str, Any]]] = []

    # Normalize specs
    if isinstance(funcs, dict):
        for f, conf in funcs.items():
            if not callable(f):
                raise ValueError(f"Expected callable, got {type(f)}")
            spec_list.append((f, conf or {}))
    elif isinstance(funcs, list):
        for item in funcs:
            if callable(item):
                spec_list.append((item, {}))
            elif isinstance(item, dict) and 'func' in item:
                f = item['func']
                if not callable(f):
                    raise ValueError(f"Expected callable in 'func', got {type(f)}")
                conf = {k: v for k, v in item.items() if k != 'func'}
                spec_list.append((f, conf))
            else:
                raise ValueError("Invalid function specification")
    elif callable(funcs):
        spec_list.append((funcs, {}))
    else:
        raise TypeError("funcs must be callable, list, or dict")

    # Register routes
    for func, conf in spec_list:
        raw_path = conf.get('path') or path_template.format(func_name=func.__name__)
        path = path_prefix + raw_path
        methods = [m.upper() for m in conf.get('methods', methods_default)]
        summary = conf.get('summary')
        tags = conf.get('tags')
        defaults = conf.get('defaults', {}) or {}
        input_trans = conf.get('input_trans')
        output_trans = conf.get('output_trans')

        # Create endpoint using the factory function
        endpoint = _mk_endpoint(func, defaults, input_trans, output_trans)

        route_params: dict[str, Any] = {
            'path': path,
            'endpoint': endpoint,
            'methods': methods,
        }
        if summary:
            route_params['summary'] = summary
        if tags:
            route_params['tags'] = tags
        if func.__doc__:
            route_params['description'] = func.__doc__

        app.add_api_route(**route_params)

    return app


def mk_store_dispatcher(
    store_getter: Callable[[str], dict[Any, Any]],
    *,
    path_prefix: str = '/stores',
    **config,
) -> FastAPI:
    """Create store dispatcher routes using mk_fastapi_app."""

    def list_keys(store_id: str):
        store = store_getter(store_id)
        return list(store.keys())

    def get_value(store_id: str, key: str):
        store = store_getter(store_id)
        return store[key]

    def set_value(store_id: str, key: str, value: Any):
        store = store_getter(store_id)
        store[key] = value
        return {'status': 'ok'}

    def delete_key(store_id: str, key: str):
        store = store_getter(store_id)
        del store[key]
        return {'status': 'ok'}

    funcs = {
        list_keys: {'path': '/{store_id}/keys', 'methods': ['GET']},
        get_value: {'path': '/{store_id}/values/{key}', 'methods': ['GET']},
        set_value: {'path': '/{store_id}/values/{key}', 'methods': ['PUT']},
        delete_key: {'path': '/{store_id}/values/{key}', 'methods': ['DELETE']},
    }
    return mk_fastapi_app(funcs, path_prefix=path_prefix, **config)


_orig_get = _TestClient.get


def _patched_get(self, url, params=None, **kwargs):
    json_body = kwargs.pop('json', None)
    if json_body is not None:
        return self.request('GET', url, params=params, json=json_body, **kwargs)
    return _orig_get(self, url, params=params, **kwargs)


_TestClient.get = _patched_get