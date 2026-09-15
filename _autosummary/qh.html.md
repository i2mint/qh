# qh

Quick HTTP: expose Python functions as a FastAPI web service with one call.

Give `mk_app` a function, a list of functions, or a dict of functions to route
configs, and get back a FastAPI app whose routes call those functions. Type
hints drive request validation and the OpenAPI document; an optional
convention layer infers RESTful paths and methods from function names; a rule
chain and a type registry decide where each parameter lives in the HTTP
request and how it is (de)serialized. The same app can be tested in-process,
served, turned into a Python, JavaScript or TypeScript client, and given
background-task endpoints for long-running functions.

Main entry points:

- `mk_app`: functions in, FastAPI app out (`qh.app`)
- `RouteConfig` / `AppConfig`: per-route and app-wide configuration (`qh.config`)
- `test_app` / `quick_test` / `service_running`: in-process and live testing (`qh.testing`)
- `mk_client_from_app` / `export_openapi`: clients and the OpenAPI document (`qh.client`, `qh.openapi`)
- `TaskConfig`: background execution for functions named in `async_funcs` (`qh.async_tasks`)

```pycon
>>> from qh import mk_app, test_app
>>> def add(x: int, y: int) -> int:
...     return x + y
>>> app = mk_app([add])
>>> with test_app(app) as client:
...     client.post('/add', json={'x': 3, 'y': 5}).json()
8
```

### Functions

| [`mk_app`](#qh.mk_app)(funcs, \*[, app, config, ...])              | Create a FastAPI application whose routes call the given Python functions.   |
|-----------------------------------------------------------------------------------------------------|------------------------------------------------------------------------------|
| [`inspect_routes`](#qh.inspect_routes)(app)                                | List the routes of a FastAPI app as plain dicts.                             |
| [`print_routes`](#qh.print_routes)(app)                                  | Print a text table of a FastAPI app's routes (methods, path, endpoint name). |
| [`register_type`](#qh.register_type)(python_type, \*, to_json, from_json) | Register a type in the global registry.                                      |
| [`register_json_type`](#qh.register_json_type)([cls, to_json, from_json])      | Decorator to register a custom type.                                         |
| [`export_openapi`](#qh.export_openapi)(app, \*[, include_examples, ...])   | Export the enhanced OpenAPI schema, optionally writing it to a file.         |
| [`enhance_openapi_schema`](#qh.enhance_openapi_schema)(app, \*[, ...])             | Generate an enhanced OpenAPI schema for a `qh` app.                          |
| [`install_enhanced_openapi`](#qh.install_enhanced_openapi)(app, \*\*enhance_kwargs)  | Make `app` serve the enhanced OpenAPI schema at its `/openapi.json`.         |
| [`python_type_to_json_schema`](#qh.python_type_to_json_schema)(type_hint, schemas, \*) | Convert a Python type hint to a JSON Schema fragment.                        |
| [`mk_client_from_openapi`](#qh.mk_client_from_openapi)(openapi_spec[, ...])        | Create an HTTP client from an OpenAPI specification.                         |
| [`mk_client_from_url`](#qh.mk_client_from_url)(openapi_url[, base_url, ...])   | Create an HTTP client by fetching OpenAPI spec from a URL.                   |
| [`mk_client_from_app`](#qh.mk_client_from_app)(app[, base_url])                | Create an HTTP client from a FastAPI app (for testing).                      |
| [`export_js_client`](#qh.export_js_client)(openapi_spec, \*[, ...])          | Generate JavaScript client class from OpenAPI spec.                          |
| [`export_ts_client`](#qh.export_ts_client)(openapi_spec, \*[, ...])          | Generate TypeScript client class from OpenAPI spec.                          |
| [`run_app`](#qh.run_app)(app, \*[, use_server])                     | Context manager for running a FastAPI app.                                   |
| [`test_app`](#qh.test_app)(app)                                      | Call an app in-process through a `TestClient`, no server, no port.           |
| [`serve_app`](#qh.serve_app)(app[, port, host])                       | Context manager for running app with real server.                            |
| [`quick_test`](#qh.quick_test)(func, \*\*kwargs)                       | Call one function through HTTP and return the decoded JSON response.         |
| [`service_running`](#qh.service_running)(\*[, url, app, launcher, ...])     | Ensure an HTTP service is running for testing purposes.                      |
| [`use_au_backend`](#qh.use_au_backend)([backend, store])                   | Create a qh TaskConfig that uses au backend and storage.                     |
| [`use_au_thread_backend`](#qh.use_au_thread_backend)([storage_path, ...])         | Use au's ThreadBackend with filesystem storage.                              |
| [`use_au_process_backend`](#qh.use_au_process_backend)([storage_path, ...])        | Use au's ProcessBackend for CPU-bound tasks.                                 |
| [`use_au_redis_backend`](#qh.use_au_redis_backend)([redis_url, ...])             | Use au's Redis/RQ backend for distributed tasks.                             |

### Classes

| [`AppConfig`](#qh.AppConfig)([default_methods, path_template, ...])   | Global configuration for the entire FastAPI app.                              |
|-----------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------|
| [`RouteConfig`](#qh.RouteConfig)([path, methods, rule_chain, ...])      | Configuration for a single route (function endpoint).                         |
| [`ConfigBuilder`](#qh.ConfigBuilder)()                                    | Fluent interface for building configurations.                                 |
| [`RuleChain`](#qh.RuleChain)([rules])                                 | Chain of rules evaluated in order with first-match semantics.                 |
| [`TransformSpec`](#qh.TransformSpec)([http_location, ingress, ...])       | Specification for how to transform a parameter.                               |
| [`HttpLocation`](#qh.HttpLocation)(\*values)                             | Where in HTTP request/response to map a parameter.                            |
| [`TypeRule`](#qh.TypeRule)(type_map)                                 | Rule that matches based on parameter type.                                    |
| [`NameRule`](#qh.NameRule)(name_map)                                 | Rule that matches based on parameter name.                                    |
| [`FuncRule`](#qh.FuncRule)(func_map)                                 | Rule that matches based on function.                                          |
| [`FuncNameRule`](#qh.FuncNameRule)(pattern_map)                          | Rule that matches based on function name pattern.                             |
| [`TypeRegistry`](#qh.TypeRegistry)()                                     | Registry for type handlers.                                                   |
| [`HttpClient`](#qh.HttpClient)(base_url[, session])                    | Client for calling HTTP endpoints with Python function interface.             |
| [`TaskConfig`](#qh.TaskConfig)([store, executor, ttl, ...])            | Configuration for async task processing.                                      |
| [`TaskStatus`](#qh.TaskStatus)(\*values)                               | Standard task status values.                                                  |
| [`TaskInfo`](#qh.TaskInfo)(task_id, status, created_at[, ...])       | Information about a task's state.                                             |
| [`TaskStore`](#qh.TaskStore)()                                        | Abstract interface for task storage backends.                                 |
| [`InMemoryTaskStore`](#qh.InMemoryTaskStore)([ttl])                           | Simple in-memory task storage (not persistent, single-process only).          |
| [`TaskExecutor`](#qh.TaskExecutor)()                                     | Abstract interface for task execution backends.                               |
| [`ThreadPoolTaskExecutor`](#qh.ThreadPoolTaskExecutor)([max_workers])              | Execute tasks using a thread pool (good for I/O-bound tasks).                 |
| [`ProcessPoolTaskExecutor`](#qh.ProcessPoolTaskExecutor)([max_workers])             | Execute tasks using a process pool (good for CPU-bound tasks).                |
| [`TaskManager`](#qh.TaskManager)([config])                              | Manages async task execution and state.                                       |
| [`AppRunner`](#qh.AppRunner)(app, \*[, use_server, host, port, ...])  | Context manager for running a FastAPI app in test mode or with a real server. |
| [`ServiceInfo`](#qh.ServiceInfo)(url, was_already_running[, ...])       | Information about a running service.                                          |
| [`AuTaskStore`](#qh.AuTaskStore)(au_store)                              | Adapter to use au's ComputationStore as qh's TaskStore.                       |
| [`AuTaskExecutor`](#qh.AuTaskExecutor)(au_backend, au_store)               | Adapter to use au's ComputationBackend as qh's TaskExecutor.                  |

### *class* qh.AppConfig(default_methods=<factory>, path_template='/{func_name}', path_prefix='', rule_chain=<factory>, title='qh API', version='0.1.0', docs_url='/docs', redoc_url='/redoc', openapi_url='/openapi.json', fastapi_kwargs=<factory>)

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

### *class* qh.AppRunner(app, , use_server=False, host='127.0.0.1', port=8000, server_timeout=2.0)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

Context manager for running a FastAPI app in test mode or with a real server.

Supports both synchronous testing (using TestClient) and integration testing
(using a real uvicorn server). With `use_server=False` (the default) the
`with` block receives a `TestClient`; with `use_server=True` it
receives the base URL of a uvicorn server started in a daemon thread. On
exit the TestClient reference is dropped; a real server is not stopped, its
daemon thread ends with the process. `run_app` is the function form.

### Examples

Basic usage with TestClient:

```pycon
>>> from qh import mk_app
>>> from qh.testing import AppRunner
>>> def add(x: int, y: int) -> int:
...     return x + y
>>> app = mk_app([add])
>>> with AppRunner(app) as client:
...     response = client.post('/add', json={'x': 3, 'y': 5})
...     assert response.json() == 8
```

With real server (integration testing):

```pycon
>>> with AppRunner(app, use_server=True, port=8001) as base_url:
...     response = requests.post(f'{base_url}/add', json={'x': 3, 'y': 5})
...     assert response.json() == 8
```

An exception inside the block propagates; `__exit__` still runs:

```pycon
>>> with AppRunner(app) as client:
...     raise ValueError("Test error")
```

### *class* qh.AuTaskExecutor(au_backend, au_store)

Bases: [`TaskExecutor`](qh.async_tasks.html.md#qh.async_tasks.TaskExecutor)

Adapter to use au’s ComputationBackend as qh’s TaskExecutor.

Delegates task execution to au’s backend system.

#### shutdown(wait=True)

Shutdown the executor.

* **Return type:**
  [`None`](https://docs.python.org/3/builtins/constants.html#None)

#### submit_task(task_id, func, args, kwargs, callback)

Submit a task to au backend.

#### NOTE
au handles result storage internally, so we don’t use the callback.
The callback is for qh’s built-in backends, but au’s store handles this.

* **Return type:**
  [`None`](https://docs.python.org/3/builtins/constants.html#None)

### *class* qh.AuTaskStore(au_store)

Bases: [`TaskStore`](qh.async_tasks.html.md#qh.async_tasks.TaskStore)

Adapter to use au’s ComputationStore as qh’s TaskStore.

Maps between qh’s TaskInfo and au’s computation results.

#### create_task(task_id, func_name)

Create a new task record.

* **Return type:**
  [`TaskInfo`](qh.async_tasks.html.md#qh.async_tasks.TaskInfo)

#### delete_task(task_id)

Delete `task_id` from the au store, returning whether it was present.

* **Return type:**
  [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

#### get_task(task_id)

Retrieve task information from au store.

* **Return type:**
  [`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`TaskInfo`](qh.async_tasks.html.md#qh.async_tasks.TaskInfo)]

#### list_tasks(limit=100)

List recent tasks.

* **Return type:**
  [`list`](https://docs.python.org/3/builtins/stdtypes.html#list)[[`TaskInfo`](qh.async_tasks.html.md#qh.async_tasks.TaskInfo)]

#### update_task(task_info)

Update task information.

#### NOTE
au manages its own state, so this is mostly a no-op.

* **Return type:**
  [`None`](https://docs.python.org/3/builtins/constants.html#None)

### *class* qh.ConfigBuilder

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

Fluent interface for building configurations.

#### build()

Build final configuration.

* **Return type:**
  [`tuple`](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[`AppConfig`](qh.config.html.md#qh.config.AppConfig), [`Dict`](https://docs.python.org/3/library/typing.html#typing.Dict)[[`Callable`](https://docs.python.org/3/library/typing.html#typing.Callable), [`RouteConfig`](qh.config.html.md#qh.config.RouteConfig)]]

#### for_function(func)

Start configuring a specific function.

* **Return type:**
  [`FunctionConfigBuilder`](qh.config.html.md#qh.config.FunctionConfigBuilder)

#### with_default_methods(methods)

Set default HTTP methods.

* **Return type:**
  [`ConfigBuilder`](qh.config.html.md#qh.config.ConfigBuilder)

#### with_path_prefix(prefix)

Set path prefix for all routes.

* **Return type:**
  [`ConfigBuilder`](qh.config.html.md#qh.config.ConfigBuilder)

#### with_path_template(template)

Set path template for auto-generation.

* **Return type:**
  [`ConfigBuilder`](qh.config.html.md#qh.config.ConfigBuilder)

#### with_rule_chain(chain)

Set global rule chain.

* **Return type:**
  [`ConfigBuilder`](qh.config.html.md#qh.config.ConfigBuilder)

### *class* qh.FuncNameRule(pattern_map)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

Rule that matches based on function name pattern.

#### match(, param_name, param_type, param_default, func, func_name)

Match by function name pattern.

* **Return type:**
  [`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`TransformSpec`](qh.rules.html.md#qh.rules.TransformSpec)]

### *class* qh.FuncRule(func_map)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

Rule that matches based on function.

#### match(, param_name, param_type, param_default, func, func_name)

Match by function object and parameter name.

* **Return type:**
  [`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`TransformSpec`](qh.rules.html.md#qh.rules.TransformSpec)]

### *class* qh.HttpClient(base_url, session=None)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

Client for calling HTTP endpoints with Python function interface.

Generated functions preserve original signatures and make HTTP requests
under the hood.

#### add_function(name, path, method, signature_info=None)

Add a function to the client.

* **Parameters:**
  * **name** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – Function name
  * **path** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – HTTP path (may contain {param} placeholders)
  * **method** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – HTTP method (GET, POST, etc.)
  * **signature_info** ([`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`Dict`](https://docs.python.org/3/library/typing.html#typing.Dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)]]) – Optional x-python-signature metadata
* **Return type:**
  [`None`](https://docs.python.org/3/builtins/constants.html#None)

### *class* qh.HttpLocation(\*values)

Bases: [`Enum`](https://docs.python.org/3/library/enum.html#enum.Enum)

Where in HTTP request/response to map a parameter.

### *class* qh.InMemoryTaskStore(ttl=None)

Bases: [`TaskStore`](qh.async_tasks.html.md#qh.async_tasks.TaskStore)

Simple in-memory task storage (not persistent, single-process only).

#### create_task(task_id, func_name)

`TaskStore.create_task`: record a new pending task in memory.

* **Return type:**
  [`TaskInfo`](qh.async_tasks.html.md#qh.async_tasks.TaskInfo)

#### delete_task(task_id)

`TaskStore.delete_task`: remove a task, returning whether it existed.

* **Return type:**
  [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

#### get_task(task_id)

`TaskStore.get_task`: look up a task, or `None` if unknown.

* **Return type:**
  [`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`TaskInfo`](qh.async_tasks.html.md#qh.async_tasks.TaskInfo)]

#### list_tasks(limit=100)

`TaskStore.list_tasks`: the `limit` most recently created tasks, newest first.

* **Return type:**
  [`list`](https://docs.python.org/3/builtins/stdtypes.html#list)[[`TaskInfo`](qh.async_tasks.html.md#qh.async_tasks.TaskInfo)]

#### update_task(task_info)

`TaskStore.update_task`: overwrite the stored record for its task ID.

* **Return type:**
  [`None`](https://docs.python.org/3/builtins/constants.html#None)

### *class* qh.NameRule(name_map)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

Rule that matches based on parameter name.

#### match(, param_name, param_type, param_default, func, func_name)

Match by parameter name.

* **Return type:**
  [`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`TransformSpec`](qh.rules.html.md#qh.rules.TransformSpec)]

### *class* qh.ProcessPoolTaskExecutor(max_workers=None)

Bases: [`TaskExecutor`](qh.async_tasks.html.md#qh.async_tasks.TaskExecutor)

Execute tasks using a process pool (good for CPU-bound tasks).

#### shutdown(wait=True)

`TaskExecutor.shutdown`: shut down the underlying process pool.

* **Return type:**
  [`None`](https://docs.python.org/3/builtins/constants.html#None)

#### submit_task(task_id, func, args, kwargs, callback)

`TaskExecutor.submit_task`: run `func` in a worker process, calling
`callback` with its result or exception when the future resolves.

* **Return type:**
  [`None`](https://docs.python.org/3/builtins/constants.html#None)

### *class* qh.RouteConfig(path=None, methods=None, rule_chain=None, param_overrides=<factory>, async_config=None, summary=None, description=None, tags=None, response_model=None, include_in_schema=True, deprecated=False)

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
  [`RouteConfig`](qh.config.html.md#qh.config.RouteConfig)

### *class* qh.RuleChain(rules=None)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

Chain of rules evaluated in order with first-match semantics.

Rules are tried from most specific to most general.

```pycon
>>> chain = RuleChain()
>>> chain.add_rule(TypeRule({int: TransformSpec(http_location=HttpLocation.QUERY)}))
>>> chain.match(param_name='x', param_type=int).http_location
<HttpLocation.QUERY: 'query'>
>>> chain.match(param_name='y', param_type=str) is None
True
```

#### add_rule(rule, priority=0)

Add a rule with optional priority (higher = evaluated earlier).

#### match(\*, param_name, param_type=<class 'NoneType'>, param_default, func=None, func_name='')

Find first matching rule.

* **Parameters:**
  * **param_name** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – The parameter’s name.
  * **param_type** ([`type`](https://docs.python.org/3/builtins/functions.html#type)) – The parameter’s type annotation.
  * **param_default** ([`Any`](https://docs.python.org/3/library/typing.html#typing.Any)) – The parameter’s default, or `inspect.Parameter.empty`.
  * **func** ([`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`Callable`](https://docs.python.org/3/library/typing.html#typing.Callable)]) – The function the parameter belongs to, if known.
  * **func_name** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – `func`’s name.
* **Return type:**
  [`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`TransformSpec`](qh.rules.html.md#qh.rules.TransformSpec)]
* **Returns:**
  TransformSpec from first matching rule, or None if no match

### *class* qh.ServiceInfo(url, was_already_running, thread=None, app=None)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

Information about a running service.

#### url

Base URL of the service (e.g., ‘[http://localhost:8000](http://localhost:8000)’)

#### was_already_running

True if service was already running, False if launched

#### thread

Thread object if service was launched in thread, None otherwise

#### app

The FastAPI app if one was provided, None otherwise

### *class* qh.TaskConfig(store=None, executor=None, ttl=3600, async_mode='query', async_param='async', async_header='X-Async', create_task_endpoints=True, default_executor='thread')

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

Configuration for async task processing.

This is the explicit configuration. The convention is to use sane defaults.
Pass an instance (or a dict) as `async_config` to `qh.mk_app`; `store`
and `executor` are built lazily by `get_store`/`get_executor` from
`default_executor` when left `None`.

```pycon
>>> tc = TaskConfig(ttl=60, default_executor='thread')
>>> tc.ttl, tc.async_mode
(60, 'query')
>>> type(tc.get_executor()).__name__
'ThreadPoolTaskExecutor'
```

#### get_executor()

Get or create the task executor.

* **Return type:**
  [`TaskExecutor`](qh.async_tasks.html.md#qh.async_tasks.TaskExecutor)

#### get_store()

Get or create the task store.

* **Return type:**
  [`TaskStore`](qh.async_tasks.html.md#qh.async_tasks.TaskStore)

### *class* qh.TaskExecutor

Bases: [`ABC`](https://docs.python.org/3/library/abc.html#abc.ABC)

Abstract interface for task execution backends.

#### *abstractmethod* shutdown(wait=True)

Shutdown the executor.

* **Return type:**
  [`None`](https://docs.python.org/3/builtins/constants.html#None)

#### *abstractmethod* submit_task(task_id, func, args, kwargs, callback)

Submit a task for execution.

* **Parameters:**
  * **task_id** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – Unique task identifier
  * **func** ([`Callable`](https://docs.python.org/3/library/typing.html#typing.Callable)) – Function to execute
  * **args** ([`tuple`](https://docs.python.org/3/builtins/stdtypes.html#tuple)) – Positional arguments
  * **kwargs** ([`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)) – Keyword arguments
  * **callback** ([`Callable`](https://docs.python.org/3/library/typing.html#typing.Callable)[[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any), [`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`Exception`](https://docs.python.org/3/builtins/exceptions.html#Exception)]], [`None`](https://docs.python.org/3/builtins/constants.html#None)]) – Called when task completes with (task_id, result, error)
* **Return type:**
  [`None`](https://docs.python.org/3/builtins/constants.html#None)

### *class* qh.TaskInfo(task_id, status, created_at, started_at=None, completed_at=None, result=None, error=None, traceback=None)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

Information about a task’s state.

#### to_dict()

Convert to dictionary for JSON serialization.

* **Return type:**
  [`Dict`](https://docs.python.org/3/library/typing.html#typing.Dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)]

### *class* qh.TaskManager(config=None)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

Manages async task execution and state.

This is the main coordinator between stores, executors, and HTTP handlers.

#### cancel_task(task_id)

Cancel a task (if possible).

* **Parameters:**
  **task_id** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – Task identifier
* **Return type:**
  [*bool*](https://docs.python.org/3/builtins/functions.html#bool)

#### NOTE
Cancellation is best-effort and may not work for all executors.

* **Return type:**
  [`bool`](https://docs.python.org/3/builtins/functions.html#bool)
* **Returns:**
  True if task was cancelled or deleted

#### create_task(func, args=(), kwargs=None)

Create and submit a new task.

* **Parameters:**
  * **func** ([`Callable`](https://docs.python.org/3/library/typing.html#typing.Callable)) – Function to execute asynchronously
  * **args** ([`tuple`](https://docs.python.org/3/builtins/stdtypes.html#tuple)) – Positional arguments
  * **kwargs** ([`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)]) – Keyword arguments
* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)
* **Returns:**
  Task ID

#### get_result(task_id, wait=False, timeout=None)

Get task result.

* **Parameters:**
  * **task_id** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – Task identifier
  * **wait** ([`bool`](https://docs.python.org/3/builtins/functions.html#bool)) – Whether to block until task completes
  * **timeout** ([`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`float`](https://docs.python.org/3/builtins/functions.html#float)]) – Maximum time to wait in seconds (None = wait forever)
* **Return type:**
  [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)
* **Returns:**
  Task result if completed
* **Raises:**
  * [**ValueError**](https://docs.python.org/3/builtins/exceptions.html#ValueError) – If task not found or failed
  * [**TimeoutError**](https://docs.python.org/3/builtins/exceptions.html#TimeoutError) – If wait times out

#### get_status(task_id)

Get task status and metadata.

* **Return type:**
  [`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`TaskInfo`](qh.async_tasks.html.md#qh.async_tasks.TaskInfo)]

#### list_tasks(limit=100)

List recent tasks.

* **Return type:**
  [`list`](https://docs.python.org/3/builtins/stdtypes.html#list)[[`TaskInfo`](qh.async_tasks.html.md#qh.async_tasks.TaskInfo)]

#### shutdown()

Shutdown the task manager and its executor.

* **Return type:**
  [`None`](https://docs.python.org/3/builtins/constants.html#None)

### *class* qh.TaskStatus(\*values)

Bases: [`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Enum`](https://docs.python.org/3/library/enum.html#enum.Enum)

Standard task status values.

### *class* qh.TaskStore

Bases: [`ABC`](https://docs.python.org/3/library/abc.html#abc.ABC)

Abstract interface for task storage backends.

#### *abstractmethod* create_task(task_id, func_name)

Create a new task record.

* **Return type:**
  [`TaskInfo`](qh.async_tasks.html.md#qh.async_tasks.TaskInfo)

#### *abstractmethod* delete_task(task_id)

Delete a task. Returns True if deleted, False if not found.

* **Return type:**
  [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

#### *abstractmethod* get_task(task_id)

Retrieve task information.

* **Return type:**
  [`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`TaskInfo`](qh.async_tasks.html.md#qh.async_tasks.TaskInfo)]

#### *abstractmethod* list_tasks(limit=100)

List recent tasks.

* **Return type:**
  [`list`](https://docs.python.org/3/builtins/stdtypes.html#list)[[`TaskInfo`](qh.async_tasks.html.md#qh.async_tasks.TaskInfo)]

#### *abstractmethod* update_task(task_info)

Update task information.

* **Return type:**
  [`None`](https://docs.python.org/3/builtins/constants.html#None)

### *class* qh.ThreadPoolTaskExecutor(max_workers=None)

Bases: [`TaskExecutor`](qh.async_tasks.html.md#qh.async_tasks.TaskExecutor)

Execute tasks using a thread pool (good for I/O-bound tasks).

#### shutdown(wait=True)

`TaskExecutor.shutdown`: shut down the underlying thread pool.

* **Return type:**
  [`None`](https://docs.python.org/3/builtins/constants.html#None)

#### submit_task(task_id, func, args, kwargs, callback)

`TaskExecutor.submit_task`: run `func` on the thread pool, calling
`callback` with its result or exception when it finishes.

* **Return type:**
  [`None`](https://docs.python.org/3/builtins/constants.html#None)

### *class* qh.TransformSpec(http_location=HttpLocation.JSON_BODY, ingress=None, egress=None, http_name=None, metadata=<factory>)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

Specification for how to transform a parameter.

### *class* qh.TypeRegistry

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
  [`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`TypeHandler`](qh.types.html.md#qh.types.TypeHandler)]
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

### *class* qh.TypeRule(type_map)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

Rule that matches based on parameter type.

#### match(, param_name, param_type, param_default, func, func_name)

Match by type, including type hierarchy.

* **Return type:**
  [`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`TransformSpec`](qh.rules.html.md#qh.rules.TransformSpec)]

### qh.enhance_openapi_schema(app, , include_examples=True, include_python_metadata=True, include_schemas=True, include_transformers=False)

Generate an enhanced OpenAPI schema for a `qh` app.

On top of FastAPI’s base document this fills in what `qh`’s
`Request`-based endpoints hide from FastAPI:

- `requestBody` / `parameters` / `responses` JSON Schema derived from
  each wrapped function’s Python type hints (`include_schemas`),
- `components.schemas` for every dataclass / `TypedDict` / Pydantic
  model / `NamedTuple` / `Enum` referenced,
- `x-python-signature` metadata (`include_python_metadata`),
- request examples (`include_examples`).

* **Parameters:**
  * **app** (`FastAPI`) – the FastAPI application.
  * **include_examples** ([`bool`](https://docs.python.org/3/builtins/functions.html#bool)) – add example requests.
  * **include_python_metadata** ([`bool`](https://docs.python.org/3/builtins/functions.html#bool)) – add `x-python-*` extensions.
  * **include_schemas** ([`bool`](https://docs.python.org/3/builtins/functions.html#bool)) – derive `requestBody` / `responses` /
    `components.schemas` from the Python type hints.
  * **include_transformers** ([`bool`](https://docs.python.org/3/builtins/functions.html#bool)) – add (placeholder) transformation metadata.
* **Return type:**
  [`Dict`](https://docs.python.org/3/library/typing.html#typing.Dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)]
* **Returns:**
  the enhanced OpenAPI schema dictionary.

### qh.export_js_client(openapi_spec, , class_name='ApiClient', use_axios=False, base_url='http://localhost:8000')

Generate JavaScript client class from OpenAPI spec.

* **Parameters:**
  * **openapi_spec** ([`Dict`](https://docs.python.org/3/library/typing.html#typing.Dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)]) – OpenAPI specification dictionary
  * **class_name** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – Name for the generated class
  * **use_axios** ([`bool`](https://docs.python.org/3/builtins/functions.html#bool)) – Use axios instead of fetch
  * **base_url** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – Default base URL
* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)
* **Returns:**
  JavaScript code as string

### Example

```pycon
>>> from qh import mk_app, export_openapi
>>> from qh.jsclient import export_js_client
>>> app = mk_app([add, subtract])
>>> spec = export_openapi(app)
>>> js_code = export_js_client(spec, use_axios=True)
```

### qh.export_openapi(app, , include_examples=True, include_python_metadata=True, include_schemas=True, include_transformers=False, output_file=None)

Export the enhanced OpenAPI schema, optionally writing it to a file.

* **Parameters:**
  * **app** (`FastAPI`) – the FastAPI application.
  * **include_examples** ([`bool`](https://docs.python.org/3/builtins/functions.html#bool)) – include example requests.
  * **include_python_metadata** ([`bool`](https://docs.python.org/3/builtins/functions.html#bool)) – include `x-python-*` extensions.
  * **include_schemas** ([`bool`](https://docs.python.org/3/builtins/functions.html#bool)) – derive `requestBody` / `responses` /
    `components.schemas` from the Python type hints.
  * **include_transformers** ([`bool`](https://docs.python.org/3/builtins/functions.html#bool)) – include transformation metadata.
  * **output_file** ([`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]) – optional path to write the JSON document to.
* **Return type:**
  [`Dict`](https://docs.python.org/3/library/typing.html#typing.Dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)]
* **Returns:**
  the enhanced OpenAPI schema dictionary.

### Example

```pycon
>>> from qh import mk_app
>>> from qh.openapi import export_openapi
>>> app = mk_app([my_func])
>>> spec = export_openapi(app, include_examples=True)
```

### qh.export_ts_client(openapi_spec, , class_name='ApiClient', use_axios=False, base_url='http://localhost:8000')

Generate TypeScript client class from OpenAPI spec.

* **Parameters:**
  * **openapi_spec** ([`Dict`](https://docs.python.org/3/library/typing.html#typing.Dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)]) – OpenAPI specification dictionary
  * **class_name** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – Name for the generated class
  * **use_axios** ([`bool`](https://docs.python.org/3/builtins/functions.html#bool)) – Use axios instead of fetch
  * **base_url** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – Default base URL
* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)
* **Returns:**
  TypeScript code as string

### Example

```pycon
>>> from qh import mk_app, export_openapi
>>> from qh.jsclient import export_ts_client
>>> app = mk_app([add, subtract])
>>> spec = export_openapi(app, include_python_metadata=True)
>>> ts_code = export_ts_client(spec, use_axios=True)
```

### qh.inspect_routes(app)

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

### qh.install_enhanced_openapi(app, \*\*enhance_kwargs)

Make `app` serve the enhanced OpenAPI schema at its `/openapi.json`.

Overrides `app.openapi` so the document returned by FastAPI — and rendered
by `/docs` and `/redoc` — carries the request/response JSON Schema and
`components.schemas` derived from the wrapped functions’ Python type hints.

The override is **defensive**: if enhancement raises for any reason, it
falls back to FastAPI’s plain schema, so a converter bug can never turn
`/openapi.json` into a 500.

* **Parameters:**
  * **app** (`FastAPI`) – the FastAPI application (typically the result of [`qh.mk_app()`](#qh.mk_app)).
  * **\*\*enhance_kwargs** ([`Any`](https://docs.python.org/3/library/typing.html#typing.Any)) – forwarded to [`enhance_openapi_schema()`](#qh.enhance_openapi_schema).
* **Return type:**
  `FastAPI`
* **Returns:**
  the same `app`, for chaining.

### qh.mk_app(funcs, , app=None, config=None, use_conventions=False, async_funcs=None, async_config=None, enhanced_openapi=True, \*\*kwargs)

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

### qh.mk_client_from_app(app, base_url='http://testserver')

Create an HTTP client from a FastAPI app (for testing).

* **Parameters:**
  * **app** – FastAPI application
  * **base_url** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – Base URL for API requests (default for TestClient)
* **Return type:**
  [`HttpClient`](qh.client.html.md#qh.client.HttpClient)
* **Returns:**
  HttpClient that uses FastAPI TestClient under the hood

### Example

```pycon
>>> from qh import mk_app
>>> from qh.client import mk_client_from_app
>>> app = mk_app([add, subtract])
>>> client = mk_client_from_app(app)
>>> result = client.add(x=3, y=5)
```

### qh.mk_client_from_openapi(openapi_spec, base_url='http://localhost:8000', session=None)

Create an HTTP client from an OpenAPI specification.

* **Parameters:**
  * **openapi_spec** ([`Dict`](https://docs.python.org/3/library/typing.html#typing.Dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)]) – The parsed OpenAPI document (as from `export_openapi`
    or `json.load` on a spec file), used to build one client function
    per operation.
  * **base_url** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – Base URL for API requests
  * **session** ([`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[`Session`]) – An existing session to reuse (e.g. for shared auth/headers);
    a new one is created if not given.
* **Return type:**
  [`HttpClient`](qh.client.html.md#qh.client.HttpClient)
* **Returns:**
  HttpClient with functions for each endpoint

### Example

```pycon
>>> from qh.client import mk_client_from_openapi
>>> spec = {'paths': {'/add': {...}}, ...}
>>> client = mk_client_from_openapi(spec, 'http://localhost:8000')
>>> result = client.add(x=3, y=5)
```

### qh.mk_client_from_url(openapi_url, base_url=None, session=None)

Create an HTTP client by fetching OpenAPI spec from a URL.

* **Parameters:**
  * **openapi_url** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – URL to OpenAPI JSON spec (e.g., “[http://localhost:8000/openapi.json](http://localhost:8000/openapi.json)”)
  * **base_url** ([`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]) – Base URL for API requests (defaults to same as openapi_url)
  * **session** ([`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[`Session`]) – An existing session to reuse; a new one is created if not given.
* **Return type:**
  [`HttpClient`](qh.client.html.md#qh.client.HttpClient)
* **Returns:**
  HttpClient with functions for each endpoint

### Example

```pycon
>>> from qh.client import mk_client_from_url
>>> client = mk_client_from_url('http://localhost:8000/openapi.json')
>>> result = client.add(x=3, y=5)
```

### qh.print_routes(app)

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

### qh.python_type_to_json_schema(type_hint, schemas, , \_stack=None)

Convert a Python type hint to a JSON Schema fragment.

Primitives, containers and unions are inlined. Named composite types —
dataclasses, `TypedDict`s, Pydantic models, `NamedTuple`s and
`Enum`s — are registered in `schemas` (the OpenAPI
`components.schemas` table) and returned as a `$ref`, so the same type
used in several places is described once.

* **Parameters:**
  * **type_hint** ([`Any`](https://docs.python.org/3/library/typing.html#typing.Any)) – the Python type / annotation to convert. `Any` and
    `inspect.Parameter.empty` map to the empty schema `{}`
    (matches anything); `None` / `NoneType` map to `{"type": "null"}`.
  * **schemas** ([`Dict`](https://docs.python.org/3/library/typing.html#typing.Dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)]) – the mutable `components.schemas` accumulator — composite
    types encountered are added here, keyed by their class name.
  * **\_stack** ([`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`frozenset`](https://docs.python.org/3/builtins/stdtypes.html#frozenset)]) – internal — the set of composite type names currently being
    built, used to break recursion on self-referential types.
* **Return type:**
  [`Dict`](https://docs.python.org/3/library/typing.html#typing.Dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)]
* **Returns:**
  a JSON Schema dict — an inline fragment, or `{"$ref": ...}` for a
  named composite type.

### Examples

```pycon
>>> python_type_to_json_schema(int, {})
{'type': 'integer'}
>>> python_type_to_json_schema(list[str], {})
{'type': 'array', 'items': {'type': 'string'}}
>>> python_type_to_json_schema(Optional[int], {})
{'anyOf': [{'type': 'integer'}, {'type': 'null'}]}
```

### qh.quick_test(func, \*\*kwargs)

Call one function through HTTP and return the decoded JSON response.

Builds `mk_app([func])`, POSTs `kwargs` as the JSON body to
`/<func name>`, and returns `response.json()`. Meant for a one-line
smoke check of what a function looks like over HTTP.

* **Parameters:**
  * **func** – Function to test
  * **\*\*kwargs** – Arguments to pass to the function (sent as the JSON body)
* **Returns:**
  The JSON-decoded response body, i.e. the function’s return value after
  JSON round-tripping.
* **Raises:**
  **httpx.HTTPStatusError** – If the response status is 4xx or 5xx (for
      example a missing required argument, or an exception in
      `func`); `fastapi.testclient.TestClient` is httpx-based, not
      requests-based.

### Examples

```pycon
>>> from qh.testing import quick_test
>>>
>>> def add(x: int, y: int) -> int:
...     return x + y
>>>
>>> result = quick_test(add, x=3, y=5)
>>> assert result == 8
>>>
>>> def greet(name: str) -> str:
...     return f"Hello, {name}!"
>>>
>>> result = quick_test(greet, name="World")
>>> assert result == "Hello, World!"
```

### qh.register_json_type(cls=None, , to_json=None, from_json=None)

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

### qh.register_type(python_type, , to_json, from_json, http_location=HttpLocation.JSON_BODY, content_type=None)

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

### qh.run_app(app, , use_server=False, \*\*kwargs)

Context manager for running a FastAPI app.

A convenience wrapper around AppRunner.

* **Parameters:**
  * **app** (`FastAPI`) – FastAPI application
  * **use_server** ([`bool`](https://docs.python.org/3/builtins/functions.html#bool)) – If True, runs real server; if False, uses TestClient
  * **\*\*kwargs** – Additional arguments passed to AppRunner
* **Yields:**
  TestClient or base URL string
* **Return type:**
  [*Generator*](https://docs.python.org/3/library/typing.html#typing.Generator)[*TestClient* | [*str*](https://docs.python.org/3/builtins/stdtypes.html#str), *None*, *None*]

### Examples

```pycon
>>> from qh import mk_app
>>> from qh.testing import run_app
>>> def add(x: int, y: int) -> int:
...     return x + y
>>> app = mk_app([add])
>>> # Quick testing with TestClient
>>> with run_app(app) as client:
...     result = client.post('/add', json={'x': 3, 'y': 5})
...     assert result.json() == 8
>>> # Integration testing with real server
>>> with run_app(app, use_server=True, port=8001) as url:
...     result = requests.post(f'{url}/add', json={'x': 3, 'y': 5})
...     assert result.json() == 8
```

### qh.serve_app(app, port=8000, host='127.0.0.1')

Context manager for running app with real server.

Convenience wrapper for integration testing with a real uvicorn server.

* **Parameters:**
  * **app** (`FastAPI`) – FastAPI application
  * **port** ([`int`](https://docs.python.org/3/builtins/functions.html#int)) – Port to bind to
  * **host** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – Host to bind to
* **Yields:**
  Base URL string
* **Return type:**
  [*Generator*](https://docs.python.org/3/library/typing.html#typing.Generator)[[*str*](https://docs.python.org/3/builtins/stdtypes.html#str), *None*, *None*]

### Examples

```pycon
>>> from qh import mk_app
>>> from qh.testing import serve_app
>>> import requests
>>> def multiply(x: int, y: int) -> int:
...     return x * y
>>> app = mk_app([multiply])
>>> with serve_app(app, port=8001) as url:
...     response = requests.post(f'{url}/multiply', json={'x': 4, 'y': 5})
...     assert response.json() == 20
```

### qh.service_running(, url=None, app=None, launcher=None, port=8000, host='127.0.0.1', startup_wait=2.0, readiness_check_interval=0.2, readiness_timeout=10.0, log_level='error')

Ensure an HTTP service is running for testing purposes.

This context manager checks if a service is already running at the specified URL.
If not running, it launches the service using one of the provided methods (app,
launcher). Either way, it leaves the service running on exit – see the Note below.

Exactly one of `url`, `app`, or `launcher` must be provided.

#### NOTE
Services are launched in daemon threads (not processes) to avoid
serialization issues with FastAPI apps on macOS. A service this
context manager launched is not stopped on exit: the thread ends
with the process.

* **Parameters:**
  * **url** ([`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]) – URL of an existing service to check (e.g., ‘[http://localhost:8000](http://localhost:8000)’).
    If provided alone, will fail if service is not running.
  * **app** ([`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[`FastAPI`]) – FastAPI/ASGI app to serve using uvicorn
  * **launcher** ([`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`Callable`](https://docs.python.org/3/library/typing.html#typing.Callable)[[], [`None`](https://docs.python.org/3/builtins/constants.html#None)]]) – Custom callable to launch the service (will run in background thread)
  * **port** ([`int`](https://docs.python.org/3/builtins/functions.html#int)) – Port to bind service to (used with app or launcher)
  * **host** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – Host to bind service to (used with app or launcher)
  * **startup_wait** ([`float`](https://docs.python.org/3/builtins/functions.html#float)) – Initial wait time after launching (seconds)
  * **readiness_check_interval** ([`float`](https://docs.python.org/3/builtins/functions.html#float)) – Polling interval for readiness checks (seconds)
  * **readiness_timeout** ([`float`](https://docs.python.org/3/builtins/functions.html#float)) – Maximum time to wait for service to be ready (seconds)
  * **log_level** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – Uvicorn log level when serving an app
* **Yields:**
  *ServiceInfo* – Information about the running service including URL and status
* **Raises:**
  * [**ValueError**](https://docs.python.org/3/builtins/exceptions.html#ValueError) – If none, or more than one, of `url`, `app` and `launcher` is given.
  * [**RuntimeError**](https://docs.python.org/3/builtins/exceptions.html#RuntimeError) – If `url` alone was given and nothing answers there, or if a
        launched service does not answer within `readiness_timeout` seconds.
* **Return type:**
  [*Generator*](https://docs.python.org/3/library/typing.html#typing.Generator)[[*ServiceInfo*](qh.testing.html.md#qh.testing.ServiceInfo), *None*, *None*]

### Examples

Test a qh app (launches a server in a daemon thread):

```pycon
>>> from qh import mk_app
>>> def add(x: int, y: int) -> int:
...     return x + y
>>> app = mk_app([add])
>>> with service_running(app=app, port=8001) as info:
...     response = requests.post(f'{info.url}/add', json={'x': 3, 'y': 5})
...     assert response.json() == 8
...     assert not info.was_already_running
```

Test an already-running service (won’t tear down):

```pycon
>>> with service_running(url='https://api.github.com') as info:
...     response = requests.get(f'{info.url}/users/octocat')
...     assert info.was_already_running
```

Use custom launcher:

```pycon
>>> def my_launcher():
...     # Custom service startup code
...     pass
>>> with service_running(launcher=my_launcher, port=8002) as info:
...     # Test your service
...     pass
```

### qh.test_app(app)

Call an app in-process through a `TestClient`, no server, no port.

The most common case, and the fastest: requests are dispatched straight
to the ASGI app. Use `serve_app` when a real socket matters (another
process, a browser, a generated client pointed at a URL).

* **Parameters:**
  **app** (`FastAPI`) – FastAPI application
* **Yields:**
  TestClient instance
* **Return type:**
  [*Generator*](https://docs.python.org/3/library/typing.html#typing.Generator)[*TestClient*, *None*, *None*]

### Examples

```pycon
>>> from qh import mk_app
>>> from qh.testing import test_app
>>> def hello(name: str = "World") -> str:
...     return f"Hello, {name}!"
>>> app = mk_app([hello])
>>> with test_app(app) as client:
...     client.post('/hello', json={'name': 'Alice'}).json()
'Hello, Alice!'
```

A missing required argument is a `422`, as in FastAPI:

```pycon
>>> def add(x: int, y: int) -> int:
...     return x + y
>>> with test_app(mk_app([add])) as client:
...     client.post('/add', json={'x': 3}).status_code
422
```

### qh.use_au_backend(backend=None, store=None, \*\*au_config_kwargs)

Create a qh TaskConfig that uses au backend and storage.

This is the main bridge function that lets qh use au.

* **Parameters:**
  * **backend** ([`None`](https://docs.python.org/3/builtins/constants.html#None)) – au ComputationBackend (ThreadBackend, ProcessBackend, RQBackend, etc.)
    If None, uses au’s default from config
  * **store** ([`None`](https://docs.python.org/3/builtins/constants.html#None)) – au ComputationStore (FileSystemStore, etc.)
    If None, uses au’s default from config
  * **\*\*au_config_kwargs** – Additional config passed to au
* **Return type:**
  [`TaskConfig`](qh.async_tasks.html.md#qh.async_tasks.TaskConfig)
* **Returns:**
  TaskConfig configured to use au
* **Raises:**
  [**ImportError**](https://docs.python.org/3/builtins/exceptions.html#ImportError) – If the `au` package is not installed.

### Example

```pycon
>>> from au import ThreadBackend, FileSystemStore
>>> from qh import mk_app
>>> from qh.au_integration import use_au_backend
>>> # Use au with thread backend and filesystem storage
>>> def slow_func(n: int) -> int:
...     import time
...     time.sleep(2)
...     return n * 2
>>> app = mk_app(
...     [slow_func],
...     async_funcs=['slow_func'],
...     async_config=use_au_backend(
...         backend=ThreadBackend(),
...         store=FileSystemStore('/tmp/qh_tasks')
...     )
... )
```

Example with au’s global config:

```pycon
>>> # Set AU environment variables:
>>> # AU_BACKEND=redis
>>> # AU_REDIS_URL=redis://localhost:6379
>>> # AU_STORAGE=filesystem
>>> # AU_STORAGE_PATH=/var/qh/tasks
>>> app = mk_app(
...     [slow_func],
...     async_funcs=['slow_func'],
...     async_config=use_au_backend()  # Uses au's config
... )
```

### qh.use_au_process_backend(storage_path='/tmp/qh_au_tasks', ttl_seconds=3600)

Use au’s ProcessBackend for CPU-bound tasks.

* **Return type:**
  [`TaskConfig`](qh.async_tasks.html.md#qh.async_tasks.TaskConfig)

### qh.use_au_redis_backend(redis_url='redis://localhost:6379', storage_path='/tmp/qh_au_tasks', ttl_seconds=3600)

Use au’s Redis/RQ backend for distributed tasks.

* **Return type:**
  [`TaskConfig`](qh.async_tasks.html.md#qh.async_tasks.TaskConfig)

### qh.use_au_thread_backend(storage_path='/tmp/qh_au_tasks', ttl_seconds=3600)

Use au’s ThreadBackend with filesystem storage.

* **Return type:**
  [`TaskConfig`](qh.async_tasks.html.md#qh.async_tasks.TaskConfig)

### Modules

| [`app`](qh.app.html.md#module-qh.app)                         | Build a FastAPI application from plain Python functions.                             |
|--------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------|
| [`async_endpoints`](qh.async_endpoints.html.md#module-qh.async_endpoints) | Helper functions to create task management endpoints.                                |
| [`async_tasks`](qh.async_tasks.html.md#module-qh.async_tasks)         | Async task processing for qh.                                                        |
| [`au_integration`](qh.au_integration.html.md#module-qh.au_integration)   | Integration layer between qh and au.                                                 |
| [`base`](qh.base.html.md#module-qh.base)                       | Config-free dispatch of Python callables as FastAPI routes, plus a store dispatcher. |
| [`client`](qh.client.html.md#module-qh.client)                   | Python client generation from OpenAPI specs.                                         |
| [`config`](qh.config.html.md#module-qh.config)                   | Configuration system for qh with layered defaults.                                   |
| [`conventions`](qh.conventions.html.md#module-qh.conventions)         | Convention-based routing for qh.                                                     |
| [`core`](qh.core.html.md#module-qh.core)                       | Minimal function-to-route dispatch built on `i2.wrapper.Wrap`.                       |
| [`endpoint`](qh.endpoint.html.md#module-qh.endpoint)               | Endpoint creation using i2.Wrap to transform functions into FastAPI routes.          |
| [`jsclient`](qh.jsclient.html.md#module-qh.jsclient)               | JavaScript and TypeScript client generation from OpenAPI specs.                      |
| [`openapi`](qh.openapi.html.md#module-qh.openapi)                 | OpenAPI generation for qh — including JSON Schema derived from Python type hints.    |
| [`rules`](qh.rules.html.md#module-qh.rules)                     | Transformation rule system for qh.                                                   |
| [`stores_qh`](qh.stores_qh.html.md#module-qh.stores_qh)             | FastAPI service for operating on stores objects.                                     |
| [`testing`](qh.testing.html.md#module-qh.testing)                 | Run a qh (or any FastAPI) app for a test: in-process, or on a real port.             |
| [`types`](qh.types.html.md#module-qh.types)                     | Type registry for qh - automatic serialization/deserialization for custom types.     |
