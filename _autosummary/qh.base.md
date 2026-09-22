# qh.base

Config-free dispatch of Python callables as FastAPI routes, plus a store dispatcher.

A lighter predecessor of `qh.app.mk_app` with a dict-based route config
(`path`, `methods`, `input_trans`, `output_trans`, `defaults`,
`summary`, `tags`). Every endpoint reads its arguments from the JSON body
merged with path parameters, and answers `422` for a missing required
argument and `500` for an exception raised by the function. Importing this
module also patches `fastapi.testclient.TestClient.get` to accept a `json`
body. Not used by `qh.app`; kept for its tests and for `mk_store_dispatcher`.

Main entry points:

- `mk_fastapi_app`: callables (or a dict of callable to config) in, FastAPI app out
- `mk_store_dispatcher`: key/value routes over a `store_getter(store_id)` mapping
- `mk_json_ingress` / `mk_json_egress`: per-key and per-type transforms for the above

### Functions

| [`mk_fastapi_app`](#qh.base.mk_fastapi_app)(funcs, \*[, app, path_prefix, ...])   | Expose Python callables as FastAPI routes.                                               |
|-------------------------------------------------------------------------------------------------------|------------------------------------------------------------------------------------------|
| [`mk_json_egress`](#qh.base.mk_json_egress)(transform_map)                        | Create an output transformer that applies functions based on the return type.            |
| [`mk_json_ingress`](#qh.base.mk_json_ingress)(transform_map)                       | Create an input transformer that applies functions to specific keys in the request JSON. |
| [`mk_store_dispatcher`](#qh.base.mk_store_dispatcher)(store_getter, \*[, ...])         | Create store dispatcher routes using mk_fastapi_app.                                     |
| [`name_based_ingress`](#qh.base.name_based_ingress)(\*\*kw)                           | Alias for mk_json_ingress with named transforms.                                         |

### qh.base.mk_fastapi_app(funcs, , app=None, path_prefix='', default_methods=None, path_template='/{func_name}')

Expose Python callables as FastAPI routes.

funcs can be:

> - dict mapping func -> RouteConfig dict
> - list of callables or dicts with ‘func’ key
> - single callable

RouteConfig keys: path, methods, input_trans, output_trans, defaults, summary, tags

* **Return type:**
  `FastAPI`

### qh.base.mk_json_egress(transform_map)

Create an output transformer that applies functions based on the return type.

* **Return type:**
  [`Callable`](https://docs.python.org/3/library/collections.abc.html#collections.abc.Callable)[[[`Any`](https://docs.python.org/3/library/typing.html#typing.Any)], [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)]

### qh.base.mk_json_ingress(transform_map)

Create an input transformer that applies functions to specific keys in the request JSON.

* **Return type:**
  [`Callable`](https://docs.python.org/3/library/collections.abc.html#collections.abc.Callable)[[[`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)]], [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)]]

### qh.base.mk_store_dispatcher(store_getter, , path_prefix='/stores', \*\*config)

Create store dispatcher routes using mk_fastapi_app.

* **Return type:**
  `FastAPI`

### qh.base.name_based_ingress(\*\*kw)

Alias for mk_json_ingress with named transforms.

* **Return type:**
  [`Callable`](https://docs.python.org/3/library/collections.abc.html#collections.abc.Callable)[[[`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)]], [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)]]
