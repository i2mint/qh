# qh.client

Python client generation from OpenAPI specs.

Generates client-side Python functions that call HTTP endpoints,
preserving the original function signatures and behavior.

### Functions

| [`mk_client_from_app`](#qh.client.mk_client_from_app)(app[, base_url])              | Create an HTTP client from a FastAPI app (for testing).    |
|---------------------------------------------------------------------------------------------------|------------------------------------------------------------|
| [`mk_client_from_openapi`](#qh.client.mk_client_from_openapi)(openapi_spec[, ...])      | Create an HTTP client from an OpenAPI specification.       |
| [`mk_client_from_url`](#qh.client.mk_client_from_url)(openapi_url[, base_url, ...]) | Create an HTTP client by fetching OpenAPI spec from a URL. |

### Classes

| [`HttpClient`](#qh.client.HttpClient)(base_url[, session])   | Client for calling HTTP endpoints with Python function interface.   |
|------------------------------------------------------------------------------------|---------------------------------------------------------------------|

### *class* qh.client.HttpClient(base_url, session=None)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

Client for calling HTTP endpoints with Python function interface.

Generated functions preserve original signatures and make HTTP requests
under the hood.

#### add_function(name, path, method, signature_info=None)

Add a function to the client.

* **Parameters:**
  * **name** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – Function name
  * **path** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – HTTP path (may contain {param} placeholders)
  * **method** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – HTTP method (GET, POST, etc.)
  * **signature_info** ([`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`Dict`](https://docs.python.org/3/library/typing.html#typing.Dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)]]) – Optional x-python-signature metadata
* **Return type:**
  [`None`](https://docs.python.org/3/builtins/constants.html#None)

### qh.client.mk_client_from_app(app, base_url='http://testserver')

Create an HTTP client from a FastAPI app (for testing).

* **Parameters:**
  * **app** – FastAPI application
  * **base_url** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – Base URL for API requests (default for TestClient)
* **Return type:**
  [`HttpClient`](#qh.client.HttpClient)
* **Returns:**
  HttpClient that uses FastAPI TestClient under the hood

### Example

```pycon
>>> from qh import mk_app
>>> from qh.client import mk_client_from_app
>>> app = mk_app([add, subtract])
>>> client = mk_client_from_app(app)
>>> result = client.add(x=3, y=5)
```

### qh.client.mk_client_from_openapi(openapi_spec, base_url='http://localhost:8000', session=None)

Create an HTTP client from an OpenAPI specification.

* **Parameters:**
  * **openapi_spec** ([`Dict`](https://docs.python.org/3/library/typing.html#typing.Dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)]) – The parsed OpenAPI document (as from `export_openapi`
    or `json.load` on a spec file), used to build one client function
    per operation.
  * **base_url** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – Base URL for API requests
  * **session** ([`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[`Session`]) – An existing session to reuse (e.g. for shared auth/headers);
    a new one is created if not given.
* **Return type:**
  [`HttpClient`](#qh.client.HttpClient)
* **Returns:**
  HttpClient with functions for each endpoint

### Example

```pycon
>>> from qh.client import mk_client_from_openapi
>>> spec = {'paths': {'/add': {...}}, ...}
>>> client = mk_client_from_openapi(spec, 'http://localhost:8000')
>>> result = client.add(x=3, y=5)
```

### qh.client.mk_client_from_url(openapi_url, base_url=None, session=None)

Create an HTTP client by fetching OpenAPI spec from a URL.

* **Parameters:**
  * **openapi_url** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – URL to OpenAPI JSON spec (e.g., “[http://localhost:8000/openapi.json](http://localhost:8000/openapi.json)”)
  * **base_url** ([`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]) – Base URL for API requests (defaults to same as openapi_url)
  * **session** ([`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[`Session`]) – An existing session to reuse; a new one is created if not given.
* **Return type:**
  [`HttpClient`](#qh.client.HttpClient)
* **Returns:**
  HttpClient with functions for each endpoint

### Example

```pycon
>>> from qh.client import mk_client_from_url
>>> client = mk_client_from_url('http://localhost:8000/openapi.json')
>>> result = client.add(x=3, y=5)
```
