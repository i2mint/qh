"""
Helper functions to create task management endpoints.

These endpoints provide standard HTTP interfaces for task status and results.

What a client sees is deliberately narrow: never a task's traceback (it stays in
the task store and the server log), a failed task's error text only with
``expose_errors=True``, never ``_private`` attributes of a result, and, when a
``TaskConfig`` has a ``task_owner``, only the caller's own tasks (anyone else's
answer 404). The cross-function task listing (``add_global_task_endpoints``) is
opt-in.

``qh.mk_app`` uses ``add_app_task_endpoints``: one set of ``/tasks/...`` routes
for all of an app's async functions, each task resolved through the managers of
that app's own ``TaskConfig`` objects (never a process-wide, name-keyed registry).
"""

from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool

from qh.async_tasks import (
    get_task_manager,
    TaskConfig,
    TaskInfo,
    TaskManager,
    TaskStatus,
)
from qh.errors import DFLT_EXPOSE_ERRORS
from qh.types import public_jsonable

DFLT_TASKS_PATH_PREFIX = "/tasks"
DFLT_TASK_LIST_LIMIT = 100

# Fields of a TaskInfo never sent to a client
_SERVER_ONLY_TASK_FIELDS = ("traceback", "owner")
_HIDDEN_ERROR_TEXT = "Task failed (details are in the server log)"

# (manager, config) pairs that a task id may belong to
ManagerSources = Callable[[], Iterable[Tuple[TaskManager, Optional[TaskConfig]]]]


def task_info_for_client(
    task_info: TaskInfo, *, expose_errors: bool = DFLT_EXPOSE_ERRORS
) -> Dict[str, Any]:
    """The client-facing view of a task: ``TaskInfo.to_dict()`` without the
    traceback and owner, with the result's private attributes left out, and with
    the error text replaced unless ``expose_errors``.

    >>> import time
    >>> info = TaskInfo('t1', TaskStatus.FAILED, time.time(), error='/srv/db: denied',
    ...                 traceback='Traceback ...', owner='alice')
    >>> d = task_info_for_client(info)
    >>> 'traceback' in d, 'owner' in d, d['error'] == _HIDDEN_ERROR_TEXT
    (False, False, True)
    >>> task_info_for_client(info, expose_errors=True)['error']
    '/srv/db: denied'
    """
    data = task_info.to_dict()
    for field_name in _SERVER_ONLY_TASK_FIELDS:
        data.pop(field_name, None)
    data["result"] = public_jsonable(task_info.result)
    if data.get("error") is not None and not expose_errors:
        data["error"] = _HIDDEN_ERROR_TEXT
    return data


def _is_visible_to(task_info: TaskInfo, request: Request, task_config) -> bool:
    task_owner = getattr(task_config, "task_owner", None)
    if task_owner is None:
        return True
    return bool(task_info.owner) and task_info.owner == task_owner(request)


def _find_visible_task(
    task_id: str, request: Request, sources: ManagerSources
) -> Tuple[TaskManager, TaskInfo]:
    """The task's manager and info, if the caller may see it, else a 404.

    A task is visible only if EVERY config whose manager knows the task allows it
    (configs may share a store, and the strictest one wins).
    """
    found = None
    for manager, task_config in sources():
        task_info = manager.get_status(task_id)
        if task_info is None:
            continue
        if not _is_visible_to(task_info, request, task_config):
            found = None
            break
        found = found or (manager, task_info)
    if found is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return found


def _add_task_routes(
    app: FastAPI,
    sources: ManagerSources,
    *,
    path_prefix: str,
    expose_errors: bool,
) -> None:
    @app.get(
        f"{path_prefix}/{{task_id}}/status",
        summary="Get task status",
        tags=["tasks"],
    )
    async def get_task_status(task_id: str, request: Request):
        """Get the status of a task."""
        _, task_info = _find_visible_task(task_id, request, sources)

        return {
            "task_id": task_info.task_id,
            "status": task_info.status.value,
            "created_at": task_info.created_at,
            "started_at": task_info.started_at,
            "completed_at": task_info.completed_at,
        }

    @app.get(
        f"{path_prefix}/{{task_id}}/result",
        summary="Get task result",
        tags=["tasks"],
    )
    async def get_task_result(
        task_id: str,
        request: Request,
        wait: bool = False,
        timeout: Optional[float] = None,
    ):
        """
        Get the result of a completed task.

        Args:
            task_id: Task identifier
            wait: Whether to block until task completes
            timeout: Maximum time to wait in seconds

        Returns:
            A dict with ``task_id`` and ``status``, plus ``result`` when
            completed. A failed or still-pending/running task is returned as
            a ``JSONResponse`` (500 or 202) instead of raising.

        Raises:
            HTTPException: 404 if ``task_id`` is unknown (or not the caller's);
                408 if ``wait`` timed out.
        """
        task_manager, _ = _find_visible_task(task_id, request, sources)

        try:
            # in a worker thread: ``get_result`` polls with ``time.sleep``, which would
            # stall every other request on the event loop for as long as it waits
            result = await run_in_threadpool(
                task_manager.get_result, task_id, wait=wait, timeout=timeout
            )
            return {
                "task_id": task_id,
                "status": "completed",
                "result": public_jsonable(result),
            }
        except ValueError:
            # Task not found, failed, or not completed
            task_info = task_manager.get_status(task_id)
            if not task_info:
                raise HTTPException(status_code=404, detail="Task not found")

            if task_info.status == TaskStatus.FAILED:
                return JSONResponse(
                    status_code=500,
                    content={
                        "task_id": task_id,
                        "status": "failed",
                        "error": task_info_for_client(
                            task_info, expose_errors=expose_errors
                        )["error"],
                    },
                )
            else:
                # Still pending/running
                return JSONResponse(
                    status_code=202,
                    content={
                        "task_id": task_id,
                        "status": task_info.status.value,
                        "message": "Task not yet completed",
                    },
                )
        except TimeoutError:
            raise HTTPException(
                status_code=408, detail=f"Task did not complete within {timeout}s"
            )

    @app.get(
        f"{path_prefix}/{{task_id}}",
        summary="Get complete task info",
        tags=["tasks"],
    )
    async def get_task_info(task_id: str, request: Request):
        """Get information about a task (never its traceback)."""
        _, task_info = _find_visible_task(task_id, request, sources)
        return task_info_for_client(task_info, expose_errors=expose_errors)

    @app.delete(
        f"{path_prefix}/{{task_id}}",
        summary="Cancel or delete a task",
        tags=["tasks"],
    )
    async def delete_task(task_id: str, request: Request):
        """Cancel (if running) or delete a task."""
        task_manager, _ = _find_visible_task(task_id, request, sources)
        if not task_manager.cancel_task(task_id):
            raise HTTPException(status_code=404, detail="Task not found")
        return {"task_id": task_id, "status": "deleted"}


def _distinct_managers(
    task_configs: Dict[str, Optional[TaskConfig]],
) -> List[Tuple[TaskManager, TaskConfig, List[str]]]:
    """``(manager, config, func_names)`` per distinct config."""
    by_config: Dict[int, Tuple[TaskManager, TaskConfig, List[str]]] = {}
    for func_name, task_config in task_configs.items():
        if task_config is None:
            continue
        entry = by_config.setdefault(
            id(task_config), (task_config.get_manager(), task_config, [])
        )
        entry[2].append(func_name)
    return list(by_config.values())


def add_app_task_endpoints(
    app: FastAPI,
    task_configs: Dict[str, Optional[TaskConfig]],
    *,
    path_prefix: str = DFLT_TASKS_PATH_PREFIX,
    expose_errors: bool = DFLT_EXPOSE_ERRORS,
) -> None:
    """
    Add one set of task endpoints serving the tasks of all the given functions.

    Creates ``GET {path_prefix}/{task_id}/status``, ``.../result``,
    ``GET {path_prefix}/{task_id}`` and ``DELETE {path_prefix}/{task_id}``. A task
    is looked up in the managers of ``task_configs`` only, and is visible to a
    caller only if every ``task_owner`` among the configs that know the task
    allows it.

    Args:
        app: FastAPI application
        task_configs: ``{func_name: TaskConfig}`` of the app's async functions
        path_prefix: URL path prefix for task endpoints
        expose_errors: Whether a failed task's error text reaches the client
            (its traceback never does).
    """
    managers = _distinct_managers(task_configs)

    def sources():
        return ((manager, config) for manager, config, _ in managers)

    _add_task_routes(app, sources, path_prefix=path_prefix, expose_errors=expose_errors)


def add_task_endpoints(
    app: FastAPI,
    func_name: str,
    path_prefix: str = DFLT_TASKS_PATH_PREFIX,
    *,
    task_config: Optional[TaskConfig] = None,
    expose_errors: bool = DFLT_EXPOSE_ERRORS,
) -> None:
    """
    Add task management endpoints for a specific function.

    Creates the following endpoints:

    - GET {path_prefix}/{task_id}/status - Get task status
    - GET {path_prefix}/{task_id}/result - Get task result (waits if needed)
    - GET {path_prefix}/{task_id} - Get complete task info
    - DELETE {path_prefix}/{task_id} - Cancel/delete a task

    Args:
        app: FastAPI application
        func_name: Name of the function these tasks belong to
        path_prefix: URL path prefix for task endpoints
        task_config: The function's ``TaskConfig``: its manager holds the tasks
            and its ``task_owner`` (if any) restricts every endpoint to the
            task's creator. Without one, the function's manager is looked up by
            name in the process-wide registry (``get_task_manager``).
        expose_errors: Whether a failed task's error text reaches the client
            (its traceback never does).
    """

    def sources():
        if task_config is not None:
            return [(task_config.get_manager(), task_config)]
        return [(get_task_manager(func_name), None)]

    _add_task_routes(app, sources, path_prefix=path_prefix, expose_errors=expose_errors)


def add_global_task_endpoints(
    app: FastAPI,
    path_prefix: str = DFLT_TASKS_PATH_PREFIX,
    *,
    task_configs: Optional[Dict[str, Optional[TaskConfig]]] = None,
    expose_errors: bool = DFLT_EXPOSE_ERRORS,
) -> None:
    """
    Add global task management endpoints (cross all functions).

    Creates:

    - GET {path_prefix}/ - List all recent tasks

    ``qh.mk_app`` only adds this with ``global_task_endpoints=True``: it lists the
    tasks of every caller, except that a function whose ``TaskConfig`` has a
    ``task_owner`` only contributes the caller's own tasks.

    Args:
        app: FastAPI application
        path_prefix: URL path prefix for task endpoints
        task_configs: ``{func_name: TaskConfig}`` of the functions to list (with
            the ``task_owner`` each one enforces). Defaults to every manager of
            the process-wide registry (``get_task_manager``), with its own config.
        expose_errors: Whether failed tasks' error text is listed
    """

    def sources() -> List[Tuple[TaskManager, Optional[TaskConfig], List[str]]]:
        if task_configs is not None:
            return _distinct_managers(task_configs)
        from qh.async_tasks import _task_managers

        return [(m, m.config, [name]) for name, m in _task_managers.items()]

    @app.get(
        f"{path_prefix}/",
        summary="List all tasks",
        tags=["tasks"],
    )
    async def list_all_tasks(request: Request, limit: int = DFLT_TASK_LIST_LIMIT):
        """List recent tasks across all functions."""
        managers = sources()
        all_tasks = {}
        for manager, _, func_names in managers:
            for task in manager.list_tasks(limit=limit):
                if task.task_id in all_tasks:
                    continue
                if not all(
                    _is_visible_to(task, request, config)
                    for other, config, _ in managers
                    if other.get_status(task.task_id) is not None
                ):
                    continue
                task_dict = task_info_for_client(task, expose_errors=expose_errors)
                task_dict["function"] = func_names[0] if len(func_names) == 1 else None
                all_tasks[task.task_id] = task_dict

        # Sort by creation time, most recent first
        tasks = sorted(all_tasks.values(), key=lambda t: t["created_at"], reverse=True)

        return {"tasks": tasks[:limit]}
