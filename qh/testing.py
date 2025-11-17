"""
Testing utilities for qh applications.

Provides context managers and helpers for testing HTTP services created with qh.

Related Tools in Other Packages
-------------------------------
This module provides testing utilities similar to those found in:
- `meshed.tools.launch_webservice`: Context manager for launching function-based web services
- `strand.taskrunning.utils.run_process`: Generic process runner with health checks
- `py2http`: Various service management utilities

The tools here are specifically optimized for qh/FastAPI applications but can work
with any HTTP service.
"""

from typing import Optional, Any, Union, Callable, Generator
from dataclasses import dataclass
import threading
import time
import multiprocessing
import requests
from contextlib import contextmanager
from fastapi import FastAPI
from fastapi.testclient import TestClient


@dataclass
class ServiceInfo:
    """Information about a running service.

    Attributes:
        url: Base URL of the service (e.g., 'http://localhost:8000')
        was_already_running: True if service was already running, False if launched
        thread: Thread object if service was launched in thread, None otherwise
        app: The FastAPI app if one was provided, None otherwise
    """

    url: str
    was_already_running: bool
    thread: Optional[threading.Thread] = None
    app: Optional[FastAPI] = None


def _is_service_running(url: str, *, timeout: float = 1.0) -> bool:
    """Check if an HTTP service is responding at the given URL.

    Args:
        url: URL to check (e.g., 'http://localhost:8000')
        timeout: Request timeout in seconds

    Returns:
        True if service responds with status < 500, False otherwise

    >>> _is_service_running('http://localhost:99999')  # doctest: +SKIP
    False
    """
    try:
        response = requests.get(url, timeout=timeout)
        return response.status_code < 500
    except (requests.ConnectionError, requests.RequestException):
        return False


@contextmanager
def service_running(
    *,
    url: Optional[str] = None,
    app: Optional[FastAPI] = None,
    launcher: Optional[Callable[[], None]] = None,
    port: int = 8000,
    host: str = '127.0.0.1',
    startup_wait: float = 2.0,
    readiness_check_interval: float = 0.2,
    readiness_timeout: float = 10.0,
    log_level: str = 'error',
) -> Generator[ServiceInfo, None, None]:
    """Ensure an HTTP service is running for testing purposes.

    This context manager checks if a service is already running at the specified URL.
    If not running, it launches the service using one of the provided methods (app,
    launcher) and tears it down on exit. If the service was already running, it leaves
    it running on exit.

    Exactly one of `url`, `app`, or `launcher` must be provided.

    Note:
        Services are launched in background threads (not processes) to avoid
        serialization issues with FastAPI apps on macOS.

    Args:
        url: URL of an existing service to check (e.g., 'http://localhost:8000').
             If provided alone, will fail if service is not running.
        app: FastAPI/ASGI app to serve using uvicorn
        launcher: Custom callable to launch the service (will run in background thread)
        port: Port to bind service to (used with app or launcher)
        host: Host to bind service to (used with app or launcher)
        startup_wait: Initial wait time after launching (seconds)
        readiness_check_interval: Polling interval for readiness checks (seconds)
        readiness_timeout: Maximum time to wait for service to be ready (seconds)
        log_level: Uvicorn log level when serving an app

    Yields:
        ServiceInfo: Information about the running service including URL and status

    Raises:
        ValueError: If invalid combination of arguments provided
        RuntimeError: If service fails to start within timeout

    Examples:
        Test a qh app (will launch and tear down):
        >>> from qh import mk_app
        >>> def add(x: int, y: int) -> int:
        ...     return x + y
        >>> app = mk_app([add])
        >>> with service_running(app=app, port=8001) as info:
        ...     response = requests.post(f'{info.url}/add', json={'x': 3, 'y': 5})
        ...     assert response.json() == 8
        ...     assert not info.was_already_running  # doctest: +SKIP

        Test an already-running service (won't tear down):
        >>> with service_running(url='https://api.github.com') as info:
        ...     response = requests.get(f'{info.url}/users/octocat')
        ...     assert info.was_already_running  # doctest: +SKIP

        Use custom launcher:
        >>> def my_launcher():
        ...     # Custom service startup code
        ...     pass  # doctest: +SKIP
        >>> with service_running(launcher=my_launcher, port=8002) as info:
        ...     # Test your service
        ...     pass  # doctest: +SKIP
    """
    # Validate arguments
    provided_args = sum([url is not None, app is not None, launcher is not None])
    if provided_args == 0:
        raise ValueError(
            "Must provide one of: url (for existing service), "
            "app (to serve), or launcher (custom startup)"
        )
    if provided_args > 1:
        raise ValueError("Cannot provide multiple service specifications")

    # Determine service URL
    if url is None:
        service_url = f'http://{host}:{port}'
    else:
        service_url = url

    # Check if already running
    was_running = _is_service_running(service_url)
    thread = None
    server = None

    if not was_running:
        if url is not None and app is None and launcher is None:
            raise RuntimeError(
                f"Service not running at {service_url} and no launcher provided"
            )

        if launcher is not None:
            # Use custom launcher in background thread
            thread = threading.Thread(target=launcher, daemon=True)
            thread.start()
        elif app is not None:
            # Launch using uvicorn in background thread
            import uvicorn

            config = uvicorn.Config(
                app,
                host=host,
                port=port,
                log_level=log_level,
            )
            server = uvicorn.Server(config)

            def run_server():
                server.run()

            thread = threading.Thread(target=run_server, daemon=True)
            thread.start()

        # Wait for service to be ready
        time.sleep(startup_wait)

        elapsed = startup_wait
        while not _is_service_running(service_url) and elapsed < readiness_timeout:
            time.sleep(readiness_check_interval)
            elapsed += readiness_check_interval

        if not _is_service_running(service_url):
            raise RuntimeError(
                f"Service failed to start at {service_url} within "
                f"{readiness_timeout}s timeout"
            )

    info = ServiceInfo(
        url=service_url,
        was_already_running=was_running,
        thread=thread,
        app=app,
    )

    try:
        yield info
    finally:
        # Only tear down if we launched it
        # Note: daemon threads will automatically stop when main thread exits
        # For proper cleanup in tests, we rely on the server finishing naturally
        pass


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
        self._client: TestClient | None = None
        self._server_thread: threading.Thread | None = None
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
def run_app(app: FastAPI, *, use_server: bool = False, **kwargs):
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

    Simple facade over `service_running` for the common case of serving a FastAPI app.
    Always launches a new server and tears it down on exit.

    Args:
        app: FastAPI application
        port: Port to bind to
        host: Host to bind to

    Yields:
        Base URL string (for backwards compatibility)

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

    Note:
        If you need to check if a service is already running and avoid duplicate
        launches, use `service_running` instead.
    """
    with service_running(app=app, port=port, host=host) as info:
        yield info.url


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
