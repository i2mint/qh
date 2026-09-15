# qh.stores_qh

FastAPI service for operating on stores objects.

This module provides a RESTful API for interacting with mall objects,
which are Mappings of MutableMappings (dict of dicts).

### Functions

| [`add_mall_access`](#qh.stores_qh.add_mall_access)(get_mall[, app, write, delete])   | Add mall/store access endpoints to a FastAPI application.   |
|----------------------------------------------------------------------------------------------------|-------------------------------------------------------------|
| [`add_store_access`](#qh.stores_qh.add_store_access)(get_obj[, app, methods, ...])    | Add store access endpoints to a FastAPI application.        |
| [`create_method_endpoint`](#qh.stores_qh.create_method_endpoint)(method_name, config, ...)  | Create an endpoint function for a specific mapping method.  |

### Classes

| [`StoreValue`](#qh.stores_qh.StoreValue)(\*\*data)   | Request body for setting store values.   |
|-------------------------------------------------------------------------|------------------------------------------|

### *class* qh.stores_qh.StoreValue(\*\*data)

Bases: `BaseModel`

Request body for setting store values.

#### model_config *: [ClassVar](https://docs.python.org/3/library/typing.html#typing.ClassVar)[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [`ConfigDict`][pydantic.config.ConfigDict].

### qh.stores_qh.add_mall_access(get_mall, app=None, , write=False, delete=False)

Add mall/store access endpoints to a FastAPI application.

* **Return type:**
  `FastAPI`

### qh.stores_qh.add_store_access(get_obj, app=None, , methods=None, get_obj_dispatch=None, base_path='/users/{user_id}/mall/{store_key}')

Add store access endpoints to a FastAPI application.

* **Parameters:**
  * **get_obj** ([`Callable`](https://docs.python.org/3/library/typing.html#typing.Callable)[[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)], [`Mapping`](https://docs.python.org/3/library/typing.html#typing.Mapping)]) – Function that takes an identifier and returns a mapping object
  * **app** – 

    Can be:
    - None: creates a new FastAPI app with default settings
    - FastAPI instance: uses this existing app
    - str: creates a new FastAPI app with this title
    - dict: creates a new FastAPI app with these kwargs
  * **methods** ([`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`Dict`](https://docs.python.org/3/library/typing.html#typing.Dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`Dict`](https://docs.python.org/3/library/typing.html#typing.Dict)]]]) – 

    Dictionary mapping method names to dispatch configuration
    - Key is the mapping method name (e.g., ‘_\_iter_\_’, ‘_\_getitem_\_’)
    - Value is None to use defaults or a dict with configuration
  * **get_obj_dispatch** ([`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`Dict`](https://docs.python.org/3/library/typing.html#typing.Dict)]) – Configuration for how to dispatch the get_obj function
  * **base_path** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – Base path for all endpoints
* **Return type:**
  `FastAPI`
* **Returns:**
  FastAPI application instance with store endpoints added

### qh.stores_qh.create_method_endpoint(method_name, config, get_obj_fn, path_params=None)

Create an endpoint function for a specific mapping method.

* **Parameters:**
  * **method_name** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – The mapping method to dispatch (e.g., ‘_\_iter_\_’, ‘_\_getitem_\_’)
  * **config** ([`Dict`](https://docs.python.org/3/library/typing.html#typing.Dict)) – Configuration for the endpoint
  * **get_obj_fn** ([`Callable`](https://docs.python.org/3/library/typing.html#typing.Callable)) – Function to retrieve the object to operate on
  * **path_params** ([`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`List`](https://docs.python.org/3/library/typing.html#typing.List)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]]) – List of path parameter names (e.g., [‘user_id’, ‘store_key’])
* **Returns:**
  An async endpoint function compatible with FastAPI
* **Raises:**
  [**ValueError**](https://docs.python.org/3/builtins/exceptions.html#ValueError) – If `path_params` has a length this method’s branch does
      not implement (currently 1 or 2 are supported).
