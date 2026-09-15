# qh.types

Type registry for qh - automatic serialization/deserialization for custom types.

Supports:

- NumPy arrays and dtypes
- Pandas DataFrames and Series
- Custom user types
- Pydantic models

The type registry maps Python types to HTTP representations and provides
automatic conversion functions (ingress/egress transformations).

### Functions

| [`get_transform_spec_for_type`](#qh.types.get_transform_spec_for_type)(python_type)           | Get TransformSpec for a type from global registry.   |
|-----------------------------------------------------------------------------------------------------|------------------------------------------------------|
| [`get_type_handler`](#qh.types.get_type_handler)(python_type)                      | Get handler for a type from global registry.         |
| [`register_json_type`](#qh.types.register_json_type)([cls, to_json, from_json])      | Decorator to register a custom type.                 |
| [`register_type`](#qh.types.register_type)(python_type, \*, to_json, from_json) | Register a type in the global registry.              |

### Classes

| [`TypeHandler`](#qh.types.TypeHandler)(python_type, to_json, from_json)   | Handler for serializing/deserializing a specific type.   |
|-------------------------------------------------------------------------------------------------|----------------------------------------------------------|
| [`TypeRegistry`](#qh.types.TypeRegistry)()                                 | Registry for type handlers.                              |

### *class* qh.types.TypeHandler(python_type, to_json, from_json, http_location=HttpLocation.JSON_BODY, content_type=None)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

Handler for serializing/deserializing a specific type.

#### python_type

The Python type this handler manages

#### to_json

Function to serialize Python object to JSON-compatible format

#### from_json

Function to deserialize JSON to Python object

#### http_location

Where in HTTP request/response this appears

#### content_type

Optional HTTP content type for binary data

#### to_transform_spec()

Convert this handler to a TransformSpec.

* **Return type:**
  [`TransformSpec`](qh.rules.html.md#qh.rules.TransformSpec)

### *class* qh.types.TypeRegistry

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

Registry for type handlers.

Manages conversion between Python types and HTTP representations.
Comes pre-populated with pass-through handlers for the JSON-native
builtins (`str`, `int`, `float`, `bool`, `list`, `dict`,
`NoneType`); its `register` method adds more. The module-level
`register_type` (and the `register_json_type` decorator built on it)
register into the separate, global registry used by the rest of `qh`,
not into a particular `TypeRegistry` instance.

```pycon
>>> reg = TypeRegistry()
>>> reg.get_handler(int).to_json(3)
3
>>> reg.get_handler(str) is not None
True
>>> class Unregistered: pass
>>> reg.get_handler(Unregistered) is None
True
```

#### get_handler(python_type)

Get handler for a type.

* **Parameters:**
  **python_type** ([`Type`](https://docs.python.org/3/library/typing.html#typing.Type)) – The type to look up
* **Return type:**
  [`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`TypeHandler`](#qh.types.TypeHandler)]
* **Returns:**
  TypeHandler if registered, None otherwise

#### get_transform_spec(python_type)

Get TransformSpec for a type.

* **Return type:**
  [`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`TransformSpec`](qh.rules.html.md#qh.rules.TransformSpec)]

#### register(python_type, , to_json, from_json, http_location=HttpLocation.JSON_BODY, content_type=None)

Register a type handler.

* **Parameters:**
  * **python_type** ([`Type`](https://docs.python.org/3/library/typing.html#typing.Type)[[`TypeVar`](https://docs.python.org/3/library/typing.html#typing.TypeVar)(`T`)]) – The Python type
  * **to_json** ([`Callable`](https://docs.python.org/3/library/typing.html#typing.Callable)[[[`TypeVar`](https://docs.python.org/3/library/typing.html#typing.TypeVar)(`T`)], [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)]) – Function to serialize to JSON-compatible format
  * **from_json** ([`Callable`](https://docs.python.org/3/library/typing.html#typing.Callable)[[[`Any`](https://docs.python.org/3/library/typing.html#typing.Any)], [`TypeVar`](https://docs.python.org/3/library/typing.html#typing.TypeVar)(`T`)]) – Function to deserialize from JSON
  * **http_location** ([`HttpLocation`](qh.rules.html.md#qh.rules.HttpLocation)) – Where this appears in HTTP
  * **content_type** ([`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]) – Optional content type for binary data
* **Return type:**
  [`None`](https://docs.python.org/3/builtins/constants.html#None)

#### unregister(python_type)

Unregister a type handler.

* **Return type:**
  [`None`](https://docs.python.org/3/builtins/constants.html#None)

### qh.types.get_transform_spec_for_type(python_type)

Get TransformSpec for a type from global registry.

* **Return type:**
  [`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`TransformSpec`](qh.rules.html.md#qh.rules.TransformSpec)]

### qh.types.get_type_handler(python_type)

Get handler for a type from global registry.

* **Return type:**
  [`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`TypeHandler`](#qh.types.TypeHandler)]

### qh.types.register_json_type(cls=None, , to_json=None, from_json=None)

Decorator to register a custom type.

Can be used as:

1. Class decorator (auto-detect to_dict/from_dict methods)
2. With explicit serializers

* **Parameters:**
  * **cls** ([`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`Type`](https://docs.python.org/3/library/typing.html#typing.Type)[[`TypeVar`](https://docs.python.org/3/library/typing.html#typing.TypeVar)(`T`)]]) – The class being decorated, when used as `@register_json_type`
    with no arguments; `None` when called as
    `@register_json_type(to_json=..., from_json=...)`.
  * **to_json** ([`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`Callable`](https://docs.python.org/3/library/typing.html#typing.Callable)[[[`TypeVar`](https://docs.python.org/3/library/typing.html#typing.TypeVar)(`T`)], [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)]]) – Serializer; when omitted, falls back to `cls.to_dict()`,
    then `obj.__dict__`.
  * **from_json** ([`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`Callable`](https://docs.python.org/3/library/typing.html#typing.Callable)[[[`Any`](https://docs.python.org/3/library/typing.html#typing.Any)], [`TypeVar`](https://docs.python.org/3/library/typing.html#typing.TypeVar)(`T`)]]) – Deserializer; when omitted, falls back to
    `cls.from_dict`, then `cls(**data)`.

### Examples

```pycon
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
```

```pycon
>>> @register_json_type(
...     to_json=lambda p: [p.x, p.y],
...     from_json=lambda data: Point(data[0], data[1])
... )
... class Point:
...     def __init__(self, x, y):
...         self.x = x
...         self.y = y
```

### qh.types.register_type(python_type, , to_json, from_json, http_location=HttpLocation.JSON_BODY, content_type=None)

Register a type in the global registry.

* **Parameters:**
  * **python_type** ([`Type`](https://docs.python.org/3/library/typing.html#typing.Type)[[`TypeVar`](https://docs.python.org/3/library/typing.html#typing.TypeVar)(`T`)]) – The Python type
  * **to_json** ([`Callable`](https://docs.python.org/3/library/typing.html#typing.Callable)[[[`TypeVar`](https://docs.python.org/3/library/typing.html#typing.TypeVar)(`T`)], [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)]) – Function to serialize to JSON-compatible format
  * **from_json** ([`Callable`](https://docs.python.org/3/library/typing.html#typing.Callable)[[[`Any`](https://docs.python.org/3/library/typing.html#typing.Any)], [`TypeVar`](https://docs.python.org/3/library/typing.html#typing.TypeVar)(`T`)]) – Function to deserialize from JSON
  * **http_location** ([`HttpLocation`](qh.rules.html.md#qh.rules.HttpLocation)) – Where this appears in HTTP
  * **content_type** ([`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]) – Optional content type for binary data
* **Return type:**
  [`None`](https://docs.python.org/3/builtins/constants.html#None)

### Example

```pycon
>>> import numpy as np
>>> register_type(
...     np.ndarray,
...     to_json=lambda arr: arr.tolist(),
...     from_json=lambda lst: np.array(lst)
... )
```
