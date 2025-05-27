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
    >>> app = add_mall_access(mock_get_mall)
    >>> type(app).__name__
    'FastAPI'
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

    def _get_store_or_404(mall: Mapping, store_key: str) -> MutableMapping:
        """Get store from mall or raise 404."""
        try:
            return mall[store_key]
        except KeyError:
            raise HTTPException(status_code=404, detail=f"Store not found: {store_key}")

    @app.get("/users/{user_id}/mall")
    async def list_mall_keys(
        user_id: str = Path(..., description="User ID")
    ) -> list[str]:
        """List all store keys in a user's mall."""
        mall = _get_mall_or_404(user_id)
        return list(_dispatch_mapping_method(mall, '__iter__'))

    @app.get("/users/{user_id}/mall/{store_key}")
    async def list_store_keys(
        user_id: str = Path(..., description="User ID"),
        store_key: str = Path(..., description="Store key"),
    ) -> list[str]:
        """List all keys in a specific store."""
        mall = _get_mall_or_404(user_id)
        store = _get_store_or_404(mall, store_key)
        return list(_dispatch_mapping_method(store, '__iter__'))

    @app.get("/users/{user_id}/mall/{store_key}/{item_key}")
    async def get_store_item(
        user_id: str = Path(..., description="User ID"),
        store_key: str = Path(..., description="Store key"),
        item_key: str = Path(..., description="Item key"),
    ):
        """Get a specific item from a store."""
        mall = _get_mall_or_404(user_id)
        store = _get_store_or_404(mall, store_key)

        try:
            value = _dispatch_mapping_method(store, '__getitem__', item_key)
            return JSONResponse(content={"value": _serialize_value(value)})
        except KeyError:
            raise HTTPException(status_code=404, detail=f"Item not found: {item_key}")

    if write:

        @app.put("/users/{user_id}/mall/{store_key}/{item_key}")
        async def set_store_item(
            user_id: str = Path(..., description="User ID"),
            store_key: str = Path(..., description="Store key"),
            item_key: str = Path(..., description="Item key"),
            body: StoreValue = Body(..., description="Value to set"),
        ):
            """Set a value in a store."""
            mall = _get_mall_or_404(user_id)
            store = _get_store_or_404(mall, store_key)

            try:
                _dispatch_mapping_method(store, '__setitem__', item_key, body.value)
                return {"message": "Item set successfully", "key": item_key}
            except Exception as e:
                raise HTTPException(
                    status_code=400, detail=f"Failed to set item: {str(e)}"
                )

    if delete:

        @app.delete("/users/{user_id}/mall/{store_key}/{item_key}")
        async def delete_store_item(
            user_id: str = Path(..., description="User ID"),
            store_key: str = Path(..., description="Store key"),
            item_key: str = Path(..., description="Item key"),
        ):
            """Delete an item from a store."""
            mall = _get_mall_or_404(user_id)
            store = _get_store_or_404(mall, store_key)

            try:
                _dispatch_mapping_method(store, '__delitem__', item_key)
                return {"message": "Item deleted successfully", "key": item_key}
            except KeyError:
                raise HTTPException(
                    status_code=404, detail=f"Item not found: {item_key}"
                )
            except Exception as e:
                raise HTTPException(
                    status_code=400, detail=f"Failed to delete item: {str(e)}"
                )

    return app


# Keep the create_mall_app for backward compatibility
def create_mall_app(
    get_mall: Callable[[str], Mapping[str, MutableMapping]],
    *,
    app_title: str = "Mall API",
    app_version: str = "1.0.0",
    allow_mutations: bool = True,
) -> FastAPI:
    """
    Create a FastAPI application for mall operations.

    This is kept for backward compatibility.
    Consider using add_mall_access instead.
    """
    app_config = {"title": app_title, "version": app_version}
    return add_mall_access(
        get_mall, app_config, write=allow_mutations, delete=allow_mutations
    )


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
