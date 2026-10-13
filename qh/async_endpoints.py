"""
Helper functions to create task management endpoints.

These endpoints provide standard HTTP interfaces for task status and results.

What a client sees is deliberately narrow: never a task's traceback (it stays in
the task store and the server log), a failed task's error text only with
``expose_errors=True``, and, when the ``TaskConfig`` has a ``task_owner``, only
the caller's own tasks (anyone else's answer 404). The cross-function task
listing (``add_global_task_endpoints``) is opt-in.
"""

from typing import Any, Dict, Optional
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from qh.async_tasks import get_task_manager, TaskConfig, TaskInfo, TaskStatus
from qh.errors import DFLT_EXPOSE_ERRORS

# Fields of a TaskInfo never sent to a client
_SERVER_ONLY_TASK_FIELDS = ("traceback", "owner")
_HIDDEN_ERROR_TEXT = "Task failed (details are in the server log)"


def task_info_for_client(
    task_info: TaskInfo, *, expose_errors: bool = DFLT_EXPOSE_ERRORS
) -> Dict[str, Any]:
    """The client-facing view of a task: ``TaskInfo.to_dict()`` without the
    traceback and owner, and with the error text replaced unless ``expose_errors``.

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
    if data.get("error") is not None and not expose_errors:
        data["error"] = _HIDDEN_ERROR_TEXT
    return data


def _is_visible_to(task_info: TaskInfo, request: Request, task_config) -> bool:
    task_owner = getattr(task_config, "task_owner", None)
    if task_owner is None:
        return True
    return task_info.owner is not None and task_info.owner == task_owner(request)


def add_task_endpoints(
    app: FastAPI,
    func_name: str,
    path_prefix: str = "/tasks",
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
        task_config: The function's ``TaskConfig``; its ``task_owner`` (if any)
            restricts every endpoint to the task's creator.
        expose_errors: Whether a failed task's error text reaches the client
            (its traceback never does).
    """

    def get_visible_task(task_id: str, request: Request) -> TaskInfo:
        task_info = get_task_manager(func_name).get_status(task_id)
        if not task_info or not _is_visible_to(task_info, request, task_config):
            raise HTTPException(status_code=404, detail="Task not found")
        return task_info

    @app.get(
        f"{path_prefix}/{{task_id}}/status",
        summary="Get task status",
        tags=["tasks"],
    )
    async def get_task_status(task_id: str, request: Request):
        """Get the status of a task."""
        task_info = get_visible_task(task_id, request)

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
            HTTPException: 404 if ``task_id`` is unknown to this function's
                task manager; 408 if ``wait`` timed out.
        """
        task_manager = get_task_manager(func_name)
        get_visible_task(task_id, request)

        try:
            result = task_manager.get_result(task_id, wait=wait, timeout=timeout)
            return {"task_id": task_id, "status": "completed", "result": result}
        except ValueError as e:
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
        task_info = get_visible_task(task_id, request)
        return task_info_for_client(task_info, expose_errors=expose_errors)

    @app.delete(
        f"{path_prefix}/{{task_id}}",
        summary="Cancel or delete a task",
        tags=["tasks"],
    )
    async def delete_task(task_id: str, request: Request):
        """Cancel (if running) or delete a task."""
        get_visible_task(task_id, request)
        deleted = get_task_manager(func_name).cancel_task(task_id)

        if not deleted:
            raise HTTPException(status_code=404, detail="Task not found")

        return {"task_id": task_id, "status": "deleted"}


def add_global_task_endpoints(
    app: FastAPI,
    path_prefix: str = "/tasks",
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
            the ``task_owner`` each one enforces). Defaults to every registered
            task manager, with its own config.
        expose_errors: Whether failed tasks' error text is listed
    """

    @app.get(
        f"{path_prefix}/",
        summary="List all tasks",
        tags=["tasks"],
    )
    async def list_all_tasks(request: Request, limit: int = 100):
        """List recent tasks across all functions."""
        from qh.async_tasks import _task_managers

        if task_configs is None:
            configs = {name: m.config for name, m in _task_managers.items()}
        else:
            configs = task_configs
        all_tasks = []
        for func_name, task_config in configs.items():
            if func_name not in _task_managers:
                continue
            tasks = _task_managers[func_name].list_tasks(limit=limit)
            for task in tasks:
                if not _is_visible_to(task, request, task_config):
                    continue
                task_dict = task_info_for_client(task, expose_errors=expose_errors)
                task_dict["function"] = func_name
                all_tasks.append(task_dict)

        # Sort by creation time, most recent first
        all_tasks.sort(key=lambda t: t["created_at"], reverse=True)

        return {"tasks": all_tasks[:limit]}
