"""
Example of async task processing with qh.

This demonstrates the boilerplate-minimal way to handle long-running operations.
"""

import time
from qh import mk_app, TaskConfig, ThreadPoolTaskExecutor, ProcessPoolTaskExecutor


# Define some functions (mix of sync and async)
def quick_add(x: int, y: int) -> int:
    """A fast operation that doesn't need async."""
    return x + y


def slow_multiply(x: int, y: int) -> int:
    """A slow operation that benefits from async."""
    time.sleep(5)  # Simulate expensive computation
    return x * y


def cpu_intensive_task(n: int) -> int:
    """A CPU-bound task that should use process pool."""
    # Compute fibonacci (inefficiently)
    def fib(x):
        if x <= 1:
            return x
        return fib(x - 1) + fib(x - 2)

    return fib(n)


async def async_fetch_data(url: str) -> dict:
    """An async function that can also be used as a task."""
    import asyncio
    await asyncio.sleep(2)  # Simulate network request
    return {"url": url, "status": "fetched"}


# Example 1: Minimal setup - just specify which functions should be async
print("Example 1: Minimal async setup")
print("=" * 60)

app1 = mk_app(
    [quick_add, slow_multiply],
    async_funcs=['slow_multiply'],  # Only slow_multiply supports async
)

print("Created app with async support for slow_multiply")
print("Usage:")
print("  POST /slow_multiply?x=5&y=10          -> Returns result immediately (blocks 5s)")
print("  POST /slow_multiply?x=5&y=10&async=true -> Returns task_id immediately")
print("  GET /tasks/{task_id}/status            -> Check task status")
print("  GET /tasks/{task_id}/result            -> Get result when ready")
print()


# Example 2: Custom configuration
print("Example 2: Custom async configuration")
print("=" * 60)

app2 = mk_app(
    [slow_multiply, cpu_intensive_task],
    async_funcs=['slow_multiply', 'cpu_intensive_task'],
    async_config={
        'slow_multiply': TaskConfig(
            executor=ThreadPoolTaskExecutor(max_workers=4),
            ttl=1800,  # Keep results for 30 minutes
        ),
        'cpu_intensive_task': TaskConfig(
            executor=ProcessPoolTaskExecutor(max_workers=2),
            ttl=3600,  # Keep results for 1 hour
        ),
    },
)

print("Created app with custom executors:")
print("  - slow_multiply uses thread pool (I/O-bound)")
print("  - cpu_intensive_task uses process pool (CPU-bound)")
print()


# Example 3: Always async mode
print("Example 3: Always async (no query param needed)")
print("=" * 60)

always_async_config = TaskConfig(
    async_mode='always',  # Every request is async
)

app3 = mk_app(
    [slow_multiply],
    async_funcs=['slow_multiply'],
    async_config=always_async_config,
)

print("Created app where slow_multiply is ALWAYS async")
print("  POST /slow_multiply?x=5&y=10  -> Always returns task_id")
print()


# Example 4: Header-based async mode
print("Example 4: Header-based async control")
print("=" * 60)

header_config = TaskConfig(
    async_mode='header',  # Check X-Async header
    async_header='X-Async-Task',  # Custom header name
)

app4 = mk_app(
    [slow_multiply],
    async_funcs=['slow_multiply'],
    async_config=header_config,
)

print("Created app with header-based async control")
print("  POST /slow_multiply with X-Async-Task: true  -> Returns task_id")
print()


# Example 5: Complete application with multiple functions
print("Example 5: Complete application")
print("=" * 60)

app5 = mk_app(
    [quick_add, slow_multiply, cpu_intensive_task, async_fetch_data],
    async_funcs=['slow_multiply', 'cpu_intensive_task', 'async_fetch_data'],
)

print("Created complete app with:")
print("  - quick_add: synchronous only")
print("  - slow_multiply: supports async")
print("  - cpu_intensive_task: supports async")
print("  - async_fetch_data: supports async (native async function)")
print()
print("Available endpoints:")
print("  POST /quick_add")
print("  POST /slow_multiply")
print("  POST /cpu_intensive_task")
print("  POST /async_fetch_data")
print("  GET /tasks/")
print("  GET /tasks/{task_id}")
print("  GET /tasks/{task_id}/status")
print("  GET /tasks/{task_id}/result")
print("  DELETE /tasks/{task_id}")
print()


# Example 6: Using the app programmatically
if __name__ == "__main__":
    print("Example 6: Running the app")
    print("=" * 60)

    from qh.testing import test_app

    # Create test client
    with test_app(app5) as client:
        print("\n1. Synchronous call to quick_add:")
        response = client.post("/quick_add", json={"x": 3, "y": 4})
        print(f"   Response: {response.json()}")

        print("\n2. Synchronous call to slow_multiply (blocks):")
        response = client.post("/slow_multiply", json={"x": 5, "y": 6})
        print(f"   Response: {response.json()}")

        print("\n3. Async call to slow_multiply:")
        response = client.post("/slow_multiply?async=true", json={"x": 7, "y": 8})
        task_data = response.json()
        print(f"   Task submitted: {task_data}")

        task_id = task_data["task_id"]

        print("\n4. Check task status:")
        response = client.get(f"/tasks/{task_id}/status")
        print(f"   Status: {response.json()}")

        print("\n5. Wait for result (blocking):")
        response = client.get(f"/tasks/{task_id}/result?wait=true&timeout=10")
        print(f"   Result: {response.json()}")

        print("\n6. List all tasks:")
        response = client.get("/tasks/")
        tasks = response.json()["tasks"]
        print(f"   Found {len(tasks)} tasks")
        for task in tasks[:3]:  # Show first 3
            print(f"   - {task['task_id']}: {task['status']}")
