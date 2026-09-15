# qh.endpoint

Endpoint creation using i2.Wrap to transform functions into FastAPI routes.

This module bridges Python functions and HTTP endpoints via transformation rules.

### Functions

| [`apply_egress_transform`](#qh.endpoint.apply_egress_transform)(result, egress)        | Apply egress transformation to function result.                     |
|------------------------------------------------------------------------------------------------|---------------------------------------------------------------------|
| [`apply_ingress_transforms`](#qh.endpoint.apply_ingress_transforms)(params, param_specs) | Apply ingress transformations to extracted parameters.              |
| [`extract_http_params`](#qh.endpoint.extract_http_params)(request, param_specs)     | Extract parameters from HTTP request based on transformation specs. |
| [`make_endpoint`](#qh.endpoint.make_endpoint)(func, route_config)             | Create FastAPI endpoint from a function using i2.Wrap.              |
| [`validate_route_config`](#qh.endpoint.validate_route_config)(func, config)           | Validate that route configuration is compatible with function.      |

### qh.endpoint.apply_egress_transform(result, egress)

Apply egress transformation to function result.

* **Return type:**
  [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)

### qh.endpoint.apply_ingress_transforms(params, param_specs)

Apply ingress transformations to extracted parameters.

* **Return type:**
  [`Dict`](https://docs.python.org/3/library/typing.html#typing.Dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)]

### *async* qh.endpoint.extract_http_params(request, param_specs)

Extract parameters from HTTP request based on transformation specs.

* **Parameters:**
  * **request** (`Request`) – FastAPI Request object
  * **param_specs** ([`Dict`](https://docs.python.org/3/library/typing.html#typing.Dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`TransformSpec`](qh.rules.html.md#qh.rules.TransformSpec)]) – Mapping of param name to its TransformSpec
* **Return type:**
  [`Dict`](https://docs.python.org/3/library/typing.html#typing.Dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)]
* **Returns:**
  Dict of parameter name to extracted value

### qh.endpoint.make_endpoint(func, route_config)

Create FastAPI endpoint from a function using i2.Wrap.

* **Parameters:**
  * **func** ([`Callable`](https://docs.python.org/3/library/typing.html#typing.Callable)) – The Python function to wrap
  * **route_config** ([`RouteConfig`](qh.config.html.md#qh.config.RouteConfig)) – Configuration for this route
* **Return type:**
  [`Callable`](https://docs.python.org/3/library/typing.html#typing.Callable)
* **Returns:**
  Async endpoint function compatible with FastAPI

### qh.endpoint.validate_route_config(func, config)

Validate that route configuration is compatible with function.

* **Parameters:**
  * **func** ([`Callable`](https://docs.python.org/3/library/typing.html#typing.Callable)) – The function the route is for.
  * **config** ([`RouteConfig`](qh.config.html.md#qh.config.RouteConfig)) – The route configuration to check against `func`’s signature.
* **Raises:**
  [**ValueError**](https://docs.python.org/3/builtins/exceptions.html#ValueError) – If configuration is invalid
* **Return type:**
  [`None`](https://docs.python.org/3/builtins/constants.html#None)
