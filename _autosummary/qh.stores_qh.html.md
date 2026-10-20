# qh.stores_qh

FastAPI service for operating on stores objects.

This module provides a RESTful API for interacting with mall objects,
which are Mappings of MutableMappings (dict of dicts).

### Functions

| [`add_mall_access`](#qh.stores_qh.add_mall_access)(get_mall[, app, write, ...])     | Add mall/store access endpoints to a FastAPI application.   |
|---------------------------------------------------------------------------------------------------|-------------------------------------------------------------|
| [`add_store_access`](#qh.stores_qh.add_store_access)(get_obj[, app, methods, ...])   | Add store access endpoints to a FastAPI application.        |
| [`create_method_endpoint`](#qh.stores_qh.create_method_endpoint)(method_name, config, ...) | Create an endpoint function for a specific mapping method.  |

### Classes

| [`StoreValue`](#qh.stores_qh.StoreValue)(\*, value)   | Request body for setting store values.   |
|--------------------------------------------------------------------------|------------------------------------------|

### *class* qh.stores_qh.StoreValue(, value)

Bases: `BaseModel`

Request body for setting store values.

#### model_config *: [ClassVar](https://docs.python.org/3/library/typing.html#typing.ClassVar)[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [`ConfigDict`][pydantic.config.ConfigDict].

### qh.stores_qh.add_mall_access(get_mall, app=None, , write=False, delete=False, caller=None, expose_errors=False)

Add mall/store access endpoints to a FastAPI application.

Routes live under `/users/{user_id}/mall`, so without an access check any
client can address any user’s mall. `caller` is that check.

* **Parameters:**
  * **get_mall** ([`Callable`](https://docs.python.org/3/library/typing.html#typing.Callable)[[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)], [`Mapping`](https://docs.python.org/3/library/typing.html#typing.Mapping)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`MutableMapping`](https://docs.python.org/3/library/typing.html#typing.MutableMapping)]]) – Function that takes a `user_id` and returns that user’s mall
    (a mapping of store keys to stores).
  * **app** – `None`, a `FastAPI` instance, a title string, or a dict of
    `FastAPI` kwargs (as in `add_store_access`).
  * **write** ([`bool`](https://docs.python.org/3/builtins/functions.html#bool)) – If True, add a `PUT` route to set store items.
  * **delete** ([`bool`](https://docs.python.org/3/builtins/functions.html#bool)) – If True, add a `DELETE` route to delete store items.
  * **caller** ([`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`Callable`](https://docs.python.org/3/library/typing.html#typing.Callable)[[`Request`], [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)]]) – `caller(request) -> user id` (sync or async) identifying the
    authenticated client, e.g. from a session or a verified token. When
    given, every route checks that it equals the `user_id` in the URL
    before the mall is looked up: an unknown caller (`None`, `""` or
    a bool) gets 401, a different user 403. To reject a request with
    another status (e.g. a bad token), raise `HTTPException` from
    `caller`; any other exception becomes a 500. A sync `caller`
    runs in a thread pool, so it may block. The comparison is exact, so
    `get_mall` should not normalise ids (case, whitespace) that
    `caller` returns un-normalised. When `None` (the default),
    no check is made, which is only appropriate when every client may
    read (and, with `write`/`delete`, change) every user’s mall.
  * **expose_errors** ([`bool`](https://docs.python.org/3/builtins/functions.html#bool)) – If True, exceptions raised by `get_mall` or by a store
    operation are sent to the client as text (see `add_store_access`).
* **Return type:**
  `FastAPI`

```pycon
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
```

### qh.stores_qh.add_store_access(get_obj, app=None, , methods=None, get_obj_dispatch=None, base_path='/users/{user_id}/mall/{store_key}', dependencies=None, expose_errors=False)

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
  * **dependencies** ([`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)]) – FastAPI dependencies (e.g. `[Depends(check_caller)]`)
    added to every route this function registers; the place for an
    authentication or authorization check.
  * **expose_errors** ([`bool`](https://docs.python.org/3/builtins/functions.html#bool)) – If True, exceptions raised by `get_obj` or by a store
    operation are sent to the client as text. By default the client
    gets `get_obj_dispatch['error_message']` (which only echoes the
    path parameters) or a generic message with an error id, and the
    exception is logged server-side (see `qh.errors`).
* **Return type:**
  `FastAPI`
* **Returns:**
  FastAPI application instance with store endpoints added

### qh.stores_qh.create_method_endpoint(method_name, config, get_obj_fn, path_params=None, , expose_errors=False, base_path='')

Create an endpoint function for a specific mapping method.

* **Parameters:**
  * **method_name** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – The mapping method to dispatch (e.g., ‘_\_iter_\_’, ‘_\_getitem_\_’)
  * **config** ([`Dict`](https://docs.python.org/3/library/typing.html#typing.Dict)) – Configuration for the endpoint
  * **get_obj_fn** ([`Callable`](https://docs.python.org/3/library/typing.html#typing.Callable)) – Function to retrieve the object to operate on
  * **path_params** ([`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`List`](https://docs.python.org/3/library/typing.html#typing.List)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]]) – List of path parameter names (e.g., [‘user_id’, ‘store_key’])
  * **expose_errors** ([`bool`](https://docs.python.org/3/builtins/functions.html#bool)) – If True, a failing store operation sends its exception
    text to the client; by default the client gets a generic message
    with an error id (see `qh.errors`).
  * **base_path** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – The route the method’s `config['path']` is appended to; only
    read by the generic branch, to tell whether `item_key` is already a
    path parameter.
* **Returns:**
  An async endpoint function compatible with FastAPI
* **Raises:**
  [**ValueError**](https://docs.python.org/3/builtins/exceptions.html#ValueError) – If `path_params` has a length this method’s branch does
      not implement (currently 1 or 2 are supported).
