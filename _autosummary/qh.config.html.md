# qh.config

Configuration system for qh with layered defaults.

Configuration flows from general to specific:

1. Global defaults
2. App-level config
3. Function-level config
4. Parameter-level config

### Functions

| [`from_dict`](#qh.config.from_dict)(config_dict)                        | Create AppConfig from dictionary.                               |
|------------------------------------------------------------------------------------------------|-----------------------------------------------------------------|
| [`normalize_funcs_input`](#qh.config.normalize_funcs_input)(funcs)                  | Normalize various input formats to Dict[Callable, RouteConfig]. |
| [`resolve_route_config`](#qh.config.resolve_route_config)(func, app_config[, ...]) | Resolve complete route configuration for a function.            |

### Classes

| [`AppConfig`](#qh.config.AppConfig)([default_methods, path_template, ...])   | Global configuration for the entire FastAPI app.               |
|-----------------------------------------------------------------------------------------------------|----------------------------------------------------------------|
| [`ConfigBuilder`](#qh.config.ConfigBuilder)()                                    | Fluent interface for building configurations.                  |
| [`FunctionConfigBuilder`](#qh.config.FunctionConfigBuilder)(parent, func)                | Fluent interface for building function-specific configuration. |
| [`RouteConfig`](#qh.config.RouteConfig)([path, methods, rule_chain, ...])      | Configuration for a single route (function endpoint).          |

### *class* qh.config.AppConfig(default_methods=<factory>, path_template='/{func_name}', path_prefix='', rule_chain=<factory>, title='qh API', version='0.1.0', docs_url='/docs', redoc_url='/redoc', openapi_url='/openapi.json', fastapi_kwargs=<factory>)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

Global configuration for the entire FastAPI app.

```pycon
>>> ac = AppConfig(path_prefix='/api')
>>> ac.default_methods, ac.path_prefix
(['POST'], '/api')
```

#### to_fastapi_kwargs()

Convert to FastAPI() constructor kwargs.

* **Return type:**
  [`Dict`](https://docs.python.org/3/library/typing.html#typing.Dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)]

### *class* qh.config.ConfigBuilder

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

Fluent interface for building configurations.

#### build()

Build final configuration.

* **Return type:**
  [`tuple`](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[`AppConfig`](#qh.config.AppConfig), [`Dict`](https://docs.python.org/3/library/typing.html#typing.Dict)[[`Callable`](https://docs.python.org/3/library/typing.html#typing.Callable), [`RouteConfig`](#qh.config.RouteConfig)]]

#### for_function(func)

Start configuring a specific function.

* **Return type:**
  [`FunctionConfigBuilder`](#qh.config.FunctionConfigBuilder)

#### with_default_methods(methods)

Set default HTTP methods.

* **Return type:**
  [`ConfigBuilder`](#qh.config.ConfigBuilder)

#### with_path_prefix(prefix)

Set path prefix for all routes.

* **Return type:**
  [`ConfigBuilder`](#qh.config.ConfigBuilder)

#### with_path_template(template)

Set path template for auto-generation.

* **Return type:**
  [`ConfigBuilder`](#qh.config.ConfigBuilder)

#### with_rule_chain(chain)

Set global rule chain.

* **Return type:**
  [`ConfigBuilder`](#qh.config.ConfigBuilder)

### *class* qh.config.FunctionConfigBuilder(parent, func)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

Fluent interface for building function-specific configuration.

#### at_path(path)

Set custom path for this function.

* **Return type:**
  [`FunctionConfigBuilder`](#qh.config.FunctionConfigBuilder)

#### done()

Finish configuring this function.

* **Return type:**
  [`ConfigBuilder`](#qh.config.ConfigBuilder)

#### with_methods(methods)

Set HTTP methods for this function.

* **Return type:**
  [`FunctionConfigBuilder`](#qh.config.FunctionConfigBuilder)

#### with_summary(summary)

Set OpenAPI summary.

* **Return type:**
  [`FunctionConfigBuilder`](#qh.config.FunctionConfigBuilder)

#### with_tags(tags)

Set OpenAPI tags.

* **Return type:**
  [`FunctionConfigBuilder`](#qh.config.FunctionConfigBuilder)

### *class* qh.config.RouteConfig(path=None, methods=None, rule_chain=None, param_overrides=<factory>, async_config=None, summary=None, description=None, tags=None, response_model=None, include_in_schema=True, deprecated=False)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

Configuration for a single route (function endpoint).

```pycon
>>> rc = RouteConfig(methods=['GET'])
>>> merged = rc.merge_with(RouteConfig(path='/x'))
>>> merged.methods, merged.path
(['GET'], '/x')
```

#### merge_with(other)

Merge with another config, other takes precedence.

* **Return type:**
  [`RouteConfig`](#qh.config.RouteConfig)

### qh.config.from_dict(config_dict)

Create AppConfig from dictionary.

* **Return type:**
  [`AppConfig`](#qh.config.AppConfig)

### qh.config.normalize_funcs_input(funcs)

Normalize various input formats to Dict[Callable, RouteConfig].

Supports:

- Single callable
- List of callables
- Dict mapping callable to config dict
- Dict mapping callable to RouteConfig

* **Return type:**
  [`Dict`](https://docs.python.org/3/library/typing.html#typing.Dict)[[`Callable`](https://docs.python.org/3/library/typing.html#typing.Callable), [`RouteConfig`](#qh.config.RouteConfig)]

### qh.config.resolve_route_config(func, app_config, route_config=None)

Resolve complete route configuration for a function.

Precedence (highest to lowest):

1. route_config (function-specific)
2. app_config (app-level defaults)
3. DEFAULT_ROUTE_CONFIG (global defaults)

* **Return type:**
  [`RouteConfig`](#qh.config.RouteConfig)
