"""
Example: Using au with qh for async task processing.

This shows how qh's clean HTTP interface combines with au's powerful backends.
"""

import time
from qh import mk_app
from qh.testing import test_app

# Check if au is available
try:
    from qh.au_integration import (
        use_au_backend,
        use_au_thread_backend,
        use_au_process_backend,
    )
    from au import ThreadBackend, FileSystemStore
    HAS_AU = True
except ImportError:
    HAS_AU = False
    print("au not installed. Install with: pip install au")


# Define some functions
def slow_io_task(seconds: int) -> dict:
    """Simulate I/O-bound task."""
    time.sleep(seconds)
    return {"slept_for": seconds, "task_type": "io"}


def cpu_intensive_task(n: int) -> int:
    """Simulate CPU-bound task."""
    def fib(x):
        if x <= 1:
            return x
        return fib(x - 1) + fib(x - 2)
    return fib(n)


if __name__ == "__main__" and HAS_AU:
    print("=" * 70)
    print("Example 1: qh with au ThreadBackend")
    print("=" * 70)

    # Create app using au's thread backend
    app1 = mk_app(
        [slow_io_task],
        async_funcs=['slow_io_task'],
        async_config=use_au_thread_backend(
            storage_path='/tmp/qh_example_tasks',
            ttl_seconds=3600,
        )
    )

    print("\nApp created with au backend!")
    print("Testing...")

    with test_app(app1) as client:
        # Synchronous call
        print("\n1. Synchronous call (blocks):")
        response = client.post("/slow_io_task", json={"seconds": 1})
        print(f"   Result: {response.json()}")

        # Asynchronous call
        print("\n2. Asynchronous call (returns immediately):")
        response = client.post("/slow_io_task?async=true", json={"seconds": 2})
        task_data = response.json()
        print(f"   Task submitted: {task_data}")

        task_id = task_data["task_id"]

        # Check status
        print("\n3. Check status:")
        response = client.get(f"/tasks/{task_id}/status")
        print(f"   Status: {response.json()}")

        # Wait for result
        print("\n4. Wait for result:")
        response = client.get(f"/tasks/{task_id}/result?wait=true&timeout=5")
        print(f"   Result: {response.json()}")

    print("\n" + "=" * 70)
    print("Example 2: qh with au ProcessBackend (CPU-bound)")
    print("=" * 70)

    # Create app using au's process backend
    app2 = mk_app(
        [cpu_intensive_task],
        async_funcs=['cpu_intensive_task'],
        async_config=use_au_process_backend(
            storage_path='/tmp/qh_cpu_tasks'
        )
    )

    print("\nApp created with ProcessBackend for CPU-intensive tasks!")
    print("Testing...")

    with test_app(app2) as client:
        # Submit CPU-intensive task
        print("\n1. Submit CPU-intensive task:")
        response = client.post(
            "/cpu_intensive_task?async=true",
            json={"n": 30}
        )
        task_id = response.json()["task_id"]
        print(f"   Task ID: {task_id}")

        # Poll for completion
        print("\n2. Polling for completion...")
        for i in range(10):
            time.sleep(0.5)
            response = client.get(f"/tasks/{task_id}/status")
            status = response.json()["status"]
            print(f"   Attempt {i+1}: {status}")
            if status == "completed":
                break

        # Get result
        response = client.get(f"/tasks/{task_id}/result")
        print(f"\n3. Final result: {response.json()}")

    print("\n" + "=" * 70)
    print("Example 3: Both sync and async functions in same app")
    print("=" * 70)

    def quick_calc(x: int, y: int) -> int:
        """Fast function - always synchronous."""
        return x + y

    # Mix sync and async functions
    app3 = mk_app(
        [quick_calc, slow_io_task],
        async_funcs=['slow_io_task'],  # Only slow_io_task supports async
        async_config=use_au_thread_backend()
    )

    print("\nApp with mixed sync/async functions!")
    print("  - quick_calc: always synchronous")
    print("  - slow_io_task: supports ?async=true")

    with test_app(app3) as client:
        # Sync function
        response = client.post("/quick_calc", json={"x": 3, "y": 5})
        print(f"\nSync function result: {response.json()}")

        # Async function
        response = client.post("/slow_io_task?async=true", json={"seconds": 1})
        print(f"Async function task: {response.json()['task_id']}")

    print("\n" + "=" * 70)
    print("Example 4: Comparison - Built-in vs au Backend")
    print("=" * 70)

    # Built-in qh async
    from qh import TaskConfig, ThreadPoolTaskExecutor

    app_builtin = mk_app(
        [slow_io_task],
        async_funcs=['slow_io_task'],
        async_config=TaskConfig(
            executor=ThreadPoolTaskExecutor(),
            async_mode='query',
        )
    )

    # au backend
    app_au = mk_app(
        [slow_io_task],
        async_funcs=['slow_io_task'],
        async_config=use_au_thread_backend()
    )

    print("\nBoth apps have the same HTTP interface!")
    print("\nBuilt-in backend:")
    print("  - Good for: Development, single-machine deployment")
    print("  - Storage: In-memory (lost on restart)")
    print("  - Features: Basic task management")

    print("\nau backend:")
    print("  - Good for: Production, distributed systems")
    print("  - Storage: Filesystem (persistent), Redis, Supabase")
    print("  - Features: Retry policies, middleware, workflows")

    print("\n✨ The beauty: swap backends with one line!")

elif __name__ == "__main__":
    print("Please install au to run this example:")
    print("  pip install au")
    print("\nFor Redis backend:")
    print("  pip install au[redis]")
