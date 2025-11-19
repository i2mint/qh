"""
Helper functions to create task management endpoints.

These endpoints provide standard HTTP interfaces for task status and results.
"""

from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

from qh.async_tasks import get_task_manager, TaskStatus


def add_task_endpoints(
    app: FastAPI,
    func_name: str,
    path_prefix: str = "/tasks",
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
    """

    @app.get(
        f"{path_prefix}/{{task_id}}/status",
        summary="Get task status",
        tags=["tasks"],
    )
    async def get_task_status(task_id: str):
        """Get the status of a task."""
        task_manager = get_task_manager(func_name)
        task_info = task_manager.get_status(task_id)

        if not task_info:
            raise HTTPException(status_code=404, detail="Task not found")

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
        wait: bool = False,
        timeout: Optional[float] = None,
    ):
        """
        Get the result of a completed task.

        Args:
            task_id: Task identifier
            wait: Whether to block until task completes
            timeout: Maximum time to wait in seconds
        """
        task_manager = get_task_manager(func_name)

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
                        "error": task_info.error,
                        "traceback": task_info.traceback,
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
    async def get_task_info(task_id: str):
        """Get complete information about a task."""
        task_manager = get_task_manager(func_name)
        task_info = task_manager.get_status(task_id)

        if not task_info:
            raise HTTPException(status_code=404, detail="Task not found")

        return task_info.to_dict()

    @app.delete(
        f"{path_prefix}/{{task_id}}",
        summary="Cancel or delete a task",
        tags=["tasks"],
    )
    async def delete_task(task_id: str):
        """Cancel (if running) or delete a task."""
        task_manager = get_task_manager(func_name)
        deleted = task_manager.cancel_task(task_id)

        if not deleted:
            raise HTTPException(status_code=404, detail="Task not found")

        return {"task_id": task_id, "status": "deleted"}


def add_global_task_endpoints(
    app: FastAPI,
    path_prefix: str = "/tasks",
) -> None:
    """
    Add global task management endpoints (cross all functions).

    Creates:
    - GET {path_prefix}/ - List all recent tasks

    Args:
        app: FastAPI application
        path_prefix: URL path prefix for task endpoints
    """

    @app.get(
        f"{path_prefix}/",
        summary="List all tasks",
        tags=["tasks"],
    )
    async def list_all_tasks(limit: int = 100):
        """List recent tasks across all functions."""
        from qh.async_tasks import _task_managers

        all_tasks = []
        for func_name, manager in _task_managers.items():
            tasks = manager.list_tasks(limit=limit)
            for task in tasks:
                task_dict = task.to_dict()
                task_dict["function"] = func_name
                all_tasks.append(task_dict)

        # Sort by creation time, most recent first
        all_tasks.sort(key=lambda t: t["created_at"], reverse=True)

        return {"tasks": all_tasks[:limit]}
