"""
FastAPI service for operating on stores objects.

This module provides a RESTful API for interacting with mall objects,
which are Mappings of MutableMappings (dict of dicts).
"""

from typing import (
    Any,
    Callable,
    Iterator,
    Mapping,
    MutableMapping,
    Optional,
    Union,
    Dict,
)
from functools import wraps
from collections.abc import ItemsView, KeysView, ValuesView

from fastapi import FastAPI, HTTPException, Path, Body
from fastapi.responses import JSONResponse
from pydantic import BaseModel


class StoreValue(BaseModel):
    """Request body for setting store values."""

    value: Any


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


def add_store_access(
    get_obj: Callable[[str], Mapping],
    app=None,
    *,
    methods: Optional[Dict[str, Optional[Dict]]] = None,
    get_obj_dispatch: Optional[Dict] = None,
    base_path: str = "/users/{user_id}/mall/{store_key}",
    write: bool = False,
    delete: bool = False,
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
        get_obj_dispatch: Configuration for how to dispatch the get_obj function
        base_path: Base path for all endpoints
        write: Whether to allow PUT operations to set values
        delete: Whether to allow DELETE operations to remove values

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

    # Default configuration for get_obj dispatch
    if get_obj_dispatch is None:
        get_obj_dispatch = {
            "path_params": ["user_id"],
            "error_code": 404,
            "error_message": "Object not found for: {user_id}",
        }

    # Default methods configuration
    default_methods = {
        "__iter__": {
            "path": "",
            "method": "get",
            "description": "List all keys in the store",
            "response_model": list[str],
        },
        "__getitem__": {
            "path": "/{item_key}",
            "method": "get",
            "description": "Get a specific item from the store",
            "path_params": ["item_key"],
        },
    }

    if write:
        default_methods["__setitem__"] = {
            "path": "/{item_key}",
            "method": "put",
            "description": "Set a value in the store",
            "path_params": ["item_key"],
            "body": "value",
            "body_model": StoreValue,
        }

    if delete:
        default_methods["__delitem__"] = {
            "path": "/{item_key}",
            "method": "delete",
            "description": "Delete an item from the store",
            "path_params": ["item_key"],
        }

    # Use provided methods or defaults
    methods = methods or default_methods

    def _get_obj_or_error(user_id: str) -> Mapping:
        """Get object or raise HTTP exception."""
        try:
            obj = get_obj(user_id)
            if obj is None:
                error_message = get_obj_dispatch["error_message"].format(
                    user_id=user_id
                )
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

    # Add endpoints for each method
    for method_name, config in methods.items():
        if config is None:
            continue

        path = base_path + config.get("path", "")
        http_method = config.get("method", "get")
        description = config.get("description", f"Execute {method_name} on the store")

        # Create a closure to capture the current values
        def create_endpoint(
            method_name=method_name, config=config, http_method=http_method
        ):
            if http_method == "get":
                if method_name == "__iter__":

                    async def endpoint(
                        user_id: str = Path(..., description="User ID"),
                    ):
                        obj = _get_obj_or_error(user_id)
                        return list(_dispatch_mapping_method(obj, method_name))

                    return endpoint
                else:  # __getitem__

                    async def endpoint(
                        user_id: str = Path(..., description="User ID"),
                        item_key: str = Path(..., description="Item key"),
                    ):
                        obj = _get_obj_or_error(user_id)
                        try:
                            value = _dispatch_mapping_method(obj, method_name, item_key)
                            return JSONResponse(
                                content={"value": _serialize_value(value)}
                            )
                        except KeyError:
                            raise HTTPException(
                                status_code=404, detail=f"Item not found: {item_key}"
                            )

                    return endpoint

            elif http_method == "put" and method_name == "__setitem__":

                async def endpoint(
                    user_id: str = Path(..., description="User ID"),
                    item_key: str = Path(..., description="Item key"),
                    body: StoreValue = Body(..., description="Value to set"),
                ):
                    obj = _get_obj_or_error(user_id)
                    try:
                        _dispatch_mapping_method(obj, method_name, item_key, body.value)
                        return {"message": "Item set successfully", "key": item_key}
                    except Exception as e:
                        raise HTTPException(
                            status_code=400, detail=f"Failed to set item: {str(e)}"
                        )

                return endpoint

            elif http_method == "delete" and method_name == "__delitem__":

                async def endpoint(
                    user_id: str = Path(..., description="User ID"),
                    item_key: str = Path(..., description="Item key"),
                ):
                    obj = _get_obj_or_error(user_id)
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

                return endpoint

        # Register the endpoint with FastAPI
        endpoint = create_endpoint()
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
    """
    Add mall/store access endpoints to a FastAPI application.

    Args:
        get_mall: Function that takes a user ID and returns a mall object
        app: Can be:
            - None: creates a new FastAPI app with default settings
            - FastAPI instance: uses this existing app
            - str: creates a new FastAPI app with this title
            - dict: creates a new FastAPI app with these kwargs
        write: Whether to allow PUT operations to set values
        delete: Whether to allow DELETE operations to remove values

    Returns:
        FastAPI application instance with mall endpoints added

    Example:

    >>> def mock_get_mall(user_id: str):
    ...     return {
    ...         'preferences': {'theme': 'dark'},
    ...         'cart': {'item1': 2}
    ...     }
    >>> app = add_mall_access(mock_get_mall) # doctest: +SKIP
    >>> isinstance(app, FastAPI) # doctest: +SKIP
    True
    """
    # Create or use app based on the input type
    if app is None:
        app = FastAPI(title="Mall API", version="1.0.0")
    elif isinstance(app, str):
        app = FastAPI(title=app, version="1.0.0")
    elif isinstance(app, dict):
        app = FastAPI(**app)
    # If it's already a FastAPI instance, use it directly

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
    async def list_mall_keys(
        user_id: str = Path(..., description="User ID")
    ) -> list[str]:
        """List all store keys in a user's mall."""
        mall = _get_mall_or_404(user_id)
        return list(_dispatch_mapping_method(mall, '__iter__'))

    # Add store-level endpoints
    store_methods = {
        "__iter__": {
            "path": "",
            "method": "get",
            "description": "List all keys in a specific store",
        },
        "__getitem__": {
            "path": "/{item_key}",
            "method": "get",
            "description": "Get a specific item from a store",
        },
    }

    if write:
        store_methods["__setitem__"] = {
            "path": "/{item_key}",
            "method": "put",
            "description": "Set a value in a store",
        }

    if delete:
        store_methods["__delitem__"] = {
            "path": "/{item_key}",
            "method": "delete",
            "description": "Delete an item from a store",
        }

    # Function to get a specific store from a mall
    def get_store(user_store_key: str) -> MutableMapping:
        parts = user_store_key.split(":", 1)
        if len(parts) != 2:
            raise ValueError("Invalid store key format, expected 'user_id:store_key'")
        user_id, store_key = parts
        mall = _get_mall_or_404(user_id)
        try:
            return mall[store_key]
        except KeyError:
            raise HTTPException(status_code=404, detail=f"Store not found: {store_key}")

    # Add store access endpoints
    add_store_access(
        get_store,
        app,
        methods=store_methods,
        get_obj_dispatch={
            "path_params": ["user_id", "store_key"],
            "error_code": 404,
            "error_message": "Store not found for user: {user_id}, store: {store_key}",
        },
        base_path="/users/{user_id}/mall/{store_key}",
        write=write,
        delete=delete,
    )

    return app


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
