"""
Enhanced OpenAPI generation for qh.

Extends FastAPI's OpenAPI generation with metadata needed for bidirectional
Python ↔ HTTP transformation:

- x-python-signature: Full function signature with defaults
- x-python-module: Module path for imports
- x-python-transformers: Type transformation metadata
- x-python-examples: Generated examples for testing
"""

from typing import Any, Dict, List, Optional, Callable, get_type_hints, get_origin, get_args
import inspect
from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi


def get_python_type_name(type_hint: Any) -> str:
    """
    Get a string representation of a Python type.

    Examples:
        int → "int"
        str → "str"
        list[int] → "list[int]"
        Optional[str] → "Optional[str]"
    """
    if type_hint is inspect.Parameter.empty or type_hint is None:
        return "Any"

    # Handle basic types
    if hasattr(type_hint, '__name__'):
        return type_hint.__name__

    # Handle typing generics
    origin = get_origin(type_hint)
    args = get_args(type_hint)

    if origin is not None:
        origin_name = getattr(origin, '__name__', str(origin))
        if args:
            args_str = ', '.join(get_python_type_name(arg) for arg in args)
            return f"{origin_name}[{args_str}]"
        return origin_name

    return str(type_hint)


def extract_function_signature(func: Callable) -> Dict[str, Any]:
    """
    Extract detailed signature information from a function.

    Returns:
        Dictionary with signature metadata:
        - name: function name
        - module: module path
        - parameters: list of parameter info
        - return_type: return type annotation
        - docstring: function docstring
    """
    sig = inspect.signature(func)
    type_hints = get_type_hints(func) if hasattr(func, '__annotations__') else {}

    parameters = []
    for param_name, param in sig.parameters.items():
        param_type = type_hints.get(param_name, param.annotation)

        param_info = {
            'name': param_name,
            'type': get_python_type_name(param_type),
            'required': param.default is inspect.Parameter.empty,
        }

        if param.default is not inspect.Parameter.empty:
            # Try to serialize default value
            default = param.default
            if isinstance(default, (str, int, float, bool, type(None))):
                param_info['default'] = default
            else:
                param_info['default'] = str(default)

        parameters.append(param_info)

    return_type = type_hints.get('return', sig.return_annotation)

    return {
        'name': func.__name__,
        'module': func.__module__,
        'parameters': parameters,
        'return_type': get_python_type_name(return_type),
        'docstring': inspect.getdoc(func),
    }


def generate_examples_for_function(func: Callable) -> List[Dict[str, Any]]:
    """
    Generate example requests/responses for a function.

    Uses type hints to generate sensible example values.
    """
    sig = inspect.signature(func)
    type_hints = get_type_hints(func) if hasattr(func, '__annotations__') else {}

    examples = []

    # Generate a basic example
    example_request = {}
    for param_name, param in sig.parameters.items():
        param_type = type_hints.get(param_name, param.annotation)

        # Use default if available
        if param.default is not inspect.Parameter.empty:
            if isinstance(param.default, (str, int, float, bool, type(None))):
                continue  # Skip optional params with defaults in minimal example

        # Generate example value based on type
        example_value = _generate_example_value(param_type, param_name)
        if example_value is not None:
            example_request[param_name] = example_value

    if example_request:
        examples.append({
            'summary': 'Basic example',
            'value': example_request
        })

    return examples


def _generate_example_value(type_hint: Any, param_name: str) -> Any:
    """Generate an example value for a given type."""
    if type_hint is inspect.Parameter.empty or type_hint is None:
        return "example_value"

    # Handle basic types
    if type_hint == int or type_hint == 'int':
        # Use param name hints
        if 'id' in param_name.lower():
            return 123
        elif 'count' in param_name.lower() or 'num' in param_name.lower():
            return 10
        return 42
    elif type_hint == str or type_hint == 'str':
        if 'name' in param_name.lower():
            return "example_name"
        elif 'id' in param_name.lower():
            return "abc123"
        return "example"
    elif type_hint == float or type_hint == 'float':
        return 3.14
    elif type_hint == bool or type_hint == 'bool':
        return True
    elif type_hint == list or get_origin(type_hint) == list:
        args = get_args(type_hint)
        if args:
            item_example = _generate_example_value(args[0], 'item')
            return [item_example] if item_example is not None else []
        return []
    elif type_hint == dict or get_origin(type_hint) == dict:
        return {"key": "value"}

    # For custom types, return a placeholder
    return None


def enhance_openapi_schema(
    app: FastAPI,
    *,
    include_examples: bool = True,
    include_python_metadata: bool = True,
    include_transformers: bool = False,
) -> Dict[str, Any]:
    """
    Generate enhanced OpenAPI schema with Python-specific extensions.

    Args:
        app: FastAPI application
        include_examples: Add example requests/responses
        include_python_metadata: Add x-python-* extensions
        include_transformers: Add transformation metadata

    Returns:
        Enhanced OpenAPI schema dictionary
    """
    # Get base OpenAPI schema from FastAPI
    schema = get_openapi(
        title=app.title,
        version=app.version,
        openapi_version=app.openapi_version,
        description=app.description,
        routes=app.routes,
    )

    # Store function metadata by operation_id
    from qh.app import inspect_routes
    routes = inspect_routes(app)

    # Enhance each endpoint with Python metadata
    for route_info in routes:
        func = route_info.get('function')
        if not func:
            continue

        path = route_info['path']
        methods = route_info.get('methods', ['POST'])

        # Skip OpenAPI/docs routes
        if path in ['/openapi.json', '/docs', '/redoc']:
            continue

        # Find the operation in the schema
        path_item = schema.get('paths', {}).get(path, {})

        for method in methods:
            method_lower = method.lower()
            operation = path_item.get(method_lower, {})

            if not operation:
                continue

            # Add Python metadata
            if include_python_metadata:
                sig_info = extract_function_signature(func)
                operation['x-python-signature'] = sig_info

            # Add examples
            if include_examples:
                examples = generate_examples_for_function(func)
                if examples and 'requestBody' in operation:
                    content = operation['requestBody'].get('content', {})
                    json_content = content.get('application/json', {})
                    json_content['examples'] = {
                        f"example_{i}": ex for i, ex in enumerate(examples)
                    }

            # Add transformer metadata (if requested)
            if include_transformers:
                # This would include information about how types are transformed
                # For now, we'll add a placeholder
                operation['x-python-transformers'] = {
                    'note': 'Type transformation metadata would go here'
                }

            path_item[method_lower] = operation

        schema['paths'][path] = path_item

    return schema


def export_openapi(
    app: FastAPI,
    *,
    include_examples: bool = True,
    include_python_metadata: bool = True,
    include_transformers: bool = False,
    output_file: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Export enhanced OpenAPI schema.

    Args:
        app: FastAPI application
        include_examples: Include example requests/responses
        include_python_metadata: Include x-python-* extensions
        include_transformers: Include transformation metadata
        output_file: Optional file path to write JSON output

    Returns:
        Enhanced OpenAPI schema dictionary

    Example:
        >>> from qh import mk_app
        >>> from qh.openapi import export_openapi
        >>> app = mk_app([my_func])
        >>> spec = export_openapi(app, include_examples=True)
    """
    schema = enhance_openapi_schema(
        app,
        include_examples=include_examples,
        include_python_metadata=include_python_metadata,
        include_transformers=include_transformers,
    )

    if output_file:
        import json
        with open(output_file, 'w') as f:
            json.dump(schema, f, indent=2)

    return schema
