"""
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
"""

import uuid
import time
import threading
import traceback
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from dataclasses import dataclass, field, asdict
from typing import Any, Callable, Dict, Optional, Protocol, Union
from datetime import datetime
from enum import Enum


class TaskStatus(str, Enum):
    """Standard task status values."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class TaskInfo:
    """Information about a task's state."""
    task_id: str
    status: TaskStatus
    created_at: float
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    result: Any = None
    error: Optional[str] = None
    traceback: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        data = asdict(self)
        # Convert status enum to string
        data['status'] = self.status.value
        # Add computed fields
        if self.started_at:
            data['duration'] = (
                (self.completed_at or time.time()) - self.started_at
            )
        return data


class TaskStore(ABC):
    """Abstract interface for task storage backends."""

    @abstractmethod
    def create_task(self, task_id: str, func_name: str) -> TaskInfo:
        """Create a new task record."""
        pass

    @abstractmethod
    def get_task(self, task_id: str) -> Optional[TaskInfo]:
        """Retrieve task information."""
        pass

    @abstractmethod
    def update_task(self, task_info: TaskInfo) -> None:
        """Update task information."""
        pass

    @abstractmethod
    def delete_task(self, task_id: str) -> bool:
        """Delete a task. Returns True if deleted, False if not found."""
        pass

    @abstractmethod
    def list_tasks(self, limit: int = 100) -> list[TaskInfo]:
        """List recent tasks."""
        pass


class InMemoryTaskStore(TaskStore):
    """Simple in-memory task storage (not persistent, single-process only)."""

    def __init__(self, ttl: Optional[int] = None):
        """
        Initialize in-memory store.

        Args:
            ttl: Time-to-live in seconds for completed tasks (None = keep forever)
        """
        self._tasks: Dict[str, TaskInfo] = {}
        self._lock = threading.RLock()
        self.ttl = ttl

    def _cleanup_expired(self):
        """Remove expired tasks."""
        if not self.ttl:
            return

        now = time.time()
        expired = [
            task_id
            for task_id, info in self._tasks.items()
            if info.completed_at and (now - info.completed_at) > self.ttl
        ]
        for task_id in expired:
            del self._tasks[task_id]

    def create_task(self, task_id: str, func_name: str) -> TaskInfo:
        with self._lock:
            self._cleanup_expired()
            task_info = TaskInfo(
                task_id=task_id,
                status=TaskStatus.PENDING,
                created_at=time.time(),
            )
            self._tasks[task_id] = task_info
            return task_info

    def get_task(self, task_id: str) -> Optional[TaskInfo]:
        with self._lock:
            self._cleanup_expired()
            return self._tasks.get(task_id)

    def update_task(self, task_info: TaskInfo) -> None:
        with self._lock:
            self._tasks[task_info.task_id] = task_info

    def delete_task(self, task_id: str) -> bool:
        with self._lock:
            if task_id in self._tasks:
                del self._tasks[task_id]
                return True
            return False

    def list_tasks(self, limit: int = 100) -> list[TaskInfo]:
        with self._lock:
            self._cleanup_expired()
            # Return most recent tasks first
            sorted_tasks = sorted(
                self._tasks.values(),
                key=lambda t: t.created_at,
                reverse=True,
            )
            return sorted_tasks[:limit]


class TaskExecutor(ABC):
    """Abstract interface for task execution backends."""

    @abstractmethod
    def submit_task(
        self,
        task_id: str,
        func: Callable,
        args: tuple,
        kwargs: dict,
        callback: Callable[[str, Any, Optional[Exception]], None],
    ) -> None:
        """
        Submit a task for execution.

        Args:
            task_id: Unique task identifier
            func: Function to execute
            args: Positional arguments
            kwargs: Keyword arguments
            callback: Called when task completes with (task_id, result, error)
        """
        pass

    @abstractmethod
    def shutdown(self, wait: bool = True) -> None:
        """Shutdown the executor."""
        pass


class ThreadPoolTaskExecutor(TaskExecutor):
    """Execute tasks using a thread pool (good for I/O-bound tasks)."""

    def __init__(self, max_workers: Optional[int] = None):
        """
        Initialize thread pool executor.

        Args:
            max_workers: Maximum number of worker threads (None = CPU count * 5)
        """
        self._pool = ThreadPoolExecutor(max_workers=max_workers)

    def submit_task(
        self,
        task_id: str,
        func: Callable,
        args: tuple,
        kwargs: dict,
        callback: Callable[[str, Any, Optional[Exception]], None],
    ) -> None:
        def wrapper():
            try:
                result = func(*args, **kwargs)
                callback(task_id, result, None)
            except Exception as e:
                callback(task_id, None, e)

        self._pool.submit(wrapper)

    def shutdown(self, wait: bool = True) -> None:
        self._pool.shutdown(wait=wait)


class ProcessPoolTaskExecutor(TaskExecutor):
    """Execute tasks using a process pool (good for CPU-bound tasks)."""

    def __init__(self, max_workers: Optional[int] = None):
        """
        Initialize process pool executor.

        Args:
            max_workers: Maximum number of worker processes (None = CPU count)
        """
        self._pool = ProcessPoolExecutor(max_workers=max_workers)

    def submit_task(
        self,
        task_id: str,
        func: Callable,
        args: tuple,
        kwargs: dict,
        callback: Callable[[str, Any, Optional[Exception]], None],
    ) -> None:
        def wrapper():
            return func(*args, **kwargs)

        future = self._pool.submit(wrapper)

        def done_callback(fut):
            try:
                result = fut.result()
                callback(task_id, result, None)
            except Exception as e:
                callback(task_id, None, e)

        future.add_done_callback(done_callback)

    def shutdown(self, wait: bool = True) -> None:
        self._pool.shutdown(wait=wait)


@dataclass
class TaskConfig:
    """
    Configuration for async task processing.

    This is the explicit configuration. The convention is to use sane defaults.
    """

    # Storage backend for task state
    store: Optional[TaskStore] = None

    # Execution backend (thread pool, process pool, etc.)
    executor: Optional[TaskExecutor] = None

    # Time-to-live for completed tasks (seconds)
    ttl: int = 3600

    # How to determine if a request should be async
    # Options: 'query' (check ?async=true), 'header' (check X-Async: true), 'always'
    async_mode: str = 'query'

    # Query parameter name for async mode
    async_param: str = 'async'

    # Header name for async mode
    async_header: str = 'X-Async'

    # Whether to create task management endpoints (GET /tasks/{id}, etc.)
    create_task_endpoints: bool = True

    # Default executor type if not specified: 'thread' or 'process'
    default_executor: str = 'thread'

    def get_store(self) -> TaskStore:
        """Get or create the task store."""
        if self.store is None:
            self.store = InMemoryTaskStore(ttl=self.ttl)
        return self.store

    def get_executor(self) -> TaskExecutor:
        """Get or create the task executor."""
        if self.executor is None:
            if self.default_executor == 'process':
                self.executor = ProcessPoolTaskExecutor()
            else:
                self.executor = ThreadPoolTaskExecutor()
        return self.executor


class TaskManager:
    """
    Manages async task execution and state.

    This is the main coordinator between stores, executors, and HTTP handlers.
    """

    def __init__(self, config: Optional[TaskConfig] = None):
        """
        Initialize task manager.

        Args:
            config: Task configuration (uses defaults if None)
        """
        self.config = config or TaskConfig()
        self.store = self.config.get_store()
        self.executor = self.config.get_executor()

    def create_task(
        self,
        func: Callable,
        args: tuple = (),
        kwargs: Optional[dict] = None,
    ) -> str:
        """
        Create and submit a new task.

        Args:
            func: Function to execute asynchronously
            args: Positional arguments
            kwargs: Keyword arguments

        Returns:
            Task ID
        """
        kwargs = kwargs or {}
        task_id = str(uuid.uuid4())

        # Create task record
        task_info = self.store.create_task(task_id, func.__name__)

        # Update status to running and set started_at
        task_info = self.store.get_task(task_id)  # Get fresh copy
        task_info.status = TaskStatus.RUNNING
        task_info.started_at = time.time()
        self.store.update_task(task_info)

        # Submit for execution (after status is set to running)
        self.executor.submit_task(
            task_id,
            func,
            args,
            kwargs,
            self._task_callback,
        )

        return task_id

    def _task_callback(
        self, task_id: str, result: Any, error: Optional[Exception]
    ) -> None:
        """Called when a task completes."""
        task_info = self.store.get_task(task_id)
        if not task_info:
            return

        task_info.completed_at = time.time()

        if error:
            task_info.status = TaskStatus.FAILED
            task_info.error = str(error)
            task_info.traceback = "".join(
                traceback.format_exception(type(error), error, error.__traceback__)
            )
        else:
            task_info.status = TaskStatus.COMPLETED
            task_info.result = result

        self.store.update_task(task_info)

    def get_status(self, task_id: str) -> Optional[TaskInfo]:
        """Get task status and metadata."""
        return self.store.get_task(task_id)

    def get_result(
        self, task_id: str, wait: bool = False, timeout: Optional[float] = None
    ) -> Any:
        """
        Get task result.

        Args:
            task_id: Task identifier
            wait: Whether to block until task completes
            timeout: Maximum time to wait in seconds (None = wait forever)

        Returns:
            Task result if completed

        Raises:
            ValueError: If task not found or failed
            TimeoutError: If wait times out
        """
        if wait:
            start_time = time.time()
            while True:
                task_info = self.store.get_task(task_id)
                if not task_info:
                    raise ValueError(f"Task not found: {task_id}")

                if task_info.status == TaskStatus.COMPLETED:
                    return task_info.result
                elif task_info.status == TaskStatus.FAILED:
                    raise ValueError(f"Task failed: {task_info.error}")

                if timeout and (time.time() - start_time) > timeout:
                    raise TimeoutError(f"Task did not complete within {timeout}s")

                time.sleep(0.1)  # Poll every 100ms
        else:
            task_info = self.store.get_task(task_id)
            if not task_info:
                raise ValueError(f"Task not found: {task_id}")

            if task_info.status == TaskStatus.COMPLETED:
                return task_info.result
            elif task_info.status == TaskStatus.FAILED:
                raise ValueError(f"Task failed: {task_info.error}")
            else:
                raise ValueError(f"Task not yet completed: {task_info.status.value}")

    def cancel_task(self, task_id: str) -> bool:
        """
        Cancel a task (if possible).

        Note: Cancellation is best-effort and may not work for all executors.

        Returns:
            True if task was cancelled or deleted
        """
        # For now, just delete the task record
        # TODO: Implement proper cancellation for executors that support it
        return self.store.delete_task(task_id)

    def list_tasks(self, limit: int = 100) -> list[TaskInfo]:
        """List recent tasks."""
        return self.store.list_tasks(limit=limit)

    def shutdown(self) -> None:
        """Shutdown the task manager and its executor."""
        self.executor.shutdown(wait=True)


# Global registry of task managers (one per function)
_task_managers: Dict[str, TaskManager] = {}


def get_task_manager(func_name: str, config: Optional[TaskConfig] = None) -> TaskManager:
    """
    Get or create a task manager for a function.

    Args:
        func_name: Name of the function
        config: Task configuration (only used when creating new manager)

    Returns:
        TaskManager instance
    """
    if func_name not in _task_managers:
        _task_managers[func_name] = TaskManager(config)
    return _task_managers[func_name]


def should_run_async(
    request: Any,  # FastAPI Request
    config: TaskConfig,
) -> bool:
    """
    Determine if a request should be executed asynchronously.

    Args:
        request: FastAPI Request object
        config: Task configuration

    Returns:
        True if request should be async
    """
    if config.async_mode == 'always':
        return True

    if config.async_mode == 'query':
        # Check query parameter
        value = request.query_params.get(config.async_param, '').lower()
        return value in ('true', '1', 'yes')

    if config.async_mode == 'header':
        # Check header
        value = request.headers.get(config.async_header, '').lower()
        return value in ('true', '1', 'yes')

    return False
