# qh.app

Build a FastAPI application from plain Python functions.

`mk_app` is the primary entry point of qh: it normalizes whatever you pass
(a callable, a list, or a dict of callables to route configs), resolves the
layered configuration from `qh.config`, applies the naming conventions from
`qh.conventions` when asked, wraps each function into a FastAPI endpoint via
`qh.endpoint`, and installs the type-hint-derived OpenAPI document from
`qh.openapi`. Functions named in `async_funcs` also get the task endpoints
of `qh.async_endpoints`.

Main entry points:

- `mk_app`: functions in, FastAPI app out
- `inspect_routes`: the registered routes as plain dicts
- `print_routes`: the same as a text table

```pycon
>>> from qh.app import mk_app, inspect_routes
>>> def add(x: int, y: int) -> int:
...     return x + y
>>> app = mk_app([add])
>>> [r['path'] for r in inspect_routes(app) if r['name'] == 'add']
['/add']
```

### Functions

| [`create_app`](#qh.app.create_app)(funcs, \*[, app, config, ...])   | Create a FastAPI application whose routes call the given Python functions.   |
|----------------------------------------------------------------------------------------------|------------------------------------------------------------------------------|
| [`inspect_routes`](#qh.app.inspect_routes)(app)                         | List the routes of a FastAPI app as plain dicts.                             |
| [`make_app`](#qh.app.make_app)(funcs, \*[, app, config, ...])     | Create a FastAPI application whose routes call the given Python functions.   |
| [`mk_app`](#qh.app.mk_app)(funcs, \*[, app, config, ...])       | Create a FastAPI application whose routes call the given Python functions.   |
| [`print_routes`](#qh.app.print_routes)(app)                           | Print a text table of a FastAPI app's routes (methods, path, endpoint name). |

### qh.app.create_app(funcs, , app=None, config=None, use_conventions=False, async_funcs=None, async_config=None, enhanced_openapi=True, \*\*kwargs)

Create a FastAPI application whose routes call the given Python functions.

This is the primary API for qh. It supports multiple input formats for maximum
flexibility while maintaining simplicity for common cases. Each function gets
one route; by default a `POST` at `/<function name>` taking its arguments
as a JSON object (see `RouteConfig` and `AppConfig` in `qh.config` for
what can be changed, and `qh.rules` for how parameters are mapped to HTTP).

* **Parameters:**
  * **funcs** (`Union`[[`Callable`](https://docs.python.org/3/library/typing.html#typing.Callable), [`List`](https://docs.python.org/3/library/typing.html#typing.List)[[`Callable`](https://docs.python.org/3/library/typing.html#typing.Callable)], [`Dict`](https://docs.python.org/3/library/typing.html#typing.Dict)[[`Callable`](https://docs.python.org/3/library/typing.html#typing.Callable), `Union`[[`Dict`](https://docs.python.org/3/library/typing.html#typing.Dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)], [`RouteConfig`](qh.config.html.md#qh.config.RouteConfig)]]]) – 

    Functions to expose as HTTP endpoints. Can be:
    - A single callable
    - A list of callables
    - A dict mapping callables to their route configurations
  * **app** ([`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[`FastAPI`]) – Optional existing FastAPI app to add routes to.
    If None, creates a new app.
  * **config** (`Union`[[`Dict`](https://docs.python.org/3/library/typing.html#typing.Dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)], [`AppConfig`](qh.config.html.md#qh.config.AppConfig), [`None`](https://docs.python.org/3/builtins/constants.html#None)]) – 

    Optional app-level configuration. Can be:
    - AppConfig object
    - Dict that will be converted to AppConfig
    - None (uses defaults)
  * **use_conventions** ([`bool`](https://docs.python.org/3/builtins/functions.html#bool)) – 

    Whether to use convention-based routing.
    If True, infers paths and methods from function names:
    - get_user(user_id) → GET /users/{user_id}
    - list_users() → GET /users
    - create_user(user) → POST /users
  * **async_funcs** ([`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`List`](https://docs.python.org/3/library/typing.html#typing.List)[`Union`[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Callable`](https://docs.python.org/3/library/typing.html#typing.Callable)]]]) – List of functions (by name or reference) that should support
    async task execution. When enabled, clients can add ?async=true to
    get a task ID instead of blocking for the result.
  * **async_config** (`Union`[[`Dict`](https://docs.python.org/3/library/typing.html#typing.Dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)], [`TaskConfig`](qh.async_tasks.html.md#qh.async_tasks.TaskConfig), [`None`](https://docs.python.org/3/builtins/constants.html#None)]) – 

    Configuration for async task processing. Can be:
    - None (uses default TaskConfig for functions in async_funcs)
    - TaskConfig object (applies to all async_funcs)
    - Dict mapping function names to TaskConfig objects
  * **enhanced_openapi** ([`bool`](https://docs.python.org/3/builtins/functions.html#bool)) – Whether to serve an enhanced OpenAPI document at
    `/openapi.json` — one with `requestBody` / `responses` /
    `components.schemas` derived from each function’s Python type
    hints (see [`qh.openapi`](qh.openapi.html.md#module-qh.openapi)). Defaults to True; the enhancement is
    additive and falls back to FastAPI’s plain schema if it ever fails.
  * **\*\*kwargs** – Additional FastAPI() constructor kwargs (if creating new app)
* **Return type:**
  `FastAPI`
* **Returns:**
  The FastAPI application (the one passed as `app`, or a new one) with
  one route per function, in the order the functions were given.
* **Raises:**
  * [**TypeError**](https://docs.python.org/3/builtins/exceptions.html#TypeError) – If `config` is neither `None`, an `AppConfig`, nor a dict.
  * [**ValueError**](https://docs.python.org/3/builtins/exceptions.html#ValueError) – If a per-function route config is invalid for that function
        (see `qh.endpoint.validate_route_config`), e.g. a `path` whose
        `{param}` placeholders don’t match the function’s parameters.

#### SEE ALSO
`qh.testing.test_app`: call the resulting app in-process without a server.
`qh.client.mk_client_from_app`: a Python client whose methods mirror the functions.
`qh.base.mk_fastapi_app`: the older, config-free variant kept for its tests.

### Examples

Simple case - just functions:

```pycon
>>> def add(x: int, y: int) -> int:
...     return x + y
>>> app = mk_app([add])
```

With conventions:

```pycon
>>> def get_user(user_id: str): ...
>>> def list_users(): ...
>>> app = mk_app([get_user, list_users], use_conventions=True)
```

With configuration:

```pycon
>>> app = mk_app(
...     [add],
...     config={'path_prefix': '/api', 'default_methods': ['POST']}
... )
```

Per-function configuration:

```pycon
>>> app = mk_app({
...     add: {'methods': ['GET', 'POST'], 'path': '/calculate/add'},
... })
```

With async support:

```pycon
>>> def expensive_task(n: int) -> int:
...     import time
...     time.sleep(5)
...     return n * 2
>>> app = mk_app([expensive_task], async_funcs=['expensive_task'])
```

Now `POST /expensive_task?async=true` returns `{"task_id": ...}` and
`GET /tasks/{task_id}/result` returns the result when ready.

### qh.app.inspect_routes(app)

List the routes of a FastAPI app as plain dicts.

* **Parameters:**
  **app** (`FastAPI`) – FastAPI application
* **Return type:**
  [`List`](https://docs.python.org/3/library/typing.html#typing.List)[[`Dict`](https://docs.python.org/3/library/typing.html#typing.Dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)]]
* **Returns:**
  One dict per route that has HTTP methods (FastAPI’s own `/docs`,
  `/redoc` and `/openapi.json` routes included), in registration
  order, with keys `path`, `methods`, `name` and `endpoint`.
  Routes made by `mk_app` also carry `function` (the original
  Python callable) and `param_specs` (the parameter-to-`TransformSpec`
  map used to build the OpenAPI document).

### Examples

```pycon
>>> from qh import mk_app, inspect_routes
>>> def add(x: int, y: int) -> int:
...     return x + y
>>> app = mk_app([add])
>>> route = [r for r in inspect_routes(app) if r['name'] == 'add'][0]
>>> route['path'], route['methods'], route['function'] is add
('/add', ['POST'], True)
```

### qh.app.make_app(funcs, , app=None, config=None, use_conventions=False, async_funcs=None, async_config=None, enhanced_openapi=True, \*\*kwargs)

Create a FastAPI application whose routes call the given Python functions.

This is the primary API for qh. It supports multiple input formats for maximum
flexibility while maintaining simplicity for common cases. Each function gets
one route; by default a `POST` at `/<function name>` taking its arguments
as a JSON object (see `RouteConfig` and `AppConfig` in `qh.config` for
what can be changed, and `qh.rules` for how parameters are mapped to HTTP).

* **Parameters:**
  * **funcs** (`Union`[[`Callable`](https://docs.python.org/3/library/typing.html#typing.Callable), [`List`](https://docs.python.org/3/library/typing.html#typing.List)[[`Callable`](https://docs.python.org/3/library/typing.html#typing.Callable)], [`Dict`](https://docs.python.org/3/library/typing.html#typing.Dict)[[`Callable`](https://docs.python.org/3/library/typing.html#typing.Callable), `Union`[[`Dict`](https://docs.python.org/3/library/typing.html#typing.Dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)], [`RouteConfig`](qh.config.html.md#qh.config.RouteConfig)]]]) – 

    Functions to expose as HTTP endpoints. Can be:
    - A single callable
    - A list of callables
    - A dict mapping callables to their route configurations
  * **app** ([`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[`FastAPI`]) – Optional existing FastAPI app to add routes to.
    If None, creates a new app.
  * **config** (`Union`[[`Dict`](https://docs.python.org/3/library/typing.html#typing.Dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)], [`AppConfig`](qh.config.html.md#qh.config.AppConfig), [`None`](https://docs.python.org/3/builtins/constants.html#None)]) – 

    Optional app-level configuration. Can be:
    - AppConfig object
    - Dict that will be converted to AppConfig
    - None (uses defaults)
  * **use_conventions** ([`bool`](https://docs.python.org/3/builtins/functions.html#bool)) – 

    Whether to use convention-based routing.
    If True, infers paths and methods from function names:
    - get_user(user_id) → GET /users/{user_id}
    - list_users() → GET /users
    - create_user(user) → POST /users
  * **async_funcs** ([`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`List`](https://docs.python.org/3/library/typing.html#typing.List)[`Union`[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Callable`](https://docs.python.org/3/library/typing.html#typing.Callable)]]]) – List of functions (by name or reference) that should support
    async task execution. When enabled, clients can add ?async=true to
    get a task ID instead of blocking for the result.
  * **async_config** (`Union`[[`Dict`](https://docs.python.org/3/library/typing.html#typing.Dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)], [`TaskConfig`](qh.async_tasks.html.md#qh.async_tasks.TaskConfig), [`None`](https://docs.python.org/3/builtins/constants.html#None)]) – 

    Configuration for async task processing. Can be:
    - None (uses default TaskConfig for functions in async_funcs)
    - TaskConfig object (applies to all async_funcs)
    - Dict mapping function names to TaskConfig objects
  * **enhanced_openapi** ([`bool`](https://docs.python.org/3/builtins/functions.html#bool)) – Whether to serve an enhanced OpenAPI document at
    `/openapi.json` — one with `requestBody` / `responses` /
    `components.schemas` derived from each function’s Python type
    hints (see [`qh.openapi`](qh.openapi.html.md#module-qh.openapi)). Defaults to True; the enhancement is
    additive and falls back to FastAPI’s plain schema if it ever fails.
  * **\*\*kwargs** – Additional FastAPI() constructor kwargs (if creating new app)
* **Return type:**
  `FastAPI`
* **Returns:**
  The FastAPI application (the one passed as `app`, or a new one) with
  one route per function, in the order the functions were given.
* **Raises:**
  * [**TypeError**](https://docs.python.org/3/builtins/exceptions.html#TypeError) – If `config` is neither `None`, an `AppConfig`, nor a dict.
  * [**ValueError**](https://docs.python.org/3/builtins/exceptions.html#ValueError) – If a per-function route config is invalid for that function
        (see `qh.endpoint.validate_route_config`), e.g. a `path` whose
        `{param}` placeholders don’t match the function’s parameters.

#### SEE ALSO
`qh.testing.test_app`: call the resulting app in-process without a server.
`qh.client.mk_client_from_app`: a Python client whose methods mirror the functions.
`qh.base.mk_fastapi_app`: the older, config-free variant kept for its tests.

### Examples

Simple case - just functions:

```pycon
>>> def add(x: int, y: int) -> int:
...     return x + y
>>> app = mk_app([add])
```

With conventions:

```pycon
>>> def get_user(user_id: str): ...
>>> def list_users(): ...
>>> app = mk_app([get_user, list_users], use_conventions=True)
```

With configuration:

```pycon
>>> app = mk_app(
...     [add],
...     config={'path_prefix': '/api', 'default_methods': ['POST']}
... )
```

Per-function configuration:

```pycon
>>> app = mk_app({
...     add: {'methods': ['GET', 'POST'], 'path': '/calculate/add'},
... })
```

With async support:

```pycon
>>> def expensive_task(n: int) -> int:
...     import time
...     time.sleep(5)
...     return n * 2
>>> app = mk_app([expensive_task], async_funcs=['expensive_task'])
```

Now `POST /expensive_task?async=true` returns `{"task_id": ...}` and
`GET /tasks/{task_id}/result` returns the result when ready.

### qh.app.mk_app(funcs, , app=None, config=None, use_conventions=False, async_funcs=None, async_config=None, enhanced_openapi=True, \*\*kwargs)

Create a FastAPI application whose routes call the given Python functions.

This is the primary API for qh. It supports multiple input formats for maximum
flexibility while maintaining simplicity for common cases. Each function gets
one route; by default a `POST` at `/<function name>` taking its arguments
as a JSON object (see `RouteConfig` and `AppConfig` in `qh.config` for
what can be changed, and `qh.rules` for how parameters are mapped to HTTP).

* **Parameters:**
  * **funcs** (`Union`[[`Callable`](https://docs.python.org/3/library/typing.html#typing.Callable), [`List`](https://docs.python.org/3/library/typing.html#typing.List)[[`Callable`](https://docs.python.org/3/library/typing.html#typing.Callable)], [`Dict`](https://docs.python.org/3/library/typing.html#typing.Dict)[[`Callable`](https://docs.python.org/3/library/typing.html#typing.Callable), `Union`[[`Dict`](https://docs.python.org/3/library/typing.html#typing.Dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)], [`RouteConfig`](qh.config.html.md#qh.config.RouteConfig)]]]) – 

    Functions to expose as HTTP endpoints. Can be:
    - A single callable
    - A list of callables
    - A dict mapping callables to their route configurations
  * **app** ([`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[`FastAPI`]) – Optional existing FastAPI app to add routes to.
    If None, creates a new app.
  * **config** (`Union`[[`Dict`](https://docs.python.org/3/library/typing.html#typing.Dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)], [`AppConfig`](qh.config.html.md#qh.config.AppConfig), [`None`](https://docs.python.org/3/builtins/constants.html#None)]) – 

    Optional app-level configuration. Can be:
    - AppConfig object
    - Dict that will be converted to AppConfig
    - None (uses defaults)
  * **use_conventions** ([`bool`](https://docs.python.org/3/builtins/functions.html#bool)) – 

    Whether to use convention-based routing.
    If True, infers paths and methods from function names:
    - get_user(user_id) → GET /users/{user_id}
    - list_users() → GET /users
    - create_user(user) → POST /users
  * **async_funcs** ([`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`List`](https://docs.python.org/3/library/typing.html#typing.List)[`Union`[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Callable`](https://docs.python.org/3/library/typing.html#typing.Callable)]]]) – List of functions (by name or reference) that should support
    async task execution. When enabled, clients can add ?async=true to
    get a task ID instead of blocking for the result.
  * **async_config** (`Union`[[`Dict`](https://docs.python.org/3/library/typing.html#typing.Dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)], [`TaskConfig`](qh.async_tasks.html.md#qh.async_tasks.TaskConfig), [`None`](https://docs.python.org/3/builtins/constants.html#None)]) – 

    Configuration for async task processing. Can be:
    - None (uses default TaskConfig for functions in async_funcs)
    - TaskConfig object (applies to all async_funcs)
    - Dict mapping function names to TaskConfig objects
  * **enhanced_openapi** ([`bool`](https://docs.python.org/3/builtins/functions.html#bool)) – Whether to serve an enhanced OpenAPI document at
    `/openapi.json` — one with `requestBody` / `responses` /
    `components.schemas` derived from each function’s Python type
    hints (see [`qh.openapi`](qh.openapi.html.md#module-qh.openapi)). Defaults to True; the enhancement is
    additive and falls back to FastAPI’s plain schema if it ever fails.
  * **\*\*kwargs** – Additional FastAPI() constructor kwargs (if creating new app)
* **Return type:**
  `FastAPI`
* **Returns:**
  The FastAPI application (the one passed as `app`, or a new one) with
  one route per function, in the order the functions were given.
* **Raises:**
  * [**TypeError**](https://docs.python.org/3/builtins/exceptions.html#TypeError) – If `config` is neither `None`, an `AppConfig`, nor a dict.
  * [**ValueError**](https://docs.python.org/3/builtins/exceptions.html#ValueError) – If a per-function route config is invalid for that function
        (see `qh.endpoint.validate_route_config`), e.g. a `path` whose
        `{param}` placeholders don’t match the function’s parameters.

#### SEE ALSO
`qh.testing.test_app`: call the resulting app in-process without a server.
`qh.client.mk_client_from_app`: a Python client whose methods mirror the functions.
`qh.base.mk_fastapi_app`: the older, config-free variant kept for its tests.

### Examples

Simple case - just functions:

```pycon
>>> def add(x: int, y: int) -> int:
...     return x + y
>>> app = mk_app([add])
```

With conventions:

```pycon
>>> def get_user(user_id: str): ...
>>> def list_users(): ...
>>> app = mk_app([get_user, list_users], use_conventions=True)
```

With configuration:

```pycon
>>> app = mk_app(
...     [add],
...     config={'path_prefix': '/api', 'default_methods': ['POST']}
... )
```

Per-function configuration:

```pycon
>>> app = mk_app({
...     add: {'methods': ['GET', 'POST'], 'path': '/calculate/add'},
... })
```

With async support:

```pycon
>>> def expensive_task(n: int) -> int:
...     import time
...     time.sleep(5)
...     return n * 2
>>> app = mk_app([expensive_task], async_funcs=['expensive_task'])
```

Now `POST /expensive_task?async=true` returns `{"task_id": ...}` and
`GET /tasks/{task_id}/result` returns the result when ready.

### qh.app.print_routes(app)

Print a text table of a FastAPI app’s routes (methods, path, endpoint name).

* **Parameters:**
  **app** (`FastAPI`) – FastAPI application
* **Return type:**
  [`None`](https://docs.python.org/3/builtins/constants.html#None)

### Examples

```pycon
>>> from qh import mk_app, print_routes
>>> def add(x: int, y: int) -> int:
...     return x + y
>>> print_routes(mk_app([add], config={'docs_url': None, 'redoc_url': None, 'openapi_url': None}))
METHODS  PATH  ENDPOINT
----------------------------------------------------------
POST  /add  add
```
