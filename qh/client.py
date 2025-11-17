"""
Python client generation from OpenAPI specs.

Generates client-side Python functions that call HTTP endpoints,
preserving the original function signatures and behavior.
"""

from typing import Any, Callable, Dict, Optional, get_type_hints
import inspect
import requests
from urllib.parse import urljoin
import re


class HttpClient:
    """
    Client for calling HTTP endpoints with Python function interface.

    Generated functions preserve original signatures and make HTTP requests
    under the hood.
    """

    def __init__(self, base_url: str, session: Optional[requests.Session] = None):
        """
        Initialize HTTP client.

        Args:
            base_url: Base URL for the API (e.g., "http://localhost:8000")
            session: Optional requests Session for connection pooling
        """
        self.base_url = base_url.rstrip('/')
        self.session = session or requests.Session()
        self._functions: Dict[str, Callable] = {}

    def add_function(
        self,
        name: str,
        path: str,
        method: str,
        signature_info: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Add a function to the client.

        Args:
            name: Function name
            path: HTTP path (may contain {param} placeholders)
            method: HTTP method (GET, POST, etc.)
            signature_info: Optional x-python-signature metadata
        """
        # Create the client function
        func = self._make_client_function(name, path, method, signature_info)
        self._functions[name] = func
        # Also set as attribute for convenience
        setattr(self, name, func)

    def _make_client_function(
        self,
        name: str,
        path: str,
        method: str,
        signature_info: Optional[Dict[str, Any]] = None,
    ) -> Callable:
        """Create a client function that makes HTTP requests."""

        # Extract path parameters
        path_params = set(re.findall(r'\{(\w+)\}', path))

        # Build function signature if we have metadata
        if signature_info:
            params = signature_info.get('parameters', [])
        else:
            params = []

        def client_function(**kwargs):
            """Client function that makes HTTP request."""
            # Separate path params from body/query params
            actual_path = path
            request_data = {}

            for key, value in kwargs.items():
                if key in path_params:
                    # Replace in path
                    actual_path = actual_path.replace(f'{{{key}}}', str(value))
                else:
                    # Add to request data
                    request_data[key] = value

            # Make the HTTP request
            url = urljoin(self.base_url, actual_path)
            method_lower = method.lower()

            try:
                if method_lower == 'get':
                    response = self.session.get(url, params=request_data)
                elif method_lower == 'post':
                    response = self.session.post(url, json=request_data)
                elif method_lower == 'put':
                    response = self.session.put(url, json=request_data)
                elif method_lower == 'delete':
                    response = self.session.delete(url)
                elif method_lower == 'patch':
                    response = self.session.patch(url, json=request_data)
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")

                response.raise_for_status()
                return response.json()
            except requests.HTTPError as e:
                # Re-raise with more context
                error_detail = e.response.text if e.response else str(e)
                raise RuntimeError(
                    f"HTTP {method} {url} failed: {e.response.status_code if e.response else 'unknown'} - {error_detail}"
                ) from e
            except requests.RequestException as e:
                raise RuntimeError(f"Request to {method} {url} failed: {str(e)}") from e

        # Set function metadata
        client_function.__name__ = name
        if signature_info:
            docstring = signature_info.get('docstring', '')
            client_function.__doc__ = docstring or f"Call {method} {path}"
        else:
            client_function.__doc__ = f"Call {method} {path}"

        return client_function

    def __getattr__(self, name: str) -> Callable:
        """Allow calling functions as attributes."""
        if name in self._functions:
            return self._functions[name]
        raise AttributeError(f"No function named '{name}' in client")

    def __dir__(self):
        """List available functions."""
        return list(self._functions.keys()) + list(super().__dir__())


def mk_client_from_openapi(
    openapi_spec: Dict[str, Any],
    base_url: str = "http://localhost:8000",
    session: Optional[requests.Session] = None,
) -> HttpClient:
    """
    Create an HTTP client from an OpenAPI specification.

    Args:
        openapi_spec: OpenAPI spec dictionary
        base_url: Base URL for API requests
        session: Optional requests Session

    Returns:
        HttpClient with functions for each endpoint

    Example:
        >>> from qh.client import mk_client_from_openapi
        >>> spec = {'paths': {'/add': {...}}, ...}
        >>> client = mk_client_from_openapi(spec, 'http://localhost:8000')
        >>> result = client.add(x=3, y=5)
    """
    client = HttpClient(base_url, session)

    # Parse OpenAPI spec and create functions
    paths = openapi_spec.get('paths', {})

    for path, path_item in paths.items():
        # Skip OpenAPI metadata endpoints
        if path in ['/openapi.json', '/docs', '/redoc']:
            continue

        for method, operation in path_item.items():
            # Only process HTTP methods
            if method.upper() not in ['GET', 'POST', 'PUT', 'DELETE', 'PATCH']:
                continue

            # Get Python signature metadata if available
            signature_info = operation.get('x-python-signature')

            # Extract function name - prefer x-python-signature if available
            if signature_info and 'name' in signature_info:
                func_name = signature_info['name']
            else:
                # Fallback: try to extract from operationId or path
                operation_id = operation.get('operationId', '')
                if operation_id:
                    # operationId is often like "add_add_post", extract the function name
                    # Try to find a reasonable name by removing method suffix
                    func_name = operation_id.split('_')[0]
                else:
                    # Last resort: use path
                    func_name = path.strip('/').replace('/', '_').replace('{', '').replace('}', '')

            # Add function to client
            client.add_function(
                name=func_name,
                path=path,
                method=method.upper(),
                signature_info=signature_info,
            )

    return client


def mk_client_from_url(
    openapi_url: str,
    base_url: Optional[str] = None,
    session: Optional[requests.Session] = None,
) -> HttpClient:
    """
    Create an HTTP client by fetching OpenAPI spec from a URL.

    Args:
        openapi_url: URL to OpenAPI JSON spec (e.g., "http://localhost:8000/openapi.json")
        base_url: Base URL for API requests (defaults to same as openapi_url)
        session: Optional requests Session

    Returns:
        HttpClient with functions for each endpoint

    Example:
        >>> from qh.client import mk_client_from_url
        >>> client = mk_client_from_url('http://localhost:8000/openapi.json')
        >>> result = client.add(x=3, y=5)
    """
    # Fetch OpenAPI spec
    session_obj = session or requests.Session()
    response = session_obj.get(openapi_url)
    response.raise_for_status()
    openapi_spec = response.json()

    # Infer base_url from openapi_url if not provided
    if base_url is None:
        from urllib.parse import urlparse
        parsed = urlparse(openapi_url)
        base_url = f"{parsed.scheme}://{parsed.netloc}"

    return mk_client_from_openapi(openapi_spec, base_url, session_obj)


def mk_client_from_app(app, base_url: str = "http://testserver") -> HttpClient:
    """
    Create an HTTP client from a FastAPI app (for testing).

    Args:
        app: FastAPI application
        base_url: Base URL for API requests (default for TestClient)

    Returns:
        HttpClient that uses FastAPI TestClient under the hood

    Example:
        >>> from qh import mk_app
        >>> from qh.client import mk_client_from_app
        >>> app = mk_app([add, subtract])
        >>> client = mk_client_from_app(app)
        >>> result = client.add(x=3, y=5)
    """
    from qh.openapi import export_openapi

    # Get enhanced OpenAPI spec
    openapi_spec = export_openapi(app, include_python_metadata=True)

    # Create client with TestClient session
    from fastapi.testclient import TestClient
    test_client = TestClient(app)

    # Wrap TestClient to look like requests.Session
    class TestClientWrapper:
        def __init__(self, test_client):
            self._client = test_client

        def get(self, url, **kwargs):
            return self._client.get(url, **kwargs)

        def post(self, url, **kwargs):
            return self._client.post(url, **kwargs)

        def put(self, url, **kwargs):
            return self._client.put(url, **kwargs)

        def delete(self, url, **kwargs):
            return self._client.delete(url, **kwargs)

        def patch(self, url, **kwargs):
            return self._client.patch(url, **kwargs)

    session = TestClientWrapper(test_client)
    return mk_client_from_openapi(openapi_spec, base_url, session)
