# qh.au_integration

Integration layer between qh and au.

This module provides adapters to use au’s powerful backend/storage system
with qh’s user-friendly HTTP interface.

Philosophy:

- qh provides the HTTP layer (each function gets its own endpoint)
- au provides the execution backend and result storage
- This module bridges them together

### Functions

| [`use_au_backend`](#qh.au_integration.use_au_backend)([backend, store])            | Create a qh TaskConfig that uses au backend and storage.   |
|----------------------------------------------------------------------------------------------|------------------------------------------------------------|
| [`use_au_process_backend`](#qh.au_integration.use_au_process_backend)([storage_path, ...]) | Use au's ProcessBackend for CPU-bound tasks.               |
| [`use_au_redis_backend`](#qh.au_integration.use_au_redis_backend)([redis_url, ...])      | Use au's Redis/RQ backend for distributed tasks.           |
| [`use_au_thread_backend`](#qh.au_integration.use_au_thread_backend)([storage_path, ...])  | Use au's ThreadBackend with filesystem storage.            |

### Classes

| [`AuTaskExecutor`](#qh.au_integration.AuTaskExecutor)(au_backend, au_store)   | Adapter to use au's ComputationBackend as qh's TaskExecutor.   |
|-----------------------------------------------------------------------------------------|----------------------------------------------------------------|
| [`AuTaskStore`](#qh.au_integration.AuTaskStore)(au_store)                  | Adapter to use au's ComputationStore as qh's TaskStore.        |

### *class* qh.au_integration.AuTaskExecutor(au_backend, au_store)

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

### *class* qh.au_integration.AuTaskStore(au_store)

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

### qh.au_integration.use_au_backend(backend=None, store=None, \*\*au_config_kwargs)

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

### qh.au_integration.use_au_process_backend(storage_path='/tmp/qh_au_tasks', ttl_seconds=3600)

Use au’s ProcessBackend for CPU-bound tasks.

* **Return type:**
  [`TaskConfig`](qh.async_tasks.html.md#qh.async_tasks.TaskConfig)

### qh.au_integration.use_au_redis_backend(redis_url='redis://localhost:6379', storage_path='/tmp/qh_au_tasks', ttl_seconds=3600)

Use au’s Redis/RQ backend for distributed tasks.

* **Return type:**
  [`TaskConfig`](qh.async_tasks.html.md#qh.async_tasks.TaskConfig)

### qh.au_integration.use_au_thread_backend(storage_path='/tmp/qh_au_tasks', ttl_seconds=3600)

Use au’s ThreadBackend with filesystem storage.

* **Return type:**
  [`TaskConfig`](qh.async_tasks.html.md#qh.async_tasks.TaskConfig)
