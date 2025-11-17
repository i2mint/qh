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
    Union,
    Dict,
)
from functools import wraps, partial
from collections.abc import ItemsView, KeysView, ValuesView

from fastapi import FastAPI, HTTPException, Path, Body
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from i2 import Pipe


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
        # For complex objects, convert to string representation
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
    path_params: Optional[List[str]] = None
):
    """
    Create an endpoint function for a specific mapping method.

    Args:
        method_name: The mapping method to dispatch (e.g., '__iter__', '__getitem__')
        config: Configuration for the endpoint
        get_obj_fn: Function to retrieve the object to operate on
        path_params: List of path parameter names (e.g., ['user_id', 'store_key'])

    Returns:
        An async endpoint function compatible with FastAPI
    """
    http_method = config.get("method", "get")
    path_params = path_params or ["user_id"]

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
                        status_code=400, detail=f"Failed to set item: {str(e)}"
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
                        status_code=400, detail=f"Failed to set item: {str(e)}"
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
                        status_code=400, detail=f"Failed to delete item: {str(e)}"
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
                        status_code=400, detail=f"Failed to delete item: {str(e)}"
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
                        status_code=400, detail=f"Failed to check if item exists: {str(e)}"
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
                        status_code=400, detail=f"Failed to check if item exists: {str(e)}"
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
                        status_code=400, detail=f"Failed to get item count: {str(e)}"
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
                        status_code=400, detail=f"Failed to get item count: {str(e)}"
                    )
        else:
            raise ValueError(f"Unsupported number of path params: {len(path_params)}")

        return endpoint

    else:
        # Generic handler for other methods
        async def endpoint(
            user_id: str = Path(..., description="User ID"),
            item_key: str = Path(..., description="Item key", default=None),
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
        path_params = re.findall(r'\{(\w+)\}', base_path)

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

    def _get_obj_or_error(*args) -> Mapping:
        """Get object or raise HTTP exception."""
        try:
            obj = get_obj(*args)
            if obj is None:
                # Format error message with all path params
                error_params = {param: arg for param, arg in zip(path_params, args)}
                error_message = get_obj_dispatch["error_message"].format(**error_params)
                raise HTTPException(
                    status_code=get_obj_dispatch["error_code"], detail=error_message
                )
            return obj
        except Exception as e:
            if isinstance(e, HTTPException):
                raise
            raise HTTPException(
                status_code=get_obj_dispatch["error_code"], detail=str(e)
            )

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
        endpoint = create_method_endpoint(method_name, config, _get_obj_or_error, path_params)
        getattr(app, http_method)(
            path,
            response_model=config.get("response_model", None),
            description=description,
        )(endpoint)

    # Register any additional methods not in the ordered list
    for method_name, config in methods.items():
        if method_name in ordered_methods or not config:
            continue
        path = base_path + config.get("path", "")
        http_method = config.get("method", "get")
        description = config.get("description", f"Execute {method_name} on the store")
        endpoint = create_method_endpoint(method_name, config, _get_obj_or_error, path_params)
        getattr(app, http_method)(
            path,
            response_model=config.get("response_model", None),
            description=description,
        )(endpoint)

    return app


def add_mall_access(
    get_mall: Callable[[str], Mapping[str, MutableMapping]],
    app=None,
    *,
    write: bool = False,
    delete: bool = False,
) -> FastAPI:
    """Add mall/store access endpoints to a FastAPI application."""
    # Create or use app based on the input type
    if app is None:
        app = FastAPI(title="Mall API", version="1.0.0")
    elif isinstance(app, str):
        app = FastAPI(title=app, version="1.0.0")
    elif isinstance(app, dict):
        app = FastAPI(**app)

    def _get_mall_or_404(user_id: str) -> Mapping[str, MutableMapping]:
        """Get mall for user or raise 404."""
        try:
            mall = get_mall(user_id)
            if mall is None:
                raise HTTPException(
                    status_code=404, detail=f"Mall not found for user: {user_id}"
                )
            return mall
        except Exception as e:
            # If get_mall raises an exception, treat as 404
            raise HTTPException(status_code=404, detail=str(e))

    # Add mall-level endpoint to list all store keys
    @app.get("/users/{user_id}/mall")
    def list_user_mall_stores(
        user_id: str = Path(..., description="User ID")
    ) -> list[str]:
        """List all store keys in a user's mall."""
        mall = _get_mall_or_404(user_id)
        return list(_dispatch_mapping_method(mall, '__iter__'))

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
        import logging
        logging.basicConfig(level=logging.INFO)
        logging.info(
            f"get_store: mall keys for user {user_id}: {list(mall.keys())}, requested store_key: {store_key}"
        )
        try:
            return mall[store_key]
        except KeyError:
            raise HTTPException(status_code=404, detail=f"Store not found: {store_key}")

    # Add store access endpoints (refactored: use user_id and store_key as separate path params)
    def get_store_wrapper(user_id: str = Path(..., description="User ID"), store_key: str = Path(..., description="Store key")):
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
    )

    return app


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

    uvicorn.run(app, host="0.0.0.0", port=8000)
