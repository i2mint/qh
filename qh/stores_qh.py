"""
FastAPI service for operating on stores objects.

This module provides a RESTful API for interacting with mall objects,
which are Mappings of MutableMappings (dict of dicts).
"""

from typing import (
    Any,
    Callable,
    Iterator,
    List,
    Mapping,
    MutableMapping,
    Optional,
    Sequence,
    Union,
    Dict,
)
import inspect
import logging
from collections.abc import ItemsView, KeysView, ValuesView

from fastapi import Body, Depends, FastAPI, HTTPException, Path, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool
from starlette.exceptions import HTTPException as StarletteHTTPException

from qh.errors import DFLT_EXPOSE_ERRORS, error_detail

logger = logging.getLogger("qh")


class StoreValue(BaseModel):
    """Request body for setting store values."""

    value: Any


# Default method configurations
DEFAULT_ITER_CONFIG = {
    "path": "",
    "method": "get",
    "description": "List all keys in the store",
    "response_model": list[str],
}

DEFAULT_GETITEM_CONFIG = {
    "path": "/{item_key}",
    "method": "get",
    "description": "Get a specific item from the store",
    "path_params": ["item_key"],
}

DEFAULT_SETITEM_CONFIG = {
    "path": "/{item_key}",
    "method": "put",
    "description": "Set a value in the store",
    "path_params": ["item_key"],
    "body": "value",
    "body_model": StoreValue,
}

DEFAULT_DELITEM_CONFIG = {
    "path": "/{item_key}",
    "method": "delete",
    "description": "Delete an item from the store",
    "path_params": ["item_key"],
}

DEFAULT_CONTAINS_CONFIG = {
    "path": "/{item_key}/exists",
    "method": "get",
    "description": "Check if key exists in the store",
    "path_params": ["item_key"],
    "response_model": bool,
}

DEFAULT_LEN_CONFIG = {
    "path": "/$count",  # changed from "/count" to avoid key conflicts
    "method": "get",
    "description": "Get the number of items in the store",
    "response_model": int,
}

DEFAULT_METHODS = {
    "__iter__": DEFAULT_ITER_CONFIG,
    "__getitem__": DEFAULT_GETITEM_CONFIG,
    "__contains__": DEFAULT_CONTAINS_CONFIG,
    "__len__": DEFAULT_LEN_CONFIG,
}

# Default configuration for get_obj dispatch
DEFAULT_GET_OBJ_DISPATCH = {
    "path_params": ["user_id"],
    "error_code": 404,
    "error_message": "Object not found for: {user_id}",
}


def _serialize_value(value: Any) -> Any:
    """
    Serialize values for JSON response.

    >>> _serialize_value({'a': 1})
    {'a': 1}
    >>> _serialize_value(KeysView({'a': 1}))
    ['a']
    """
    if isinstance(value, (KeysView, ValuesView, ItemsView)):
        return list(value)
    elif isinstance(value, (list, tuple, set)):
        return list(value)
    elif isinstance(value, dict):
        return value
    elif isinstance(value, (str, int, float, bool, type(None))):
        return value
    else:
        # For complex objects, convert to string representation (sent to the
        # client as is: a store holding objects whose str() carries secrets
        # should serialize them itself)
        return str(value)


def _dispatch_mapping_method(
    obj: Union[Mapping, MutableMapping], method_name: str, *args, **kwargs
) -> Any:
    """
    Dispatch a method call to a mapping object.

    >>> d = {'a': 1, 'b': 2}
    >>> _dispatch_mapping_method(d, '__iter__')  # doctest: +ELLIPSIS
    <dict_keyiterator object at ...>
    >>> list(_dispatch_mapping_method(d, '__iter__'))
    ['a', 'b']
    """
    method = getattr(obj, method_name, None)
    if method is None:
        raise AttributeError(f"Object has no method '{method_name}'")

    return method(*args, **kwargs)


def create_method_endpoint(
    method_name: str,
    config: Dict,
    get_obj_fn: Callable,
    path_params: Optional[List[str]] = None,
    *,
    expose_errors: bool = DFLT_EXPOSE_ERRORS,
):
    """
    Create an endpoint function for a specific mapping method.

    Args:
        method_name: The mapping method to dispatch (e.g., '__iter__', '__getitem__')
        config: Configuration for the endpoint
        get_obj_fn: Function to retrieve the object to operate on
        path_params: List of path parameter names (e.g., ['user_id', 'store_key'])
        expose_errors: If True, a failing store operation sends its exception
            text to the client; by default the client gets a generic message
            with an error id (see ``qh.errors``).

    Returns:
        An async endpoint function compatible with FastAPI

    Raises:
        ValueError: If ``path_params`` has a length this method's branch does
            not implement (currently 1 or 2 are supported).
    """
    path_params = path_params or ["user_id"]

    def _failure_detail(exc: Exception, what: str) -> str:
        return error_detail(
            exc,
            context=method_name,
            expose_errors=expose_errors,
            exposed_text=f"{what}: {exc}",
        )

    if method_name == "__iter__":
        # Generate endpoint dynamically based on path_params
        if len(path_params) == 1:

            async def endpoint(user_id: str = Path(..., description="User ID")):
                obj = get_obj_fn(user_id)
                return list(_dispatch_mapping_method(obj, method_name))
        elif len(path_params) == 2:

            async def endpoint(
                user_id: str = Path(..., description="User ID"),
                store_key: str = Path(..., description="Store key"),
            ):
                obj = get_obj_fn(user_id, store_key)
                return list(_dispatch_mapping_method(obj, method_name))
        else:
            raise ValueError(f"Unsupported number of path params: {len(path_params)}")

        return endpoint

    elif method_name == "__getitem__":
        # Generate endpoint dynamically based on path_params
        if len(path_params) == 1:

            async def endpoint(
                user_id: str = Path(..., description="User ID"),
                item_key: str = Path(..., description="Item key"),
            ):
                obj = get_obj_fn(user_id)
                try:
                    value = _dispatch_mapping_method(obj, method_name, item_key)
                    return JSONResponse(content={"value": _serialize_value(value)})
                except KeyError:
                    raise HTTPException(
                        status_code=404, detail=f"Item not found: {item_key}"
                    )
        elif len(path_params) == 2:

            async def endpoint(
                user_id: str = Path(..., description="User ID"),
                store_key: str = Path(..., description="Store key"),
                item_key: str = Path(..., description="Item key"),
            ):
                obj = get_obj_fn(user_id, store_key)
                try:
                    value = _dispatch_mapping_method(obj, method_name, item_key)
                    return JSONResponse(content={"value": _serialize_value(value)})
                except KeyError:
                    raise HTTPException(
                        status_code=404, detail=f"Item not found: {item_key}"
                    )
        else:
            raise ValueError(f"Unsupported number of path params: {len(path_params)}")

        return endpoint

    elif method_name == "__setitem__":
        if len(path_params) == 1:

            async def endpoint(
                user_id: str = Path(..., description="User ID"),
                item_key: str = Path(..., description="Item key"),
                body: StoreValue = Body(..., description="Value to set"),
            ):
                obj = get_obj_fn(user_id)
                try:
                    _dispatch_mapping_method(obj, method_name, item_key, body.value)
                    return {"message": "Item set successfully", "key": item_key}
                except Exception as e:
                    raise HTTPException(
                        status_code=400, detail=_failure_detail(e, "Failed to set item")
                    )
        elif len(path_params) == 2:

            async def endpoint(
                user_id: str = Path(..., description="User ID"),
                store_key: str = Path(..., description="Store key"),
                item_key: str = Path(..., description="Item key"),
                body: StoreValue = Body(..., description="Value to set"),
            ):
                obj = get_obj_fn(user_id, store_key)
                try:
                    _dispatch_mapping_method(obj, method_name, item_key, body.value)
                    return {"message": "Item set successfully", "key": item_key}
                except Exception as e:
                    raise HTTPException(
                        status_code=400, detail=_failure_detail(e, "Failed to set item")
                    )
        else:
            raise ValueError(f"Unsupported number of path params: {len(path_params)}")

        return endpoint

    elif method_name == "__delitem__":
        if len(path_params) == 1:

            async def endpoint(
                user_id: str = Path(..., description="User ID"),
                item_key: str = Path(..., description="Item key"),
            ):
                obj = get_obj_fn(user_id)
                try:
                    _dispatch_mapping_method(obj, method_name, item_key)
                    return {"message": "Item deleted successfully", "key": item_key}
                except KeyError:
                    raise HTTPException(
                        status_code=404, detail=f"Item not found: {item_key}"
                    )
                except Exception as e:
                    raise HTTPException(
                        status_code=400,
                        detail=_failure_detail(e, "Failed to delete item"),
                    )
        elif len(path_params) == 2:

            async def endpoint(
                user_id: str = Path(..., description="User ID"),
                store_key: str = Path(..., description="Store key"),
                item_key: str = Path(..., description="Item key"),
            ):
                obj = get_obj_fn(user_id, store_key)
                try:
                    _dispatch_mapping_method(obj, method_name, item_key)
                    return {"message": "Item deleted successfully", "key": item_key}
                except KeyError:
                    raise HTTPException(
                        status_code=404, detail=f"Item not found: {item_key}"
                    )
                except Exception as e:
                    raise HTTPException(
                        status_code=400,
                        detail=_failure_detail(e, "Failed to delete item"),
                    )
        else:
            raise ValueError(f"Unsupported number of path params: {len(path_params)}")

        return endpoint

    elif method_name == "__contains__":
        if len(path_params) == 1:

            async def endpoint(
                user_id: str = Path(..., description="User ID"),
                item_key: str = Path(..., description="Item key"),
            ):
                obj = get_obj_fn(user_id)
                try:
                    exists = _dispatch_mapping_method(obj, method_name, item_key)
                    return exists
                except Exception as e:
                    raise HTTPException(
                        status_code=400,
                        detail=_failure_detail(e, "Failed to check if item exists"),
                    )
        elif len(path_params) == 2:

            async def endpoint(
                user_id: str = Path(..., description="User ID"),
                store_key: str = Path(..., description="Store key"),
                item_key: str = Path(..., description="Item key"),
            ):
                obj = get_obj_fn(user_id, store_key)
                try:
                    exists = _dispatch_mapping_method(obj, method_name, item_key)
                    return exists
                except Exception as e:
                    raise HTTPException(
                        status_code=400,
                        detail=_failure_detail(e, "Failed to check if item exists"),
                    )
        else:
            raise ValueError(f"Unsupported number of path params: {len(path_params)}")

        return endpoint

    elif method_name == "__len__":
        if len(path_params) == 1:

            async def endpoint(user_id: str = Path(..., description="User ID")):
                obj = get_obj_fn(user_id)
                try:
                    count = _dispatch_mapping_method(obj, method_name)
                    return count
                except Exception as e:
                    raise HTTPException(
                        status_code=400,
                        detail=_failure_detail(e, "Failed to get item count"),
                    )
        elif len(path_params) == 2:

            async def endpoint(
                user_id: str = Path(..., description="User ID"),
                store_key: str = Path(..., description="Store key"),
            ):
                obj = get_obj_fn(user_id, store_key)
                try:
                    count = _dispatch_mapping_method(obj, method_name)
                    return count
                except Exception as e:
                    raise HTTPException(
                        status_code=400,
                        detail=_failure_detail(e, "Failed to get item count"),
                    )
        else:
            raise ValueError(f"Unsupported number of path params: {len(path_params)}")

        return endpoint

    else:
        # Generic handler for other methods
        async def endpoint(
            user_id: str = Path(..., description="User ID"),
            item_key: Optional[str] = Query(None, description="Item key"),
        ):
            obj = get_obj_fn(user_id)
            args = []
            if item_key is not None:
                args.append(item_key)
            result = _dispatch_mapping_method(obj, method_name, *args)
            return JSONResponse(content={"value": _serialize_value(result)})

        return endpoint


def add_store_access(
    get_obj: Callable[[str], Mapping],
    app=None,
    *,
    methods: Optional[Dict[str, Optional[Dict]]] = None,
    get_obj_dispatch: Optional[Dict] = None,
    base_path: str = "/users/{user_id}/mall/{store_key}",
    dependencies: Optional[Sequence] = None,
    expose_errors: bool = DFLT_EXPOSE_ERRORS,
) -> FastAPI:
    """
    Add store access endpoints to a FastAPI application.

    Args:
        get_obj: Function that takes an identifier and returns a mapping object
        app: Can be:

            - None: creates a new FastAPI app with default settings
            - FastAPI instance: uses this existing app
            - str: creates a new FastAPI app with this title
            - dict: creates a new FastAPI app with these kwargs

        methods: Dictionary mapping method names to dispatch configuration

            - Key is the mapping method name (e.g., '__iter__', '__getitem__')
            - Value is None to use defaults or a dict with configuration

        get_obj_dispatch: Configuration for how to dispatch the get_obj function
        base_path: Base path for all endpoints
        dependencies: FastAPI dependencies (e.g. ``[Depends(check_caller)]``)
            added to every route this function registers; the place for an
            authentication or authorization check.
        expose_errors: If True, exceptions raised by ``get_obj`` or by a store
            operation are sent to the client as text. By default the client
            gets ``get_obj_dispatch['error_message']`` (which only echoes the
            path parameters) or a generic message with an error id, and the
            exception is logged server-side (see ``qh.errors``).

    Returns:
        FastAPI application instance with store endpoints added
    """
    # Create or use app based on the input type
    if app is None:
        app = FastAPI(title="Store API", version="1.0.0")
    elif isinstance(app, str):
        app = FastAPI(title=app, version="1.0.0")
    elif isinstance(app, dict):
        app = FastAPI(**app)
    # If it's already a FastAPI instance, use it directly

    # Use provided configuration or defaults
    get_obj_dispatch = get_obj_dispatch or DEFAULT_GET_OBJ_DISPATCH
    methods = methods or DEFAULT_METHODS.copy()

    # Extract path parameters from base_path or get_obj_dispatch
    import re

    if "path_params" in get_obj_dispatch:
        path_params = get_obj_dispatch["path_params"]
    else:
        # Extract from base_path
        path_params = re.findall(r"\{(\w+)\}", base_path)

    # Process methods dict to apply defaults
    for method_name, config in list(methods.items()):
        if config is None:
            # Use default configuration if available
            if method_name == "__iter__":
                methods[method_name] = DEFAULT_ITER_CONFIG.copy()
            elif method_name == "__getitem__":
                methods[method_name] = DEFAULT_GETITEM_CONFIG.copy()
            elif method_name == "__setitem__":
                methods[method_name] = DEFAULT_SETITEM_CONFIG.copy()
            elif method_name == "__delitem__":
                methods[method_name] = DEFAULT_DELITEM_CONFIG.copy()
            elif method_name == "__contains__":
                methods[method_name] = DEFAULT_CONTAINS_CONFIG.copy()
            elif method_name == "__len__":
                methods[method_name] = DEFAULT_LEN_CONFIG.copy()
            else:
                # No default available for this method
                continue

    def _not_found_detail(args) -> str:
        error_params = {param: arg for param, arg in zip(path_params, args)}
        try:
            return get_obj_dispatch["error_message"].format(**error_params)
        except (KeyError, IndexError, AttributeError, ValueError):  # no or bad template
            return "Object not found"

    def _get_obj_or_error(*args) -> Mapping:
        """Get object or raise HTTP exception."""
        error_code = get_obj_dispatch.get("error_code", 404)
        try:
            obj = get_obj(*args)
        except StarletteHTTPException:
            raise
        except Exception as e:
            if expose_errors:
                detail = str(e)
            else:
                logger.info("get_obj failed for %s", args, exc_info=e)
                detail = _not_found_detail(args)
            raise HTTPException(status_code=error_code, detail=detail)
        if obj is None:
            raise HTTPException(status_code=error_code, detail=_not_found_detail(args))
        return obj

    # Reorder endpoints to prioritize static routes over dynamic ones
    ordered_methods = [
        "__iter__",
        "__len__",
        "__contains__",
        "__getitem__",
        "__setitem__",
        "__delitem__",
    ]
    for method_name in ordered_methods:
        config = methods.get(method_name)
        if not config:
            continue
        path = base_path + config.get("path", "")
        http_method = config.get("method", "get")
        description = config.get("description", f"Execute {method_name} on the store")
        endpoint = create_method_endpoint(
            method_name,
            config,
            _get_obj_or_error,
            path_params,
            expose_errors=expose_errors,
        )
        getattr(app, http_method)(
            path,
            response_model=config.get("response_model", None),
            description=description,
            dependencies=list(dependencies or []),
        )(endpoint)

    # Register any additional methods not in the ordered list
    for method_name, config in methods.items():
        if method_name in ordered_methods or not config:
            continue
        path = base_path + config.get("path", "")
        http_method = config.get("method", "get")
        description = config.get("description", f"Execute {method_name} on the store")
        endpoint = create_method_endpoint(
            method_name,
            config,
            _get_obj_or_error,
            path_params,
            expose_errors=expose_errors,
        )
        getattr(app, http_method)(
            path,
            response_model=config.get("response_model", None),
            description=description,
            dependencies=list(dependencies or []),
        )(endpoint)

    return app


def add_mall_access(
    get_mall: Callable[[str], Mapping[str, MutableMapping]],
    app=None,
    *,
    write: bool = False,
    delete: bool = False,
    caller: Optional[Callable[[Request], Any]] = None,
    expose_errors: bool = DFLT_EXPOSE_ERRORS,
) -> FastAPI:
    """Add mall/store access endpoints to a FastAPI application.

    Routes live under ``/users/{user_id}/mall``, so without an access check any
    client can address any user's mall. ``caller`` is that check.

    Args:
        get_mall: Function that takes a ``user_id`` and returns that user's mall
            (a mapping of store keys to stores).
        app: ``None``, a ``FastAPI`` instance, a title string, or a dict of
            ``FastAPI`` kwargs (as in ``add_store_access``).
        write: If True, add a ``PUT`` route to set store items.
        delete: If True, add a ``DELETE`` route to delete store items.
        caller: ``caller(request) -> user id`` (sync or async) identifying the
            authenticated client, e.g. from a session or a verified token. When
            given, every route checks that it equals the ``user_id`` in the URL
            before the mall is looked up: an unknown caller (``None``, ``""`` or
            a bool) gets 401, a different user 403. To reject a request with
            another status (e.g. a bad token), raise ``HTTPException`` from
            ``caller``; any other exception becomes a 500. A sync ``caller``
            runs in a thread pool, so it may block. The comparison is exact, so
            ``get_mall`` should not normalise ids (case, whitespace) that
            ``caller`` returns un-normalised. When ``None`` (the default),
            no check is made, which is only appropriate when every client may
            read (and, with ``write``/``delete``, change) every user's mall.
        expose_errors: If True, exceptions raised by ``get_mall`` or by a store
            operation are sent to the client as text (see ``add_store_access``).

    >>> from fastapi.testclient import TestClient
    >>> malls = {'alice': {'notes': {'a': 1}}, 'bob': {'notes': {'b': 2}}}
    >>> app = add_mall_access(
    ...     malls.get, caller=lambda request: request.headers.get('x-user')
    ... )
    >>> client = TestClient(app)
    >>> client.get('/users/alice/mall', headers={'x-user': 'alice'}).json()
    ['notes']
    >>> client.get('/users/bob/mall/notes', headers={'x-user': 'alice'}).status_code
    403
    >>> client.get('/users/bob/mall').status_code
    401
    """
    # Create or use app based on the input type
    if app is None:
        app = FastAPI(title="Mall API", version="1.0.0")
    elif isinstance(app, str):
        app = FastAPI(title=app, version="1.0.0")
    elif isinstance(app, dict):
        app = FastAPI(**app)

    dependencies = [] if caller is None else [Depends(_caller_check(caller))]

    def _get_mall_or_404(user_id: str) -> Mapping[str, MutableMapping]:
        """Get mall for user or raise 404."""
        not_found = f"Mall not found for user: {user_id}"
        try:
            mall = get_mall(user_id)
        except StarletteHTTPException:
            raise
        except Exception as e:
            # If get_mall raises an exception, treat as 404
            if expose_errors:
                raise HTTPException(status_code=404, detail=str(e))
            logger.info("get_mall failed for user %r", user_id, exc_info=e)
            raise HTTPException(status_code=404, detail=not_found)
        if mall is None:
            raise HTTPException(status_code=404, detail=not_found)
        return mall

    # Add mall-level endpoint to list all store keys
    @app.get("/users/{user_id}/mall", dependencies=dependencies)
    def list_user_mall_stores(
        user_id: str = Path(..., description="User ID"),
    ) -> list[str]:
        """List all store keys in a user's mall."""
        mall = _get_mall_or_404(user_id)
        return list(_dispatch_mapping_method(mall, "__iter__"))

    # Prepare store methods based on write/delete flags
    store_methods = {
        "__iter__": None,  # Use default config
        "__getitem__": None,  # Use default config
    }
    if write:
        store_methods["__setitem__"] = None  # Use default config

    if delete:
        store_methods["__delitem__"] = None  # Use default config

    # Function to get a specific store from a mall (refactored: use user_id and store_key separately)
    def get_store(user_id: str, store_key: str) -> MutableMapping:
        mall = _get_mall_or_404(user_id)
        try:
            return mall[store_key]
        except KeyError:
            raise HTTPException(status_code=404, detail=f"Store not found: {store_key}")

    # Add store access endpoints (refactored: use user_id and store_key as separate path params)
    def get_store_wrapper(
        user_id: str = Path(..., description="User ID"),
        store_key: str = Path(..., description="Store key"),
    ):
        return get_store(user_id, store_key)

    add_store_access(
        get_store_wrapper,
        app,
        methods=store_methods,
        get_obj_dispatch={
            "error_message": "Store not found for user: {user_id}, store: {store_key}",
            "path_params": ["user_id", "store_key"],
            "error_code": 404,
        },
        base_path="/users/{user_id}/mall/{store_key}",
        dependencies=dependencies,
        expose_errors=expose_errors,
    )

    return app


def _caller_check(caller: Callable[[Request], Any]) -> Callable:
    """Make a FastAPI dependency that requires ``caller(request)`` to be the
    ``user_id`` path parameter: 401 if the caller is unknown (``None``, ``""``,
    or a bool, a common "no user" sentinel that would otherwise match a user
    called ``False``), 403 if it is someone else."""

    async def check_caller(
        request: Request, user_id: str = Path(..., description="User ID")
    ) -> None:
        if inspect.iscoroutinefunction(caller):
            who = await caller(request)
        else:
            who = await run_in_threadpool(caller, request)
            if inspect.isawaitable(who):
                who = await who
        if who is None or isinstance(who, bool) or who == "":
            raise HTTPException(status_code=401, detail="Not authenticated")
        if str(who) != user_id:
            raise HTTPException(status_code=403, detail="Not allowed")

    return check_caller


# Example usage and runner
# Example usage and runner
if __name__ == "__main__":
    # Example mall implementation for testing
    _user_malls = {
        "user123": {
            "preferences": {"theme": "dark", "language": "en"},
            "cart": {"item1": 2, "item2": 1},
            "wishlist": {"product_a": True, "product_b": True},
        }
    }

    def example_get_mall(user_id: str) -> Mapping[str, MutableMapping]:
        """Example mall getter for demonstration."""
        if user_id not in _user_malls:
            _user_malls[user_id] = {}
        return _user_malls[user_id]

    # Create the app
    app = add_mall_access(
        example_get_mall,
        "User Mall Service",
        write=True,
        delete=True,
    )

    # Run with: uvicorn module_name:app --reload
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
