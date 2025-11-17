"""
Type registry for qh - automatic serialization/deserialization for custom types.

Supports:
- NumPy arrays and dtypes
- Pandas DataFrames and Series
- Custom user types
- Pydantic models

The type registry maps Python types to HTTP representations and provides
automatic conversion functions (ingress/egress transformations).
"""

from typing import Any, Callable, Dict, Optional, Type, TypeVar, get_origin
from dataclasses import dataclass
import inspect

from qh.rules import TransformSpec, HttpLocation


T = TypeVar('T')


@dataclass
class TypeHandler:
    """
    Handler for serializing/deserializing a specific type.

    Attributes:
        python_type: The Python type this handler manages
        to_json: Function to serialize Python object to JSON-compatible format
        from_json: Function to deserialize JSON to Python object
        http_location: Where in HTTP request/response this appears
        content_type: Optional HTTP content type for binary data
    """

    python_type: Type
    to_json: Callable[[Any], Any]
    from_json: Callable[[Any], Any]
    http_location: HttpLocation = HttpLocation.JSON_BODY
    content_type: Optional[str] = None

    def to_transform_spec(self) -> TransformSpec:
        """Convert this handler to a TransformSpec."""
        return TransformSpec(
            http_location=self.http_location,
            ingress=self.from_json,
            egress=self.to_json,
        )


class TypeRegistry:
    """
    Registry for type handlers.

    Manages conversion between Python types and HTTP representations.
    """

    def __init__(self):
        self.handlers: Dict[Type, TypeHandler] = {}
        self._init_builtin_handlers()

    def _init_builtin_handlers(self):
        """Initialize handlers for Python builtins."""
        # Builtins pass through (FastAPI handles them)
        for typ in [str, int, float, bool, list, dict, type(None)]:
            self.register(
                typ,
                to_json=lambda x: x,
                from_json=lambda x: x,
            )

    def register(
        self,
        python_type: Type[T],
        *,
        to_json: Callable[[T], Any],
        from_json: Callable[[Any], T],
        http_location: HttpLocation = HttpLocation.JSON_BODY,
        content_type: Optional[str] = None,
    ) -> None:
        """
        Register a type handler.

        Args:
            python_type: The Python type
            to_json: Function to serialize to JSON-compatible format
            from_json: Function to deserialize from JSON
            http_location: Where this appears in HTTP
            content_type: Optional content type for binary data
        """
        handler = TypeHandler(
            python_type=python_type,
            to_json=to_json,
            from_json=from_json,
            http_location=http_location,
            content_type=content_type,
        )
        self.handlers[python_type] = handler

    def get_handler(self, python_type: Type) -> Optional[TypeHandler]:
        """
        Get handler for a type.

        Args:
            python_type: The type to look up

        Returns:
            TypeHandler if registered, None otherwise
        """
        # Exact match first
        if python_type in self.handlers:
            return self.handlers[python_type]

        # Check type hierarchy
        for registered_type, handler in self.handlers.items():
            try:
                if isinstance(python_type, type) and issubclass(python_type, registered_type):
                    return handler
            except TypeError:
                # Not a class
                pass

        # Check generic types
        origin = get_origin(python_type)
        if origin is not None and origin in self.handlers:
            return self.handlers[origin]

        return None

    def get_transform_spec(self, python_type: Type) -> Optional[TransformSpec]:
        """Get TransformSpec for a type."""
        handler = self.get_handler(python_type)
        if handler:
            return handler.to_transform_spec()
        return None

    def unregister(self, python_type: Type) -> None:
        """Unregister a type handler."""
        self.handlers.pop(python_type, None)


# Global type registry
_global_registry = TypeRegistry()


def register_type(
    python_type: Type[T],
    *,
    to_json: Callable[[T], Any],
    from_json: Callable[[Any], T],
    http_location: HttpLocation = HttpLocation.JSON_BODY,
    content_type: Optional[str] = None,
) -> None:
    """
    Register a type in the global registry.

    Args:
        python_type: The Python type
        to_json: Function to serialize to JSON-compatible format
        from_json: Function to deserialize from JSON
        http_location: Where this appears in HTTP
        content_type: Optional content type for binary data

    Example:
        >>> import numpy as np
        >>> register_type(
        ...     np.ndarray,
        ...     to_json=lambda arr: arr.tolist(),
        ...     from_json=lambda lst: np.array(lst)
        ... )
    """
    _global_registry.register(
        python_type,
        to_json=to_json,
        from_json=from_json,
        http_location=http_location,
        content_type=content_type,
    )


def get_type_handler(python_type: Type) -> Optional[TypeHandler]:
    """Get handler for a type from global registry."""
    return _global_registry.get_handler(python_type)


def get_transform_spec_for_type(python_type: Type) -> Optional[TransformSpec]:
    """Get TransformSpec for a type from global registry."""
    return _global_registry.get_transform_spec(python_type)


# NumPy support (if available)
try:
    import numpy as np

    def numpy_array_to_json(arr: np.ndarray) -> Any:
        """Convert NumPy array to JSON-compatible format."""
        # Handle different dtypes
        if np.issubdtype(arr.dtype, np.integer):
            return arr.tolist()
        elif np.issubdtype(arr.dtype, np.floating):
            return arr.tolist()
        elif arr.dtype == np.bool_:
            return arr.tolist()
        else:
            # Generic fallback
            return arr.tolist()

    def numpy_array_from_json(data: Any) -> np.ndarray:
        """Convert JSON data to NumPy array."""
        return np.array(data)

    # Register NumPy array
    register_type(
        np.ndarray,
        to_json=numpy_array_to_json,
        from_json=numpy_array_from_json,
    )

except ImportError:
    # NumPy not available
    pass


# Pandas support (if available)
try:
    import pandas as pd

    def dataframe_to_json(df: pd.DataFrame) -> Any:
        """Convert DataFrame to JSON-compatible format."""
        return df.to_dict(orient='records')

    def dataframe_from_json(data: Any) -> pd.DataFrame:
        """Convert JSON data to DataFrame."""
        if isinstance(data, dict):
            return pd.DataFrame(data)
        elif isinstance(data, list):
            return pd.DataFrame(data)
        else:
            raise ValueError(f"Cannot convert {type(data)} to DataFrame")

    def series_to_json(series: pd.Series) -> Any:
        """Convert Series to JSON-compatible format."""
        return series.tolist()

    def series_from_json(data: Any) -> pd.Series:
        """Convert JSON data to Series."""
        return pd.Series(data)

    # Register Pandas types
    register_type(
        pd.DataFrame,
        to_json=dataframe_to_json,
        from_json=dataframe_from_json,
    )

    register_type(
        pd.Series,
        to_json=series_to_json,
        from_json=series_from_json,
    )

except ImportError:
    # Pandas not available
    pass


# Decorator for easy registration
def register_json_type(
    cls: Optional[Type[T]] = None,
    *,
    to_json: Optional[Callable[[T], Any]] = None,
    from_json: Optional[Callable[[Any], T]] = None,
):
    """
    Decorator to register a custom type.

    Can be used as:
    1. Class decorator (auto-detect to_dict/from_dict methods)
    2. With explicit serializers

    Examples:
        >>> @register_json_type
        ... class Point:
        ...     def __init__(self, x, y):
        ...         self.x = x
        ...         self.y = y
        ...     def to_dict(self):
        ...         return {'x': self.x, 'y': self.y}
        ...     @classmethod
        ...     def from_dict(cls, data):
        ...         return cls(data['x'], data['y'])

        >>> @register_json_type(
        ...     to_json=lambda p: [p.x, p.y],
        ...     from_json=lambda data: Point(data[0], data[1])
        ... )
        ... class Point:
        ...     def __init__(self, x, y):
        ...         self.x = x
        ...         self.y = y
    """

    def decorator(cls_to_register: Type[T]) -> Type[T]:
        # Determine serializers
        _to_json = to_json
        _from_json = from_json

        # Auto-detect serialization methods if not provided
        if _to_json is None:
            if hasattr(cls_to_register, 'to_dict'):
                _to_json = lambda obj: obj.to_dict()
            elif hasattr(cls_to_register, '__dict__'):
                _to_json = lambda obj: obj.__dict__
            else:
                raise ValueError(f"Cannot auto-detect serialization for {cls_to_register}")

        if _from_json is None:
            if hasattr(cls_to_register, 'from_dict'):
                _from_json = cls_to_register.from_dict
            elif hasattr(cls_to_register, '__init__'):
                # Try to call constructor with dict unpacking
                _from_json = lambda data: cls_to_register(**data)
            else:
                raise ValueError(f"Cannot auto-detect deserialization for {cls_to_register}")

        # Register the type
        register_type(
            cls_to_register,
            to_json=_to_json,
            from_json=_from_json,
        )

        return cls_to_register

    # Support both @register_json_type and @register_json_type(...)
    if cls is not None:
        # Called as @register_json_type (no parens) - cls is the class being decorated
        return decorator(cls)
    else:
        # Called as @register_json_type(...) (with keyword params)
        # Return the decorator to be applied
        return decorator
