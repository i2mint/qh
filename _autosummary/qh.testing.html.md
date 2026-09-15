# qh.testing

Run a qh (or any FastAPI) app for a test: in-process, or on a real port.

Two ways to exercise an app. `test_app` (and `run_app`, `AppRunner`) wrap
FastAPI’s `TestClient` so requests go straight to the app with no socket.
`serve_app` and `service_running` start uvicorn in a daemon thread and
give you a base URL to hit with `requests`; `service_running` can also
notice a service that is already up and leave it alone. `quick_test` is the
one-liner: build an app around one function, POST to it, return the JSON.

Similar tools elsewhere: `meshed.tools.launch_webservice`,
`strand.taskrunning.utils.run_process`, and the service helpers in
`py2http`.

Main entry points:

- `test_app`: `with test_app(app) as client:` for in-process requests
- `quick_test`: call one function through HTTP and get its JSON back
- `serve_app` / `service_running`: a live server on a port, for integration tests

```pycon
>>> from qh import mk_app
>>> from qh.testing import quick_test
>>> def add(x: int, y: int) -> int:
...     return x + y
>>> quick_test(add, x=3, y=5)
8
```

### Functions

| [`service_running`](#qh.testing.service_running)(\*[, url, app, launcher, ...])   | Ensure an HTTP service is running for testing purposes.              |
|---------------------------------------------------------------------------------------------------|----------------------------------------------------------------------|
| [`run_app`](#qh.testing.run_app)(app, \*[, use_server])                   | Context manager for running a FastAPI app.                           |
| [`test_app`](#qh.testing.test_app)(app)                                    | Call an app in-process through a `TestClient`, no server, no port.   |
| [`serve_app`](#qh.testing.serve_app)(app[, port, host])                     | Context manager for running app with real server.                    |
| [`quick_test`](#qh.testing.quick_test)(func, \*\*kwargs)                     | Call one function through HTTP and return the decoded JSON response. |
| [`app_runner`](#qh.testing.app_runner)(app, \*[, use_server])                | Context manager for running a FastAPI app.                           |
| [`test_client`](#qh.testing.test_client)(app)                                 | Call an app in-process through a `TestClient`, no server, no port.   |

### Classes

| [`ServiceInfo`](#qh.testing.ServiceInfo)(url, was_already_running[, ...])      | Information about a running service.                                          |
|----------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------|
| [`AppRunner`](#qh.testing.AppRunner)(app, \*[, use_server, host, port, ...]) | Context manager for running a FastAPI app in test mode or with a real server. |

### *class* qh.testing.AppRunner(app, , use_server=False, host='127.0.0.1', port=8000, server_timeout=2.0)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

Context manager for running a FastAPI app in test mode or with a real server.

Supports both synchronous testing (using TestClient) and integration testing
(using a real uvicorn server). With `use_server=False` (the default) the
`with` block receives a `TestClient`; with `use_server=True` it
receives the base URL of a uvicorn server started in a daemon thread. On
exit the TestClient reference is dropped; a real server is not stopped, its
daemon thread ends with the process. `run_app` is the function form.

### Examples

Basic usage with TestClient:

```pycon
>>> from qh import mk_app
>>> from qh.testing import AppRunner
>>> def add(x: int, y: int) -> int:
...     return x + y
>>> app = mk_app([add])
>>> with AppRunner(app) as client:
...     response = client.post('/add', json={'x': 3, 'y': 5})
...     assert response.json() == 8
```

With real server (integration testing):

```pycon
>>> with AppRunner(app, use_server=True, port=8001) as base_url:
...     response = requests.post(f'{base_url}/add', json={'x': 3, 'y': 5})
...     assert response.json() == 8
```

An exception inside the block propagates; `__exit__` still runs:

```pycon
>>> with AppRunner(app) as client:
...     raise ValueError("Test error")
```

### *class* qh.testing.ServiceInfo(url, was_already_running, thread=None, app=None)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

Information about a running service.

#### url

Base URL of the service (e.g., ‘[http://localhost:8000](http://localhost:8000)’)

#### was_already_running

True if service was already running, False if launched

#### thread

Thread object if service was launched in thread, None otherwise

#### app

The FastAPI app if one was provided, None otherwise

### qh.testing.app_runner(app, , use_server=False, \*\*kwargs)

Context manager for running a FastAPI app.

A convenience wrapper around AppRunner.

* **Parameters:**
  * **app** (`FastAPI`) – FastAPI application
  * **use_server** ([`bool`](https://docs.python.org/3/builtins/functions.html#bool)) – If True, runs real server; if False, uses TestClient
  * **\*\*kwargs** – Additional arguments passed to AppRunner
* **Yields:**
  TestClient or base URL string
* **Return type:**
  [*Generator*](https://docs.python.org/3/library/typing.html#typing.Generator)[*TestClient* | [*str*](https://docs.python.org/3/builtins/stdtypes.html#str), *None*, *None*]

### Examples

```pycon
>>> from qh import mk_app
>>> from qh.testing import run_app
>>> def add(x: int, y: int) -> int:
...     return x + y
>>> app = mk_app([add])
>>> # Quick testing with TestClient
>>> with run_app(app) as client:
...     result = client.post('/add', json={'x': 3, 'y': 5})
...     assert result.json() == 8
>>> # Integration testing with real server
>>> with run_app(app, use_server=True, port=8001) as url:
...     result = requests.post(f'{url}/add', json={'x': 3, 'y': 5})
...     assert result.json() == 8
```

### qh.testing.quick_test(func, \*\*kwargs)

Call one function through HTTP and return the decoded JSON response.

Builds `mk_app([func])`, POSTs `kwargs` as the JSON body to
`/<func name>`, and returns `response.json()`. Meant for a one-line
smoke check of what a function looks like over HTTP.

* **Parameters:**
  * **func** – Function to test
  * **\*\*kwargs** – Arguments to pass to the function (sent as the JSON body)
* **Returns:**
  The JSON-decoded response body, i.e. the function’s return value after
  JSON round-tripping.
* **Raises:**
  **httpx.HTTPStatusError** – If the response status is 4xx or 5xx (for
      example a missing required argument, or an exception in
      `func`); `fastapi.testclient.TestClient` is httpx-based, not
      requests-based.

### Examples

```pycon
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
```

### qh.testing.run_app(app, , use_server=False, \*\*kwargs)

Context manager for running a FastAPI app.

A convenience wrapper around AppRunner.

* **Parameters:**
  * **app** (`FastAPI`) – FastAPI application
  * **use_server** ([`bool`](https://docs.python.org/3/builtins/functions.html#bool)) – If True, runs real server; if False, uses TestClient
  * **\*\*kwargs** – Additional arguments passed to AppRunner
* **Yields:**
  TestClient or base URL string
* **Return type:**
  [*Generator*](https://docs.python.org/3/library/typing.html#typing.Generator)[*TestClient* | [*str*](https://docs.python.org/3/builtins/stdtypes.html#str), *None*, *None*]

### Examples

```pycon
>>> from qh import mk_app
>>> from qh.testing import run_app
>>> def add(x: int, y: int) -> int:
...     return x + y
>>> app = mk_app([add])
>>> # Quick testing with TestClient
>>> with run_app(app) as client:
...     result = client.post('/add', json={'x': 3, 'y': 5})
...     assert result.json() == 8
>>> # Integration testing with real server
>>> with run_app(app, use_server=True, port=8001) as url:
...     result = requests.post(f'{url}/add', json={'x': 3, 'y': 5})
...     assert result.json() == 8
```

### qh.testing.serve_app(app, port=8000, host='127.0.0.1')

Context manager for running app with real server.

Convenience wrapper for integration testing with a real uvicorn server.

* **Parameters:**
  * **app** (`FastAPI`) – FastAPI application
  * **port** ([`int`](https://docs.python.org/3/builtins/functions.html#int)) – Port to bind to
  * **host** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – Host to bind to
* **Yields:**
  Base URL string
* **Return type:**
  [*Generator*](https://docs.python.org/3/library/typing.html#typing.Generator)[[*str*](https://docs.python.org/3/builtins/stdtypes.html#str), *None*, *None*]

### Examples

```pycon
>>> from qh import mk_app
>>> from qh.testing import serve_app
>>> import requests
>>> def multiply(x: int, y: int) -> int:
...     return x * y
>>> app = mk_app([multiply])
>>> with serve_app(app, port=8001) as url:
...     response = requests.post(f'{url}/multiply', json={'x': 4, 'y': 5})
...     assert response.json() == 20
```

### qh.testing.service_running(, url=None, app=None, launcher=None, port=8000, host='127.0.0.1', startup_wait=2.0, readiness_check_interval=0.2, readiness_timeout=10.0, log_level='error')

Ensure an HTTP service is running for testing purposes.

This context manager checks if a service is already running at the specified URL.
If not running, it launches the service using one of the provided methods (app,
launcher). Either way, it leaves the service running on exit – see the Note below.

Exactly one of `url`, `app`, or `launcher` must be provided.

#### NOTE
Services are launched in daemon threads (not processes) to avoid
serialization issues with FastAPI apps on macOS. A service this
context manager launched is not stopped on exit: the thread ends
with the process.

* **Parameters:**
  * **url** ([`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]) – URL of an existing service to check (e.g., ‘[http://localhost:8000](http://localhost:8000)’).
    If provided alone, will fail if service is not running.
  * **app** ([`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[`FastAPI`]) – FastAPI/ASGI app to serve using uvicorn
  * **launcher** ([`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`Callable`](https://docs.python.org/3/library/typing.html#typing.Callable)[[], [`None`](https://docs.python.org/3/builtins/constants.html#None)]]) – Custom callable to launch the service (will run in background thread)
  * **port** ([`int`](https://docs.python.org/3/builtins/functions.html#int)) – Port to bind service to (used with app or launcher)
  * **host** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – Host to bind service to (used with app or launcher)
  * **startup_wait** ([`float`](https://docs.python.org/3/builtins/functions.html#float)) – Initial wait time after launching (seconds)
  * **readiness_check_interval** ([`float`](https://docs.python.org/3/builtins/functions.html#float)) – Polling interval for readiness checks (seconds)
  * **readiness_timeout** ([`float`](https://docs.python.org/3/builtins/functions.html#float)) – Maximum time to wait for service to be ready (seconds)
  * **log_level** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – Uvicorn log level when serving an app
* **Yields:**
  *ServiceInfo* – Information about the running service including URL and status
* **Raises:**
  * [**ValueError**](https://docs.python.org/3/builtins/exceptions.html#ValueError) – If none, or more than one, of `url`, `app` and `launcher` is given.
  * [**RuntimeError**](https://docs.python.org/3/builtins/exceptions.html#RuntimeError) – If `url` alone was given and nothing answers there, or if a
        launched service does not answer within `readiness_timeout` seconds.
* **Return type:**
  [*Generator*](https://docs.python.org/3/library/typing.html#typing.Generator)[[*ServiceInfo*](#qh.testing.ServiceInfo), *None*, *None*]

### Examples

Test a qh app (launches a server in a daemon thread):

```pycon
>>> from qh import mk_app
>>> def add(x: int, y: int) -> int:
...     return x + y
>>> app = mk_app([add])
>>> with service_running(app=app, port=8001) as info:
...     response = requests.post(f'{info.url}/add', json={'x': 3, 'y': 5})
...     assert response.json() == 8
...     assert not info.was_already_running
```

Test an already-running service (won’t tear down):

```pycon
>>> with service_running(url='https://api.github.com') as info:
...     response = requests.get(f'{info.url}/users/octocat')
...     assert info.was_already_running
```

Use custom launcher:

```pycon
>>> def my_launcher():
...     # Custom service startup code
...     pass
>>> with service_running(launcher=my_launcher, port=8002) as info:
...     # Test your service
...     pass
```

### qh.testing.test_app(app)

Call an app in-process through a `TestClient`, no server, no port.

The most common case, and the fastest: requests are dispatched straight
to the ASGI app. Use `serve_app` when a real socket matters (another
process, a browser, a generated client pointed at a URL).

* **Parameters:**
  **app** (`FastAPI`) – FastAPI application
* **Yields:**
  TestClient instance
* **Return type:**
  [*Generator*](https://docs.python.org/3/library/typing.html#typing.Generator)[*TestClient*, *None*, *None*]

### Examples

```pycon
>>> from qh import mk_app
>>> from qh.testing import test_app
>>> def hello(name: str = "World") -> str:
...     return f"Hello, {name}!"
>>> app = mk_app([hello])
>>> with test_app(app) as client:
...     client.post('/hello', json={'name': 'Alice'}).json()
'Hello, Alice!'
```

A missing required argument is a `422`, as in FastAPI:

```pycon
>>> def add(x: int, y: int) -> int:
...     return x + y
>>> with test_app(mk_app([add])) as client:
...     client.post('/add', json={'x': 3}).status_code
422
```

### qh.testing.test_client(app)

Call an app in-process through a `TestClient`, no server, no port.

The most common case, and the fastest: requests are dispatched straight
to the ASGI app. Use `serve_app` when a real socket matters (another
process, a browser, a generated client pointed at a URL).

* **Parameters:**
  **app** (`FastAPI`) – FastAPI application
* **Yields:**
  TestClient instance
* **Return type:**
  [*Generator*](https://docs.python.org/3/library/typing.html#typing.Generator)[*TestClient*, *None*, *None*]

### Examples

```pycon
>>> from qh import mk_app
>>> from qh.testing import test_app
>>> def hello(name: str = "World") -> str:
...     return f"Hello, {name}!"
>>> app = mk_app([hello])
>>> with test_app(app) as client:
...     client.post('/hello', json={'name': 'Alice'}).json()
'Hello, Alice!'
```

A missing required argument is a `422`, as in FastAPI:

```pycon
>>> def add(x: int, y: int) -> int:
...     return x + y
>>> with test_app(mk_app([add])) as client:
...     client.post('/add', json={'x': 3}).status_code
422
```
