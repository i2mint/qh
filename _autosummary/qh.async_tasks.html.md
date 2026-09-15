# qh.async_tasks

Async task processing for qh.

Provides a minimal, boilerplate-free way to handle long-running operations
by returning task IDs immediately and allowing clients to poll for results.

Terminology (standard async task processing):

- Task: An asynchronous computation
- Task ID: Unique identifier for tracking a task
- Task Status: State of the task (pending, running, completed, failed)
- Task Result: The output of the completed task

Design Philosophy:

- Convention over configuration with escape hatches
- Pluggable backends (in-memory, file-based, au, Celery, etc.)
- HTTP-first patterns (query params, standard endpoints)

### Functions

| [`get_task_manager`](#qh.async_tasks.get_task_manager)(func_name[, config])   | Get or create a task manager for a function.              |
|------------------------------------------------------------------------------------------|-----------------------------------------------------------|
| [`should_run_async`](#qh.async_tasks.should_run_async)(request, config)       | Determine if a request should be executed asynchronously. |

### Classes

| [`InMemoryTaskStore`](#qh.async_tasks.InMemoryTaskStore)([ttl])                     | Simple in-memory task storage (not persistent, single-process only).   |
|-----------------------------------------------------------------------------------------------|------------------------------------------------------------------------|
| [`ProcessPoolTaskExecutor`](#qh.async_tasks.ProcessPoolTaskExecutor)([max_workers])       | Execute tasks using a process pool (good for CPU-bound tasks).         |
| [`TaskConfig`](#qh.async_tasks.TaskConfig)([store, executor, ttl, ...])      | Configuration for async task processing.                               |
| [`TaskExecutor`](#qh.async_tasks.TaskExecutor)()                               | Abstract interface for task execution backends.                        |
| [`TaskInfo`](#qh.async_tasks.TaskInfo)(task_id, status, created_at[, ...]) | Information about a task's state.                                      |
| [`TaskManager`](#qh.async_tasks.TaskManager)([config])                        | Manages async task execution and state.                                |
| [`TaskStatus`](#qh.async_tasks.TaskStatus)(\*values)                         | Standard task status values.                                           |
| [`TaskStore`](#qh.async_tasks.TaskStore)()                                  | Abstract interface for task storage backends.                          |
| [`ThreadPoolTaskExecutor`](#qh.async_tasks.ThreadPoolTaskExecutor)([max_workers])        | Execute tasks using a thread pool (good for I/O-bound tasks).          |

### *class* qh.async_tasks.InMemoryTaskStore(ttl=None)

Bases: [`TaskStore`](#qh.async_tasks.TaskStore)

Simple in-memory task storage (not persistent, single-process only).

#### create_task(task_id, func_name)

`TaskStore.create_task`: record a new pending task in memory.

* **Return type:**
  [`TaskInfo`](#qh.async_tasks.TaskInfo)

#### delete_task(task_id)

`TaskStore.delete_task`: remove a task, returning whether it existed.

* **Return type:**
  [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

#### get_task(task_id)

`TaskStore.get_task`: look up a task, or `None` if unknown.

* **Return type:**
  [`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`TaskInfo`](#qh.async_tasks.TaskInfo)]

#### list_tasks(limit=100)

`TaskStore.list_tasks`: the `limit` most recently created tasks, newest first.

* **Return type:**
  [`list`](https://docs.python.org/3/builtins/stdtypes.html#list)[[`TaskInfo`](#qh.async_tasks.TaskInfo)]

#### update_task(task_info)

`TaskStore.update_task`: overwrite the stored record for its task ID.

* **Return type:**
  [`None`](https://docs.python.org/3/builtins/constants.html#None)

### *class* qh.async_tasks.ProcessPoolTaskExecutor(max_workers=None)

Bases: [`TaskExecutor`](#qh.async_tasks.TaskExecutor)

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

### *class* qh.async_tasks.TaskConfig(store=None, executor=None, ttl=3600, async_mode='query', async_param='async', async_header='X-Async', create_task_endpoints=True, default_executor='thread')

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
  [`TaskExecutor`](#qh.async_tasks.TaskExecutor)

#### get_store()

Get or create the task store.

* **Return type:**
  [`TaskStore`](#qh.async_tasks.TaskStore)

### *class* qh.async_tasks.TaskExecutor

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

### *class* qh.async_tasks.TaskInfo(task_id, status, created_at, started_at=None, completed_at=None, result=None, error=None, traceback=None)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

Information about a task’s state.

#### to_dict()

Convert to dictionary for JSON serialization.

* **Return type:**
  [`Dict`](https://docs.python.org/3/library/typing.html#typing.Dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)]

### *class* qh.async_tasks.TaskManager(config=None)

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
  [`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`TaskInfo`](#qh.async_tasks.TaskInfo)]

#### list_tasks(limit=100)

List recent tasks.

* **Return type:**
  [`list`](https://docs.python.org/3/builtins/stdtypes.html#list)[[`TaskInfo`](#qh.async_tasks.TaskInfo)]

#### shutdown()

Shutdown the task manager and its executor.

* **Return type:**
  [`None`](https://docs.python.org/3/builtins/constants.html#None)

### *class* qh.async_tasks.TaskStatus(\*values)

Bases: [`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Enum`](https://docs.python.org/3/library/enum.html#enum.Enum)

Standard task status values.

### *class* qh.async_tasks.TaskStore

Bases: [`ABC`](https://docs.python.org/3/library/abc.html#abc.ABC)

Abstract interface for task storage backends.

#### *abstractmethod* create_task(task_id, func_name)

Create a new task record.

* **Return type:**
  [`TaskInfo`](#qh.async_tasks.TaskInfo)

#### *abstractmethod* delete_task(task_id)

Delete a task. Returns True if deleted, False if not found.

* **Return type:**
  [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

#### *abstractmethod* get_task(task_id)

Retrieve task information.

* **Return type:**
  [`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`TaskInfo`](#qh.async_tasks.TaskInfo)]

#### *abstractmethod* list_tasks(limit=100)

List recent tasks.

* **Return type:**
  [`list`](https://docs.python.org/3/builtins/stdtypes.html#list)[[`TaskInfo`](#qh.async_tasks.TaskInfo)]

#### *abstractmethod* update_task(task_info)

Update task information.

* **Return type:**
  [`None`](https://docs.python.org/3/builtins/constants.html#None)

### *class* qh.async_tasks.ThreadPoolTaskExecutor(max_workers=None)

Bases: [`TaskExecutor`](#qh.async_tasks.TaskExecutor)

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

### qh.async_tasks.get_task_manager(func_name, config=None)

Get or create a task manager for a function.

* **Parameters:**
  * **func_name** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – Name of the function
  * **config** ([`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`TaskConfig`](#qh.async_tasks.TaskConfig)]) – Task configuration (only used when creating new manager)
* **Return type:**
  [`TaskManager`](#qh.async_tasks.TaskManager)
* **Returns:**
  TaskManager instance

### qh.async_tasks.should_run_async(request, config)

Determine if a request should be executed asynchronously.

* **Parameters:**
  * **request** ([`Any`](https://docs.python.org/3/library/typing.html#typing.Any)) – FastAPI Request object
  * **config** ([`TaskConfig`](#qh.async_tasks.TaskConfig)) – Task configuration
* **Return type:**
  [`bool`](https://docs.python.org/3/builtins/functions.html#bool)
* **Returns:**
  True if request should be async
