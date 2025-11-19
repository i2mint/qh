"""
Integration layer between qh and au.

This module provides adapters to use au's powerful backend/storage system
with qh's user-friendly HTTP interface.

Philosophy:
- qh provides the HTTP layer (each function gets its own endpoint)
- au provides the execution backend and result storage
- This module bridges them together
"""

from typing import Any, Callable, Optional
import inspect

from qh.async_tasks import (
    TaskConfig,
    TaskStore,
    TaskInfo,
    TaskStatus,
    TaskExecutor,
)

try:
    from au import (
        submit_task as au_submit_task,
        get_result as au_get_result,
        get_status as au_get_status,
        cancel_task as au_cancel_task,
        ComputationStatus,
        FileSystemStore,
        ThreadBackend,
        ProcessBackend,
        get_global_config,
    )
    from au.base import ComputationStore, ComputationBackend
    HAS_AU = True
except ImportError:
    HAS_AU = False
    ComputationStore = None
    ComputationBackend = None


class AuTaskStore(TaskStore):
    """
    Adapter to use au's ComputationStore as qh's TaskStore.

    Maps between qh's TaskInfo and au's computation results.
    """

    def __init__(self, au_store: 'ComputationStore'):
        if not HAS_AU:
            raise ImportError("au is required. Install with: pip install au")
        self.au_store = au_store

    def _au_status_to_qh_status(self, au_status: 'ComputationStatus') -> TaskStatus:
        """Convert au status to qh status."""
        mapping = {
            ComputationStatus.PENDING: TaskStatus.PENDING,
            ComputationStatus.RUNNING: TaskStatus.RUNNING,
            ComputationStatus.COMPLETED: TaskStatus.COMPLETED,
            ComputationStatus.FAILED: TaskStatus.FAILED,
        }
        return mapping.get(au_status, TaskStatus.PENDING)

    def create_task(self, task_id: str, func_name: str) -> TaskInfo:
        """Create a new task record."""
        import time
        task_info = TaskInfo(
            task_id=task_id,
            status=TaskStatus.PENDING,
            created_at=time.time(),
        )
        # au creates records when submitting, we just return info
        return task_info

    def get_task(self, task_id: str) -> Optional[TaskInfo]:
        """Retrieve task information from au store."""
        if task_id not in self.au_store:
            return None

        try:
            # Get au status
            au_status = au_get_status(task_id, store=self.au_store)

            # Convert to qh TaskInfo
            import time
            task_info = TaskInfo(
                task_id=task_id,
                status=self._au_status_to_qh_status(au_status),
                created_at=time.time(),  # au doesn't expose this easily
            )

            # Try to get result/error if completed
            if au_status == ComputationStatus.COMPLETED:
                try:
                    result = au_get_result(task_id, timeout=0, store=self.au_store)
                    task_info.result = result
                    task_info.completed_at = time.time()
                except:
                    pass
            elif au_status == ComputationStatus.FAILED:
                try:
                    au_get_result(task_id, timeout=0, store=self.au_store)
                except Exception as e:
                    task_info.error = str(e)
                    task_info.completed_at = time.time()

            return task_info

        except Exception:
            return None

    def update_task(self, task_info: TaskInfo) -> None:
        """Update task information.

        Note: au manages its own state, so this is mostly a no-op.
        """
        pass

    def delete_task(self, task_id: str) -> bool:
        """Delete a task."""
        if task_id in self.au_store:
            del self.au_store[task_id]
            return True
        return False

    def list_tasks(self, limit: int = 100) -> list[TaskInfo]:
        """List recent tasks."""
        tasks = []
        for task_id in list(self.au_store)[:limit]:
            task_info = self.get_task(task_id)
            if task_info:
                tasks.append(task_info)
        return tasks


class AuTaskExecutor(TaskExecutor):
    """
    Adapter to use au's ComputationBackend as qh's TaskExecutor.

    Delegates task execution to au's backend system.
    """

    def __init__(
        self,
        au_backend: 'ComputationBackend',
        au_store: 'ComputationStore',
    ):
        if not HAS_AU:
            raise ImportError("au is required. Install with: pip install au")
        self.au_backend = au_backend
        self.au_store = au_store

    def submit_task(
        self,
        task_id: str,
        func: Callable,
        args: tuple,
        kwargs: dict,
        callback: Callable[[str, Any, Optional[Exception]], None],
    ) -> None:
        """Submit a task to au backend.

        Note: au handles result storage internally, so we don't use the callback.
        The callback is for qh's built-in backends, but au's store handles this.
        """
        # Call au backend's launch() method directly with our custom task_id (key)
        # au will store the result in its store when done
        self.au_backend.launch(func, args, kwargs, task_id)

    def shutdown(self, wait: bool = True) -> None:
        """Shutdown the executor."""
        # au backends handle their own lifecycle
        if hasattr(self.au_backend, 'shutdown'):
            self.au_backend.shutdown(wait=wait)


def use_au_backend(
    backend: Optional['ComputationBackend'] = None,
    store: Optional['ComputationStore'] = None,
    **au_config_kwargs
) -> TaskConfig:
    """
    Create a qh TaskConfig that uses au backend and storage.

    This is the main bridge function that lets qh use au.

    Args:
        backend: au ComputationBackend (ThreadBackend, ProcessBackend, RQBackend, etc.)
                 If None, uses au's default from config
        store: au ComputationStore (FileSystemStore, etc.)
               If None, uses au's default from config
        **au_config_kwargs: Additional config passed to au

    Returns:
        TaskConfig configured to use au

    Example:
        >>> from au import ThreadBackend, FileSystemStore
        >>> from qh import mk_app
        >>> from qh.au_integration import use_au_backend
        >>>
        >>> # Use au with thread backend and filesystem storage
        >>> def slow_func(n: int) -> int:
        ...     import time
        ...     time.sleep(2)
        ...     return n * 2
        >>>
        >>> app = mk_app(
        ...     [slow_func],
        ...     async_funcs=['slow_func'],
        ...     async_config=use_au_backend(
        ...         backend=ThreadBackend(),
        ...         store=FileSystemStore('/tmp/qh_tasks')
        ...     )
        ... )

    Example with au's global config:
        >>> # Set AU environment variables:
        >>> # AU_BACKEND=redis
        >>> # AU_REDIS_URL=redis://localhost:6379
        >>> # AU_STORAGE=filesystem
        >>> # AU_STORAGE_PATH=/var/qh/tasks
        >>>
        >>> app = mk_app(
        ...     [slow_func],
        ...     async_funcs=['slow_func'],
        ...     async_config=use_au_backend()  # Uses au's config
        ... )
    """
    if not HAS_AU:
        raise ImportError(
            "au is required for this feature. Install with: pip install au\n"
            "For specific backends, use: pip install au[redis] or au[http]"
        )

    # Get backend and store (use au's defaults if not provided)
    if backend is None:
        from au.api import _get_default_backend
        backend = _get_default_backend()

    if store is None:
        from au.api import _get_default_store
        store = _get_default_store()

    # Create adapters
    task_store = AuTaskStore(store)
    task_executor = AuTaskExecutor(backend, store)

    # Return qh TaskConfig using au backend
    return TaskConfig(
        store=task_store,
        executor=task_executor,
        **au_config_kwargs
    )


# Convenience functions for common au backends

def use_au_thread_backend(
    storage_path: str = '/tmp/qh_au_tasks',
    ttl_seconds: int = 3600,
) -> TaskConfig:
    """Use au's ThreadBackend with filesystem storage."""
    if not HAS_AU:
        raise ImportError("au is required. Install with: pip install au")

    store = FileSystemStore(storage_path, ttl_seconds=ttl_seconds)
    backend = ThreadBackend(store)  # au backends need store
    return use_au_backend(backend=backend, store=store)


def use_au_process_backend(
    storage_path: str = '/tmp/qh_au_tasks',
    ttl_seconds: int = 3600,
) -> TaskConfig:
    """Use au's ProcessBackend for CPU-bound tasks."""
    if not HAS_AU:
        raise ImportError("au is required. Install with: pip install au")

    store = FileSystemStore(storage_path, ttl_seconds=ttl_seconds)
    backend = ProcessBackend(store)  # au backends need store
    return use_au_backend(backend=backend, store=store)


def use_au_redis_backend(
    redis_url: str = 'redis://localhost:6379',
    storage_path: str = '/tmp/qh_au_tasks',
    ttl_seconds: int = 3600,
) -> TaskConfig:
    """Use au's Redis/RQ backend for distributed tasks."""
    if not HAS_AU:
        raise ImportError("au is required. Install with: pip install au[redis]")

    try:
        from au.backends.rq_backend import RQBackend
    except ImportError:
        raise ImportError(
            "Redis backend requires: pip install au[redis]"
        )

    backend = RQBackend(redis_url=redis_url)
    store = FileSystemStore(storage_path, ttl_seconds=ttl_seconds)
    return use_au_backend(backend=backend, store=store)
