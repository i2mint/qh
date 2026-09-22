# qh.async_endpoints

Helper functions to create task management endpoints.

These endpoints provide standard HTTP interfaces for task status and results.

### Functions

| [`add_global_task_endpoints`](#qh.async_endpoints.add_global_task_endpoints)(app[, path_prefix])     | Add global task management endpoints (cross all functions).   |
|----------------------------------------------------------------------------------------------------|---------------------------------------------------------------|
| [`add_task_endpoints`](#qh.async_endpoints.add_task_endpoints)(app, func_name[, path_prefix]) | Add task management endpoints for a specific function.        |

### qh.async_endpoints.add_global_task_endpoints(app, path_prefix='/tasks')

Add global task management endpoints (cross all functions).

Creates:

- GET {path_prefix}/ - List all recent tasks

* **Parameters:**
  * **app** (`FastAPI`) – FastAPI application
  * **path_prefix** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – URL path prefix for task endpoints
* **Return type:**
  [`None`](https://docs.python.org/3/builtins/constants.html#None)

### qh.async_endpoints.add_task_endpoints(app, func_name, path_prefix='/tasks')

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
* **Return type:**
  [`None`](https://docs.python.org/3/builtins/constants.html#None)
