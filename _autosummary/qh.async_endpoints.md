# qh.async_endpoints

Helper functions to create task management endpoints.

These endpoints provide standard HTTP interfaces for task status and results.

What a client sees is deliberately narrow: never a task’s traceback (it stays in
the task store and the server log), a failed task’s error text only with
`expose_errors=True`, never `_private` attributes of a result, and, when a
`TaskConfig` has a `task_owner`, only the caller’s own tasks (anyone else’s
answer 404). The cross-function task listing (`add_global_task_endpoints`) is
opt-in.

`qh.mk_app` uses `add_app_task_endpoints`: one set of `/tasks/...` routes
for all of an app’s async functions, each task resolved through the managers of
that app’s own `TaskConfig` objects (never a process-wide, name-keyed registry).

### Functions

| [`add_app_task_endpoints`](#qh.async_endpoints.add_app_task_endpoints)(app, task_configs, \*)   | Add one set of task endpoints serving the tasks of all the given functions.                                                                                                                     |
|--------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| [`add_global_task_endpoints`](#qh.async_endpoints.add_global_task_endpoints)(app[, ...])           | Add global task management endpoints (cross all functions).                                                                                                                                     |
| [`add_task_endpoints`](#qh.async_endpoints.add_task_endpoints)(app, func_name[, ...])       | Add task management endpoints for a specific function.                                                                                                                                          |
| [`task_info_for_client`](#qh.async_endpoints.task_info_for_client)(task_info, \*[, ...])      | The client-facing view of a task: `TaskInfo.to_dict()` without the traceback and owner, with the result's private attributes left out, and with the error text replaced unless `expose_errors`. |

### qh.async_endpoints.add_app_task_endpoints(app, task_configs, , path_prefix='/tasks', expose_errors=False)

Add one set of task endpoints serving the tasks of all the given functions.

Creates `GET {path_prefix}/{task_id}/status`, `.../result`,
`GET {path_prefix}/{task_id}` and `DELETE {path_prefix}/{task_id}`. A task
is looked up in the managers of `task_configs` only, and is visible to a
caller only if every `task_owner` among the configs that know the task
allows it.

* **Parameters:**
  * **app** (`FastAPI`) – FastAPI application
  * **task_configs** ([`Dict`](https://docs.python.org/3/library/typing.html#typing.Dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`TaskConfig`](qh.async_tasks.md#qh.async_tasks.TaskConfig)]]) – `{func_name: TaskConfig}` of the app’s async functions
  * **path_prefix** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – URL path prefix for task endpoints
  * **expose_errors** ([`bool`](https://docs.python.org/3/builtins/functions.html#bool)) – Whether a failed task’s error text reaches the client
    (its traceback never does).
* **Return type:**
  [`None`](https://docs.python.org/3/builtins/constants.html#None)

### qh.async_endpoints.add_global_task_endpoints(app, path_prefix='/tasks', , task_configs=None, expose_errors=False)

Add global task management endpoints (cross all functions).

Creates:

- GET {path_prefix}/ - List all recent tasks

`qh.mk_app` only adds this with `global_task_endpoints=True`: it lists the
tasks of every caller, except that a function whose `TaskConfig` has a
`task_owner` only contributes the caller’s own tasks.

* **Parameters:**
  * **app** (`FastAPI`) – FastAPI application
  * **path_prefix** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – URL path prefix for task endpoints
  * **task_configs** ([`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`Dict`](https://docs.python.org/3/library/typing.html#typing.Dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`TaskConfig`](qh.async_tasks.md#qh.async_tasks.TaskConfig)]]]) – `{func_name: TaskConfig}` of the functions to list (with
    the `task_owner` each one enforces). Defaults to every manager of
    the process-wide registry (`get_task_manager`), with its own config.
  * **expose_errors** ([`bool`](https://docs.python.org/3/builtins/functions.html#bool)) – Whether failed tasks’ error text is listed
* **Return type:**
  [`None`](https://docs.python.org/3/builtins/constants.html#None)

### qh.async_endpoints.add_task_endpoints(app, func_name, path_prefix='/tasks', , task_config=None, expose_errors=False)

Add task management endpoints for a specific function.

Creates the following endpoints:

- GET {path_prefix}/{task_id}/status - Get task status
- GET {path_prefix}/{task_id}/result - Get task result (waits if needed)
- GET {path_prefix}/{task_id} - Get complete task info
- DELETE {path_prefix}/{task_id} - Cancel/delete a task

* **Parameters:**
  * **app** (`FastAPI`) – FastAPI application
  * **func_name** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – Name of the function these tasks belong to
  * **path_prefix** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – URL path prefix for task endpoints
  * **task_config** ([`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`TaskConfig`](qh.async_tasks.md#qh.async_tasks.TaskConfig)]) – The function’s `TaskConfig`: its manager holds the tasks
    and its `task_owner` (if any) restricts every endpoint to the
    task’s creator. Without one, the function’s manager is looked up by
    name in the process-wide registry (`get_task_manager`).
  * **expose_errors** ([`bool`](https://docs.python.org/3/builtins/functions.html#bool)) – Whether a failed task’s error text reaches the client
    (its traceback never does).
* **Return type:**
  [`None`](https://docs.python.org/3/builtins/constants.html#None)

### qh.async_endpoints.task_info_for_client(task_info, , expose_errors=False)

The client-facing view of a task: `TaskInfo.to_dict()` without the
traceback and owner, with the result’s private attributes left out, and with
the error text replaced unless `expose_errors`.

* **Return type:**
  [`Dict`](https://docs.python.org/3/library/typing.html#typing.Dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)]

```pycon
>>> import time
>>> info = TaskInfo('t1', TaskStatus.FAILED, time.time(), error='/srv/db: denied',
...                 traceback='Traceback ...', owner='alice')
>>> d = task_info_for_client(info)
>>> 'traceback' in d, 'owner' in d, d['error'] == _HIDDEN_ERROR_TEXT
(False, False, True)
>>> task_info_for_client(info, expose_errors=True)['error']
'/srv/db: denied'
```
