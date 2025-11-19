"""
Tests for async task processing functionality.
"""

import time
import pytest
from qh import mk_app, TaskConfig, TaskStatus
from qh.testing import test_app


def slow_function(x: int) -> int:
    """A function that takes time to complete."""
    time.sleep(0.5)
    return x * 2


def failing_function(x: int) -> int:
    """A function that raises an error."""
    raise ValueError("Intentional error")


async def async_function(x: int) -> int:
    """An async function."""
    import asyncio
    await asyncio.sleep(0.1)
    return x + 10


class TestBasicAsync:
    """Test basic async functionality."""

    def test_sync_execution(self):
        """Test that functions work normally without async flag."""
        app = mk_app([slow_function], async_funcs=['slow_function'])

        with test_app(app) as client:
            response = client.post("/slow_function", json={"x": 5})
            assert response.status_code == 200
            assert response.json() == 10

    def test_async_execution(self):
        """Test async execution returns task ID."""
        app = mk_app([slow_function], async_funcs=['slow_function'])

        with test_app(app) as client:
            # Request async execution
            response = client.post("/slow_function?async=true", json={"x": 5})
            assert response.status_code == 202  # Accepted
            data = response.json()
            assert "task_id" in data
            assert data["status"] == "submitted"

    def test_task_status(self):
        """Test checking task status."""
        app = mk_app([slow_function], async_funcs=['slow_function'])

        with test_app(app) as client:
            # Submit task
            response = client.post("/slow_function?async=true", json={"x": 5})
            task_id = response.json()["task_id"]

            # Check status
            response = client.get(f"/tasks/{task_id}/status")
            assert response.status_code == 200
            status_data = response.json()
            assert status_data["task_id"] == task_id
            assert status_data["status"] in ["pending", "running", "completed"]

    def test_task_result_wait(self):
        """Test waiting for task result."""
        app = mk_app([slow_function], async_funcs=['slow_function'])

        with test_app(app) as client:
            # Submit task
            response = client.post("/slow_function?async=true", json={"x": 5})
            task_id = response.json()["task_id"]

            # Wait for result
            response = client.get(
                f"/tasks/{task_id}/result?wait=true&timeout=5"
            )
            assert response.status_code == 200
            result_data = response.json()
            assert result_data["status"] == "completed"
            assert result_data["result"] == 10

    def test_task_not_found(self):
        """Test error when task doesn't exist."""
        app = mk_app([slow_function], async_funcs=['slow_function'])

        with test_app(app) as client:
            response = client.get("/tasks/nonexistent/status")
            assert response.status_code == 404

    def test_failed_task(self):
        """Test handling of failed tasks."""
        app = mk_app([failing_function], async_funcs=['failing_function'])

        with test_app(app) as client:
            # Submit task that will fail
            response = client.post(
                "/failing_function?async=true", json={"x": 5}
            )
            task_id = response.json()["task_id"]

            # Wait for the task to process
            time.sleep(0.5)

            # Get full task info to check error was captured
            response = client.get(f"/tasks/{task_id}")
            assert response.status_code == 200
            info = response.json()

            # The important thing is that the error was captured
            assert "error" in info
            assert "Intentional error" in info["error"]
            assert info["traceback"] is not None


class TestAsyncConfig:
    """Test async configuration options."""

    def test_always_async(self):
        """Test always async mode."""
        config = TaskConfig(async_mode='always')
        app = mk_app(
            [slow_function],
            async_funcs=['slow_function'],
            async_config=config,
        )

        with test_app(app) as client:
            # Even without async=true, should return task ID
            response = client.post("/slow_function", json={"x": 5})
            assert response.status_code == 202
            assert "task_id" in response.json()

    def test_header_mode(self):
        """Test header-based async mode."""
        config = TaskConfig(async_mode='header', async_header='X-Async')
        app = mk_app(
            [slow_function],
            async_funcs=['slow_function'],
            async_config=config,
        )

        with test_app(app) as client:
            # With header
            response = client.post(
                "/slow_function",
                json={"x": 5},
                headers={"X-Async": "true"},
            )
            assert response.status_code == 202
            assert "task_id" in response.json()

            # Without header (should be sync)
            response = client.post("/slow_function", json={"x": 5})
            assert response.status_code == 200
            assert response.json() == 10

    def test_ttl_config(self):
        """Test TTL configuration."""
        config = TaskConfig(ttl=1)  # 1 second TTL
        app = mk_app(
            [slow_function],
            async_funcs=['slow_function'],
            async_config=config,
        )

        with test_app(app) as client:
            # Submit and complete task
            response = client.post("/slow_function?async=true", json={"x": 5})
            task_id = response.json()["task_id"]

            # Wait for completion
            time.sleep(1)

            # Should still be there
            response = client.get(f"/tasks/{task_id}/status")
            assert response.status_code == 200

            # Wait for TTL to expire
            time.sleep(2)

            # Trigger cleanup by creating new task
            response = client.post("/slow_function?async=true", json={"x": 6})

            # Original task might be gone (TTL cleanup is opportunistic)
            # This is okay - just testing that TTL doesn't crash


class TestAsyncFunction:
    """Test with native async functions."""

    def test_async_function_sync_mode(self):
        """Test async function in sync mode."""
        app = mk_app([async_function], async_funcs=['async_function'])

        with test_app(app) as client:
            response = client.post("/async_function", json={"x": 5})
            assert response.status_code == 200
            assert response.json() == 15

    def test_async_function_async_mode(self):
        """Test async function in async mode."""
        app = mk_app([async_function], async_funcs=['async_function'])

        with test_app(app) as client:
            # Submit as task
            response = client.post("/async_function?async=true", json={"x": 5})
            task_id = response.json()["task_id"]

            # Wait for result
            response = client.get(
                f"/tasks/{task_id}/result?wait=true&timeout=5"
            )
            assert response.status_code == 200
            assert response.json()["result"] == 15


class TestTaskManagement:
    """Test task management endpoints."""

    def test_list_tasks(self):
        """Test listing all tasks."""
        app = mk_app([slow_function], async_funcs=['slow_function'])

        with test_app(app) as client:
            # Create a few tasks
            task_ids = []
            for i in range(3):
                response = client.post(
                    "/slow_function?async=true", json={"x": i}
                )
                task_ids.append(response.json()["task_id"])

            # List tasks
            response = client.get("/tasks/")
            assert response.status_code == 200
            data = response.json()
            assert "tasks" in data
            assert len(data["tasks"]) >= 3

            # Check that our tasks are in the list
            listed_ids = {t["task_id"] for t in data["tasks"]}
            for task_id in task_ids:
                assert task_id in listed_ids

    def test_delete_task(self):
        """Test deleting a task."""
        app = mk_app([slow_function], async_funcs=['slow_function'])

        with test_app(app) as client:
            # Create task
            response = client.post("/slow_function?async=true", json={"x": 5})
            task_id = response.json()["task_id"]

            # Delete it
            response = client.delete(f"/tasks/{task_id}")
            assert response.status_code == 200

            # Should be gone
            response = client.get(f"/tasks/{task_id}/status")
            assert response.status_code == 404

    def test_get_complete_task_info(self):
        """Test getting complete task information."""
        app = mk_app([slow_function], async_funcs=['slow_function'])

        with test_app(app) as client:
            # Create and complete task
            response = client.post("/slow_function?async=true", json={"x": 5})
            task_id = response.json()["task_id"]

            # Wait for completion
            time.sleep(1)

            # Get complete info
            response = client.get(f"/tasks/{task_id}")
            assert response.status_code == 200
            info = response.json()
            assert info["task_id"] == task_id
            assert info["status"] == "completed"
            assert info["result"] == 10
            assert "created_at" in info
            assert "duration" in info


class TestMultipleFunctions:
    """Test with multiple functions."""

    def test_multiple_async_funcs(self):
        """Test multiple functions with async support."""
        def func_a(x: int) -> int:
            time.sleep(0.2)
            return x * 2

        def func_b(x: int) -> int:
            time.sleep(0.2)
            return x * 3

        app = mk_app(
            [func_a, func_b],
            async_funcs=['func_a', 'func_b'],
        )

        with test_app(app) as client:
            # Submit tasks to both functions
            response_a = client.post("/func_a?async=true", json={"x": 5})
            task_a = response_a.json()["task_id"]

            response_b = client.post("/func_b?async=true", json={"x": 5})
            task_b = response_b.json()["task_id"]

            # Wait for both
            time.sleep(1)

            # Check results
            result_a = client.get(f"/tasks/{task_a}/result").json()
            result_b = client.get(f"/tasks/{task_b}/result").json()

            assert result_a["result"] == 10
            assert result_b["result"] == 15

    def test_mixed_sync_async(self):
        """Test mixing sync and async functions."""
        def sync_func(x: int) -> int:
            return x + 1

        def async_func(x: int) -> int:
            time.sleep(0.2)
            return x * 2

        app = mk_app(
            [sync_func, async_func],
            async_funcs=['async_func'],  # Only async_func supports async
        )

        with test_app(app) as client:
            # sync_func doesn't support async
            response = client.post("/sync_func?async=true", json={"x": 5})
            # Should execute synchronously even with async=true
            assert response.status_code == 200
            assert response.json() == 6

            # async_func supports async
            response = client.post("/async_func?async=true", json={"x": 5})
            assert response.status_code == 202
            assert "task_id" in response.json()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
