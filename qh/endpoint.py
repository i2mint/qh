"""
Endpoint creation using i2.Wrap to transform functions into FastAPI routes.

This module bridges Python functions and HTTP endpoints via transformation rules.
"""

from typing import Any, Callable, Dict, Optional, get_type_hints
from fastapi import Request, Response, HTTPException
from fastapi.responses import JSONResponse
import inspect
import json

from i2 import Sig
from i2.wrapper import Wrap

from qh.rules import RuleChain, TransformSpec, HttpLocation, resolve_transform
from qh.config import RouteConfig


async def extract_http_params(
    request: Request,
    param_specs: Dict[str, TransformSpec],
) -> Dict[str, Any]:
    """
    Extract parameters from HTTP request based on transformation specs.

    Args:
        request: FastAPI Request object
        param_specs: Mapping of param name to its TransformSpec

    Returns:
        Dict of parameter name to extracted value
    """
    params = {}

    # Collect parameters from various HTTP locations
    for param_name, spec in param_specs.items():
        http_name = spec.http_name or param_name
        value = None

        if spec.http_location == HttpLocation.PATH:
            # Path parameters
            value = request.path_params.get(http_name)

        elif spec.http_location == HttpLocation.QUERY:
            # Query parameters
            value = request.query_params.get(http_name)

        elif spec.http_location == HttpLocation.HEADER:
            # Headers
            value = request.headers.get(http_name)

        elif spec.http_location == HttpLocation.COOKIE:
            # Cookies
            value = request.cookies.get(http_name)

        elif spec.http_location == HttpLocation.JSON_BODY:
            # Will be handled after we parse the body
            pass

        elif spec.http_location == HttpLocation.BINARY_BODY:
            # Raw body
            value = await request.body()

        elif spec.http_location == HttpLocation.FORM_DATA:
            # Form data
            form = await request.form()
            value = form.get(http_name)

        if value is not None:
            params[param_name] = value

    # Handle JSON body parameters
    json_params = {
        name: spec for name, spec in param_specs.items()
        if spec.http_location == HttpLocation.JSON_BODY
    }

    if json_params:
        try:
            # Try to parse JSON body
            body = await request.json()
            if body is None:
                body = {}

            for param_name, spec in json_params.items():
                http_name = spec.http_name or param_name
                if http_name in body:
                    params[param_name] = body[http_name]

        except json.JSONDecodeError:
            # If no valid JSON, that's okay for GET requests
            if request.method not in ['GET', 'DELETE', 'HEAD']:
                # For other methods, might be an error
                pass

    return params


def apply_ingress_transforms(
    params: Dict[str, Any],
    param_specs: Dict[str, TransformSpec],
) -> Dict[str, Any]:
    """Apply ingress transformations to extracted parameters."""
    transformed = {}

    for param_name, value in params.items():
        spec = param_specs.get(param_name)
        if spec and spec.ingress:
            transformed[param_name] = spec.ingress(value)
        else:
            transformed[param_name] = value

    return transformed


def apply_egress_transform(
    result: Any,
    egress: Optional[Callable[[Any], Any]],
) -> Any:
    """Apply egress transformation to function result."""
    if egress:
        return egress(result)
    return result


def make_endpoint(
    func: Callable,
    route_config: RouteConfig,
) -> Callable:
    """
    Create FastAPI endpoint from a function using i2.Wrap.

    Args:
        func: The Python function to wrap
        route_config: Configuration for this route

    Returns:
        Async endpoint function compatible with FastAPI
    """
    # Get function signature
    sig = inspect.signature(func)
    is_async = inspect.iscoroutinefunction(func)

    # Detect path parameters from route path
    import re
    from typing import get_type_hints
    path_param_names = set()
    if route_config.path:
        path_param_names = set(re.findall(r'\{(\w+)\}', route_config.path))

    # Check if this uses query params (GET-only routes without POST/PUT/PATCH)
    # Routes with POST/PUT/PATCH should use JSON body even if GET is also supported
    methods = route_config.methods or []
    has_body_methods = any(m in methods for m in ['POST', 'PUT', 'PATCH'])
    use_query_params = 'GET' in methods and not has_body_methods

    # Resolve transformation specs for each parameter
    rule_chain = route_config.rule_chain
    param_specs: Dict[str, TransformSpec] = {}

    # Get type hints for type conversion
    type_hints = get_type_hints(func) if hasattr(func, '__annotations__') else {}

    for param_name in sig.parameters:
        # Check for parameter-specific override
        if param_name in route_config.param_overrides:
            param_specs[param_name] = route_config.param_overrides[param_name]
        # Check if this is a path parameter
        elif param_name in path_param_names:
            # Path parameters should be extracted from the URL path
            param_specs[param_name] = TransformSpec(http_location=HttpLocation.PATH)
        # For GET-only requests, non-path parameters come from query string
        elif use_query_params:
            param_type = type_hints.get(param_name, str)

            # Create type converter for query params (they come as strings)
            def make_query_converter(target_type):
                def convert(value):
                    if value is None:
                        return None
                    if isinstance(value, target_type):
                        return value
                    return target_type(value)
                return convert

            param_specs[param_name] = TransformSpec(
                http_location=HttpLocation.QUERY,
                ingress=make_query_converter(param_type) if param_type != str else None
            )
        else:
            # Resolve from rule chain
            param_specs[param_name] = resolve_transform(
                func, param_name, rule_chain
            )

    # Determine if we need egress transformation for output
    # For now, we'll use a simple JSON serializer
    def default_egress(obj: Any) -> Any:
        """Default output transformation."""
        # Handle common types
        if isinstance(obj, (dict, list, str, int, float, bool, type(None))):
            return obj
        # Try to convert to dict if it has __dict__
        elif hasattr(obj, '__dict__'):
            return obj.__dict__
        # Otherwise convert to string
        else:
            return str(obj)

    async def endpoint(request: Request) -> Response:
        """FastAPI endpoint that wraps the original function."""
        try:
            # Extract parameters from HTTP request
            http_params = await extract_http_params(request, param_specs)

            # Apply ingress transformations
            transformed_params = apply_ingress_transforms(http_params, param_specs)

            # Validate required parameters
            for param_name, param in sig.parameters.items():
                if param.default is inspect.Parameter.empty:
                    # Required parameter
                    if param_name not in transformed_params:
                        raise HTTPException(
                            status_code=422,
                            detail=f"Missing required parameter: {param_name}",
                        )
                else:
                    # Optional parameter - use default if not provided
                    if param_name not in transformed_params:
                        transformed_params[param_name] = param.default

            # Call the wrapped function
            if is_async:
                result = await func(**transformed_params)
            else:
                result = func(**transformed_params)

            # Apply egress transformation
            output = apply_egress_transform(result, default_egress)

            # Return JSON response
            return JSONResponse(content=output)

        except HTTPException:
            # Re-raise HTTP exceptions
            raise

        except Exception as e:
            # Wrap other exceptions
            raise HTTPException(
                status_code=500,
                detail=f"Error in {func.__name__}: {str(e)}",
            )

    # Set endpoint metadata
    endpoint.__name__ = f"{func.__name__}_endpoint"
    endpoint.__doc__ = func.__doc__
    # Store original function for OpenAPI/client generation
    endpoint._qh_original_func = func  # type: ignore

    return endpoint


def validate_route_config(func: Callable, config: RouteConfig) -> None:
    """
    Validate that route configuration is compatible with function.

    Raises:
        ValueError: If configuration is invalid
    """
    sig = inspect.signature(func)
    param_names = list(sig.parameters.keys())

    # Check that param_overrides reference actual parameters
    for param_name in config.param_overrides:
        if param_name not in param_names:
            raise ValueError(
                f"Parameter override '{param_name}' not found in function {func.__name__}. "
                f"Available parameters: {param_names}"
            )

    # Validate path parameters are in function signature
    if config.path:
        # Extract {param} from path
        import re
        path_params = re.findall(r'\{(\w+)\}', config.path)
        for param in path_params:
            if param not in param_names:
                raise ValueError(
                    f"Path parameter '{param}' in route '{config.path}' "
                    f"not found in function {func.__name__}. "
                    f"Available parameters: {param_names}"
                )
