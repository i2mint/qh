# qh.core

Minimal function-to-route dispatch built on `i2.wrapper.Wrap`.

An early, self-contained take on the qh idea: `mk_fastapi_app` turns a
collection of callables into `POST` routes that read a JSON body as keyword
arguments and return the JSON-encoded result. It is not used by `qh.app.mk_app`,
the maintained entry point, and it keeps a process-wide `default_configs`
dict that `mk_fastapi_app` mutates; prefer `qh.app` for new code.

Main entry points:

- `mk_fastapi_app`: callables in, FastAPI app out
- `default_configs`: the mutable process-wide defaults (path, method, mappers)

### Functions

| [`default_input_mapper`](#qh.core.default_input_mapper)(request)                   | Extract function arguments from request JSON body.       |
|--------------------------------------------------------------------------------------------------|----------------------------------------------------------|
| [`default_output_mapper`](#qh.core.default_output_mapper)(output)                   | Serialize function output to JSON response.              |
| [`get_config_for_func`](#qh.core.get_config_for_func)(func, default_configs, ...) | Merge default and per-function configurations.           |
| [`mk_fastapi_app`](#qh.core.mk_fastapi_app)(funcs[, configs, func_configs])  | Create a FastAPI app from a collection of functions.     |
| [`mk_wrapped_func`](#qh.core.mk_wrapped_func)(func, input_mapper, ...)        | Wrap a function with ingress and egress transformations. |

### *async* qh.core.default_input_mapper(request)

Extract function arguments from request JSON body.

* **Return type:**
  [`tuple`](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[`tuple`](https://docs.python.org/3/builtins/stdtypes.html#tuple), [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)]

### qh.core.default_output_mapper(output)

Serialize function output to JSON response.

* **Return type:**
  `Response`

### qh.core.get_config_for_func(func, default_configs, func_configs)

Merge default and per-function configurations.

* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)]

### qh.core.mk_fastapi_app(funcs, configs=None, func_configs=None)

Create a FastAPI app from a collection of functions.

* **Return type:**
  `FastAPI`

### qh.core.mk_wrapped_func(func, input_mapper, output_mapper)

Wrap a function with ingress and egress transformations.

* **Return type:**
  [`Callable`](https://docs.python.org/3/library/collections.abc.html#collections.abc.Callable)
