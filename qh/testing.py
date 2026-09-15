"""Run a qh (or any FastAPI) app for a test: in-process, or on a real port.

Two ways to exercise an app. ``test_app`` (and ``run_app``, ``AppRunner``) wrap
FastAPI's ``TestClient`` so requests go straight to the app with no socket.
``serve_app`` and ``service_running`` start uvicorn in a daemon thread and
give you a base URL to hit with ``requests``; ``service_running`` can also
notice a service that is already up and leave it alone. ``quick_test`` is the
one-liner: build an app around one function, POST to it, return the JSON.

Similar tools elsewhere: ``meshed.tools.launch_webservice``,
``strand.taskrunning.utils.run_process``, and the service helpers in
``py2http``.

Main entry points:

- ``test_app``: ``with test_app(app) as client:`` for in-process requests
- ``quick_test``: call one function through HTTP and get its JSON back
- ``serve_app`` / ``service_running``: a live server on a port, for integration tests

>>> from qh import mk_app
>>> from qh.testing import quick_test
>>> def add(x: int, y: int) -> int:
...     return x + y
>>> quick_test(add, x=3, y=5)
8
"""

from typing import Optional, Any, Callable, Generator
from dataclasses import dataclass
import threading
import time
import requests
from contextlib import contextmanager
from fastapi import FastAPI
from fastapi.testclient import TestClient

__all__ = [
    "ServiceInfo",
    "service_running",
    "AppRunner",
    "run_app",
    "test_app",
    "serve_app",
    "quick_test",
    "app_runner",
    "test_client",
]


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
    host: str = "127.0.0.1",
    startup_wait: float = 2.0,
    readiness_check_interval: float = 0.2,
    readiness_timeout: float = 10.0,
    log_level: str = "error",
) -> Generator[ServiceInfo, None, None]:
    """Ensure an HTTP service is running for testing purposes.

    This context manager checks if a service is already running at the specified URL.
    If not running, it launches the service using one of the provided methods (app,
    launcher) and tears it down on exit. If the service was already running, it leaves
    it running on exit.

    Exactly one of ``url``, ``app``, or ``launcher`` must be provided.

    Note:
        Services are launched in daemon threads (not processes) to avoid
        serialization issues with FastAPI apps on macOS. A service this
        context manager launched is not stopped on exit: the thread ends
        with the process.

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
        ValueError: If none, or more than one, of ``url``, ``app`` and ``launcher`` is given.
        RuntimeError: If ``url`` alone was given and nothing answers there, or if a
            launched service does not answer within ``readiness_timeout`` seconds.

    Examples:
        Test a qh app (launches a server in a daemon thread):

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
    provided_args = sum([url is not None, app is not None, launcher is not None])
    if provided_args == 0:
        raise ValueError(
            "Must provide one of: url (for existing service), "
            "app (to serve), or launcher (custom startup)"
        )
    if provided_args > 1:
        raise ValueError("Cannot provide multiple service specifications")

    if url is None:
        service_url = f"http://{host}:{port}"
    else:
        service_url = url

    was_running = _is_service_running(service_url)
    thread = None
    server = None

    if not was_running:
        if url is not None and app is None and launcher is None:
            raise RuntimeError(
                f"Service not running at {service_url} and no launcher provided"
            )

        if launcher is not None:
            thread = threading.Thread(target=launcher, daemon=True)
            thread.start()
        elif app is not None:
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
        # Only tear down if we launched it. Daemon threads stop when main thread exits;
        # for proper cleanup in tests, we rely on the server finishing naturally.
        pass


class AppRunner:
    """
    Context manager for running a FastAPI app in test mode or with a real server.

    Supports both synchronous testing (using TestClient) and integration testing
    (using a real uvicorn server). With ``use_server=False`` (the default) the
    ``with`` block receives a ``TestClient``; with ``use_server=True`` it
    receives the base URL of a uvicorn server started in a daemon thread. On
    exit the TestClient reference is dropped; a real server is not stopped, its
    daemon thread ends with the process. ``run_app`` is the function form.

    Examples:
        Basic usage with TestClient:

        >>> from qh import mk_app
        >>> from qh.testing import AppRunner  # doctest: +SKIP
        >>> def add(x: int, y: int) -> int:  # doctest: +SKIP
        ...     return x + y
        >>> app = mk_app([add])  # doctest: +SKIP
        >>> with AppRunner(app) as client:  # doctest: +SKIP
        ...     response = client.post('/add', json={'x': 3, 'y': 5})
        ...     assert response.json() == 8

        With real server (integration testing):

        >>> with AppRunner(app, use_server=True, port=8001) as base_url:  # doctest: +SKIP
        ...     response = requests.post(f'{base_url}/add', json={'x': 3, 'y': 5})
        ...     assert response.json() == 8

        An exception inside the block propagates; ``__exit__`` still runs:

        >>> with AppRunner(app) as client:  # doctest: +SKIP
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
        Drop the TestClient, or mark the server as no longer tracked.

        Runs even if the block raised; never suppresses the exception. A real
        server (``use_server=True``) keeps running in its daemon thread.
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

        Raises:
            RuntimeError: If ``/docs`` does not answer within ``server_timeout`` seconds.
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
        """Forget the server thread; the daemon thread itself keeps running until the process exits."""
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

        >>> from qh import mk_app  # doctest: +SKIP
        >>> from qh.testing import run_app  # doctest: +SKIP
        >>> def add(x: int, y: int) -> int:  # doctest: +SKIP
        ...     return x + y
        >>> app = mk_app([add])  # doctest: +SKIP
        >>> # Quick testing with TestClient
        >>> with run_app(app) as client:  # doctest: +SKIP
        ...     result = client.post('/add', json={'x': 3, 'y': 5})
        ...     assert result.json() == 8
        >>> # Integration testing with real server
        >>> with run_app(app, use_server=True, port=8001) as url:  # doctest: +SKIP
        ...     result = requests.post(f'{url}/add', json={'x': 3, 'y': 5})
        ...     assert result.json() == 8
    """
    runner = AppRunner(app, use_server=use_server, **kwargs)
    with runner as client_or_url:
        yield client_or_url


@contextmanager
def test_app(app: FastAPI):
    """
    Call an app in-process through a ``TestClient``, no server, no port.

    The most common case, and the fastest: requests are dispatched straight
    to the ASGI app. Use ``serve_app`` when a real socket matters (another
    process, a browser, a generated client pointed at a URL).

    Args:
        app: FastAPI application

    Yields:
        TestClient instance

    Examples:

        >>> from qh import mk_app
        >>> from qh.testing import test_app
        >>> def hello(name: str = "World") -> str:
        ...     return f"Hello, {name}!"
        >>> app = mk_app([hello])
        >>> with test_app(app) as client:
        ...     client.post('/hello', json={'name': 'Alice'}).json()
        'Hello, Alice!'

        A missing required argument is a ``422``, as in FastAPI:

        >>> def add(x: int, y: int) -> int:
        ...     return x + y
        >>> with test_app(mk_app([add])) as client:
        ...     client.post('/add', json={'x': 3}).status_code
        422
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

        >>> from qh import mk_app  # doctest: +SKIP
        >>> from qh.testing import serve_app  # doctest: +SKIP
        >>> import requests  # doctest: +SKIP
        >>> def multiply(x: int, y: int) -> int:  # doctest: +SKIP
        ...     return x * y
        >>> app = mk_app([multiply])  # doctest: +SKIP
        >>> with serve_app(app, port=8001) as url:  # doctest: +SKIP
        ...     response = requests.post(f'{url}/multiply', json={'x': 4, 'y': 5})
        ...     assert response.json() == 20
    """
    with run_app(app, use_server=True, port=port, host=host) as base_url:
        yield base_url


def quick_test(func, **kwargs):
    """
    Call one function through HTTP and return the decoded JSON response.

    Builds ``mk_app([func])``, POSTs ``kwargs`` as the JSON body to
    ``/<func name>``, and returns ``response.json()``. Meant for a one-line
    smoke check of what a function looks like over HTTP.

    Args:
        func: Function to test
        **kwargs: Arguments to pass to the function (sent as the JSON body)

    Returns:
        The JSON-decoded response body, i.e. the function's return value after
        JSON round-tripping.

    Raises:
        httpx.HTTPStatusError: If the response status is 4xx or 5xx (for
            example a missing required argument, or an exception in
            ``func``); ``fastapi.testclient.TestClient`` is httpx-based, not
            requests-based.

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
        response = client.post(f"/{func.__name__}", json=kwargs)
        response.raise_for_status()
        return response.json()


# Tell pytest not to collect these as tests (they start with `test_` but are
# context managers / helpers, not test functions).
test_app.__test__ = False
quick_test.__test__ = False

# Aliases for convenience
app_runner = run_app  # Alias
test_client = test_app  # Alias
