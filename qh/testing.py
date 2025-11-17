"""
Testing utilities for qh applications.

Provides context managers and helpers for testing HTTP services created with qh.
"""

from typing import Optional, Any
import threading
import time
import requests
from contextlib import contextmanager
from fastapi import FastAPI
from fastapi.testclient import TestClient


class AppRunner:
    """
    Context manager for running a FastAPI app in test mode or with a real server.

    Supports both synchronous testing (using TestClient) and integration testing
    (using a real uvicorn server).

    Examples:
        Basic usage with TestClient:
        >>> from qh import mk_app
        >>> from qh.testing import AppRunner
        >>>
        >>> def add(x: int, y: int) -> int:
        ...     return x + y
        >>>
        >>> app = mk_app([add])
        >>> with AppRunner(app) as client:
        ...     response = client.post('/add', json={'x': 3, 'y': 5})
        ...     assert response.json() == 8

        With real server (integration testing):
        >>> with AppRunner(app, use_server=True, port=8001) as base_url:
        ...     response = requests.post(f'{base_url}/add', json={'x': 3, 'y': 5})
        ...     assert response.json() == 8

        Automatic cleanup on error:
        >>> with AppRunner(app) as client:
        ...     # Server automatically stops if exception occurs
        ...     raise ValueError("Test error")
    """

    def __init__(
        self,
        app: FastAPI,
        *,
        use_server: bool = False,
        host: str = "127.0.0.1",
        port: int = 8000,
        server_timeout: float = 2.0,
    ):
        """
        Initialize the app runner.

        Args:
            app: FastAPI application to run
            use_server: If True, runs real uvicorn server; if False, uses TestClient
            host: Host to bind server to (only used if use_server=True)
            port: Port to bind server to (only used if use_server=True)
            server_timeout: Seconds to wait for server startup
        """
        self.app = app
        self.use_server = use_server
        self.host = host
        self.port = port
        self.server_timeout = server_timeout
        self._client: Optional[TestClient] = None
        self._server_thread: Optional[threading.Thread] = None
        self._server_running = False

    def __enter__(self):
        """
        Start the app (either TestClient or real server).

        Returns:
            TestClient if use_server=False, base URL string if use_server=True
        """
        if self.use_server:
            return self._start_server()
        else:
            return self._start_test_client()

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Stop the app and clean up resources.

        Automatically called even if an exception occurs.
        """
        if self.use_server:
            self._stop_server()
        else:
            self._stop_test_client()

        # Don't suppress exceptions
        return False

    def _start_test_client(self) -> TestClient:
        """Start TestClient for synchronous testing."""
        self._client = TestClient(self.app)
        return self._client

    def _stop_test_client(self):
        """Stop TestClient and clean up."""
        if self._client:
            # TestClient cleanup is automatic, but we can explicitly close
            self._client = None

    def _start_server(self) -> str:
        """
        Start a real uvicorn server in a background thread.

        Returns:
            Base URL string (e.g., "http://127.0.0.1:8000")
        """
        import uvicorn

        # Create server config
        config = uvicorn.Config(
            self.app,
            host=self.host,
            port=self.port,
            log_level="error",  # Reduce noise during testing
        )
        server = uvicorn.Server(config)

        # Run server in background thread
        def run_server():
            server.run()

        self._server_thread = threading.Thread(target=run_server, daemon=True)
        self._server_running = True
        self._server_thread.start()

        # Wait for server to start
        base_url = f"http://{self.host}:{self.port}"
        start_time = time.time()
        while time.time() - start_time < self.server_timeout:
            try:
                response = requests.get(f"{base_url}/docs", timeout=0.5)
                if response.status_code in [200, 404]:  # Server is up
                    return base_url
            except (requests.ConnectionError, requests.Timeout):
                time.sleep(0.1)

        raise RuntimeError(
            f"Server failed to start within {self.server_timeout} seconds"
        )

    def _stop_server(self):
        """Stop the uvicorn server."""
        if self._server_running:
            # Server will stop when thread is terminated
            # (daemon thread will automatically stop when main thread exits)
            self._server_running = False
            self._server_thread = None


@contextmanager
def run_app(
    app: FastAPI,
    *,
    use_server: bool = False,
    **kwargs
):
    """
    Context manager for running a FastAPI app.

    A convenience wrapper around AppRunner.

    Args:
        app: FastAPI application
        use_server: If True, runs real server; if False, uses TestClient
        **kwargs: Additional arguments passed to AppRunner

    Yields:
        TestClient or base URL string

    Examples:
        >>> from qh import mk_app
        >>> from qh.testing import run_app
        >>>
        >>> def add(x: int, y: int) -> int:
        ...     return x + y
        >>>
        >>> app = mk_app([add])
        >>>
        >>> # Quick testing with TestClient
        >>> with run_app(app) as client:
        ...     result = client.post('/add', json={'x': 3, 'y': 5})
        ...     assert result.json() == 8
        >>>
        >>> # Integration testing with real server
        >>> with run_app(app, use_server=True, port=8001) as url:
        ...     result = requests.post(f'{url}/add', json={'x': 3, 'y': 5})
        ...     assert result.json() == 8
    """
    runner = AppRunner(app, use_server=use_server, **kwargs)
    with runner as client_or_url:
        yield client_or_url


@contextmanager
def test_app(app: FastAPI):
    """
    Simple context manager for testing with TestClient.

    Convenience wrapper for the most common case: testing with TestClient.

    Args:
        app: FastAPI application

    Yields:
        TestClient instance

    Examples:
        >>> from qh import mk_app
        >>> from qh.testing import test_app
        >>>
        >>> def hello(name: str = "World") -> str:
        ...     return f"Hello, {name}!"
        >>>
        >>> app = mk_app([hello])
        >>> with test_app(app) as client:
        ...     response = client.post('/hello', json={'name': 'Alice'})
        ...     assert response.json() == "Hello, Alice!"
    """
    with run_app(app, use_server=False) as client:
        yield client


@contextmanager
def serve_app(app: FastAPI, port: int = 8000, host: str = "127.0.0.1"):
    """
    Context manager for running app with real server.

    Convenience wrapper for integration testing with a real uvicorn server.

    Args:
        app: FastAPI application
        port: Port to bind to
        host: Host to bind to

    Yields:
        Base URL string

    Examples:
        >>> from qh import mk_app
        >>> from qh.testing import serve_app
        >>> import requests
        >>>
        >>> def multiply(x: int, y: int) -> int:
        ...     return x * y
        >>>
        >>> app = mk_app([multiply])
        >>> with serve_app(app, port=8001) as url:
        ...     response = requests.post(f'{url}/multiply', json={'x': 4, 'y': 5})
        ...     assert response.json() == 20
    """
    with run_app(app, use_server=True, port=port, host=host) as base_url:
        yield base_url


def quick_test(func, **kwargs):
    """
    Quick test helper for a single function.

    Creates an app, runs it with TestClient, and tests a single function call.

    Args:
        func: Function to test
        **kwargs: Arguments to pass to the function

    Returns:
        Response from calling the function

    Examples:
        >>> from qh.testing import quick_test
        >>>
        >>> def add(x: int, y: int) -> int:
        ...     return x + y
        >>>
        >>> result = quick_test(add, x=3, y=5)
        >>> assert result == 8
        >>>
        >>> def greet(name: str) -> str:
        ...     return f"Hello, {name}!"
        >>>
        >>> result = quick_test(greet, name="World")
        >>> assert result == "Hello, World!"
    """
    from qh import mk_app

    app = mk_app([func])
    with test_app(app) as client:
        response = client.post(f'/{func.__name__}', json=kwargs)
        response.raise_for_status()
        return response.json()


# Aliases for convenience
app_runner = run_app  # Alias
test_client = test_app  # Alias
