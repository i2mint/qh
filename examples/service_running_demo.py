"""
Demo of the service_running context manager for testing HTTP services.

This example shows how to use service_running to test qh applications
and external services, with automatic lifecycle management.
"""

import requests
from qh import mk_app, service_running


def add(x: int, y: int) -> int:
    """Add two numbers."""
    return x + y


def multiply(x: int, y: int) -> int:
    """Multiply two numbers."""
    return x * y


def demo_basic_usage():
    """Basic usage: test a qh app."""
    print("\n=== Basic Usage: Test a qh App ===")

    app = mk_app([add, multiply])

    with service_running(app=app, port=8001) as info:
        print(f"Service URL: {info.url}")
        print(f"Was already running: {info.was_already_running}")

        # Test the add endpoint
        response = requests.post(f'{info.url}/add', json={'x': 3, 'y': 5})
        print(f"3 + 5 = {response.json()}")

        # Test the multiply endpoint
        response = requests.post(f'{info.url}/multiply', json={'x': 4, 'y': 5})
        print(f"4 * 5 = {response.json()}")

    print("Service stopped (was launched by us)\n")


def demo_already_running():
    """Test behavior when service is already running."""
    print("\n=== Testing Already-Running Service ===")

    # This tests against GitHub's API (already running)
    with service_running(url='https://api.github.com') as info:
        print(f"Service URL: {info.url}")
        print(f"Was already running: {info.was_already_running}")

        response = requests.get(f'{info.url}/users/octocat')
        user_data = response.json()
        print(f"GitHub user: {user_data.get('name', 'N/A')}")

    print("Service still running (was already running)\n")


def demo_custom_launcher():
    """Demo with custom launcher function."""
    print("\n=== Custom Launcher (Advanced) ===")

    def my_launcher():
        """Custom service launcher."""
        import uvicorn

        app = mk_app([add])
        uvicorn.run(app, host='127.0.0.1', port=8002, log_level='error')

    with service_running(launcher=my_launcher, port=8002) as info:
        print(f"Custom service running at: {info.url}")
        response = requests.post(f'{info.url}/add', json={'x': 10, 'y': 20})
        print(f"10 + 20 = {response.json()}")

    print("Custom service stopped\n")


def demo_service_info():
    """Demo accessing ServiceInfo attributes."""
    print("\n=== ServiceInfo Attributes ===")

    app = mk_app([add])

    with service_running(app=app, port=8003) as info:
        print(f"URL: {info.url}")
        print(f"Was already running: {info.was_already_running}")
        print(f"Thread: {info.thread}")
        print(f"App: {type(info.app).__name__ if info.app else None}")

        if not info.was_already_running and info.thread:
            print(f"Thread alive: {info.thread.is_alive()}")

    print("Service stopped\n")


if __name__ == '__main__':
    demo_basic_usage()
    demo_already_running()
    # demo_custom_launcher()  # Uncomment to test custom launcher
    demo_service_info()

    print("✅ All demos completed successfully!")
