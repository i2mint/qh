"""
Convention-based routing for qh.

Automatically infer HTTP paths and methods from function names and signatures.

Supports patterns like:
- get_user(user_id: str) → GET /users/{user_id}
- list_users(limit: int = 100) → GET /users?limit=100
- create_user(user: User) → POST /users
- update_user(user_id: str, user: User) → PUT /users/{user_id}
- delete_user(user_id: str) → DELETE /users/{user_id}
"""

from typing import Callable, Optional, List, Dict, Tuple, Any
import inspect
import re
from dataclasses import dataclass


# Common CRUD verb patterns
CRUD_VERBS = {
    'get': 'GET',
    'fetch': 'GET',
    'retrieve': 'GET',
    'read': 'GET',
    'list': 'GET',
    'find': 'GET',
    'search': 'GET',
    'query': 'GET',
    'create': 'POST',
    'add': 'POST',
    'insert': 'POST',
    'new': 'POST',
    'update': 'PUT',
    'modify': 'PUT',
    'edit': 'PUT',
    'change': 'PUT',
    'set': 'PUT',
    'patch': 'PATCH',
    'delete': 'DELETE',
    'remove': 'DELETE',
    'destroy': 'DELETE',
}


@dataclass
class ParsedFunctionName:
    """Result of parsing a function name."""
    verb: str  # e.g., 'get', 'list', 'create'
    resource: str  # e.g., 'user', 'users', 'order'
    is_plural: bool  # Whether resource is plural
    is_collection_operation: bool  # e.g., list_users vs get_user


def parse_function_name(func_name: str) -> ParsedFunctionName:
    """
    Parse a function name to extract verb and resource.

    Examples:
        >>> parse_function_name('get_user')
        ParsedFunctionName(verb='get', resource='user', is_plural=False, is_collection_operation=False)

        >>> parse_function_name('list_users')
        ParsedFunctionName(verb='list', resource='users', is_plural=True, is_collection_operation=True)

        >>> parse_function_name('create_order_item')
        ParsedFunctionName(verb='create', resource='order_item', is_plural=False, is_collection_operation=False)
    """
    # Try to match verb_resource pattern
    parts = func_name.split('_', 1)

    if len(parts) == 2:
        verb, resource = parts
        verb = verb.lower()

        # Check if verb is in our known list
        if verb in CRUD_VERBS:
            # Check if this is a collection operation
            is_collection = verb in ('list', 'create', 'search', 'query')

            # Check if resource is plural (simple heuristic)
            is_plural = resource.endswith('s') or is_collection

            return ParsedFunctionName(
                verb=verb,
                resource=resource,
                is_plural=is_plural,
                is_collection_operation=is_collection,
            )

    # Fallback: treat whole name as resource
    return ParsedFunctionName(
        verb='',
        resource=func_name,
        is_plural=False,
        is_collection_operation=False,
    )


def infer_http_method(func_name: str, parsed: Optional[ParsedFunctionName] = None) -> str:
    """
    Infer HTTP method from function name.

    Args:
        func_name: Function name
        parsed: Optional pre-parsed function name

    Returns:
        HTTP method ('GET', 'POST', 'PUT', 'PATCH', 'DELETE')

    Examples:
        >>> infer_http_method('get_user')
        'GET'
        >>> infer_http_method('create_user')
        'POST'
        >>> infer_http_method('update_user')
        'PUT'
        >>> infer_http_method('delete_user')
        'DELETE'
    """
    if parsed is None:
        parsed = parse_function_name(func_name)

    if parsed.verb in CRUD_VERBS:
        return CRUD_VERBS[parsed.verb]

    # Default to POST for unknown verbs
    return 'POST'


def singularize(word: str) -> str:
    """
    Simple singularization (just removes trailing 's' for now).

    More sophisticated rules can be added later.
    """
    if word.endswith('ies'):
        return word[:-3] + 'y'
    elif word.endswith('ses'):
        return word[:-2]
    elif word.endswith('s') and not word.endswith('ss'):
        return word[:-1]
    return word


def pluralize(word: str) -> str:
    """
    Simple pluralization.

    More sophisticated rules can be added later.
    """
    if word.endswith('y') and word[-2] not in 'aeiou':
        return word[:-1] + 'ies'
    elif word.endswith('s') or word.endswith('x') or word.endswith('z'):
        return word + 'es'
    else:
        return word + 's'


def get_id_params(func: Callable) -> List[str]:
    """
    Extract parameters that look like IDs from function signature.

    ID parameters typically:
    - End with '_id'
    - Are named 'id'
    - Are the first parameter (for item operations)

    Args:
        func: Function to analyze

    Returns:
        List of parameter names that are likely IDs
    """
    sig = inspect.signature(func)
    id_params = []

    for param_name, param in sig.parameters.items():
        # Check if it's an ID parameter
        if param_name == 'id' or param_name.endswith('_id'):
            id_params.append(param_name)
        # Check if it's a key parameter (for stores)
        elif param_name == 'key':
            id_params.append(param_name)

    return id_params


def infer_path_from_function(
    func: Callable,
    *,
    use_plurals: bool = True,
    base_path: str = '',
) -> str:
    """
    Infer RESTful path from function name and signature.

    Args:
        func: Function to analyze
        use_plurals: Whether to use plural resource names for collections
        base_path: Base path to prepend

    Returns:
        Inferred path

    Examples:
        >>> def get_user(user_id: str): pass
        >>> infer_path_from_function(get_user)
        '/users/{user_id}'

        >>> def list_users(limit: int = 100): pass
        >>> infer_path_from_function(list_users)
        '/users'

        >>> def create_user(name: str, email: str): pass
        >>> infer_path_from_function(create_user)
        '/users'

        >>> def update_user(user_id: str, name: str): pass
        >>> infer_path_from_function(update_user)
        '/users/{user_id}'
    """
    func_name = func.__name__
    parsed = parse_function_name(func_name)
    id_params = get_id_params(func)

    # For collection operations (list, create, search), don't include ID in path
    # IDs for create operations go in the request body, not the path
    if parsed.is_collection_operation:
        id_params = []

    # Determine resource name (plural or singular)
    resource = parsed.resource

    if use_plurals:
        # Collection operations use plural
        if parsed.is_collection_operation:
            resource = pluralize(singularize(resource))  # Normalize first
        # Item operations use plural base + ID
        elif id_params:
            resource = pluralize(singularize(resource))
        else:
            # No clear pattern, use as-is
            pass

    # Build path
    path_parts = [base_path] if base_path else []

    # Add resource
    path_parts.append(resource)

    # Add ID parameters to path
    for id_param in id_params:
        path_parts.append(f'{{{id_param}}}')

    path = '/' + '/'.join(p.strip('/') for p in path_parts if p)

    return path


def infer_route_config(
    func: Callable,
    *,
    use_conventions: bool = True,
    base_path: str = '',
    use_plurals: bool = True,
) -> Dict[str, Any]:
    """
    Infer complete route configuration from function.

    Args:
        func: Function to analyze
        use_conventions: Whether to use conventions (if False, returns empty dict)
        base_path: Base path to prepend
        use_plurals: Whether to use plural resource names

    Returns:
        Route configuration dict
    """
    if not use_conventions:
        return {}

    func_name = func.__name__
    parsed = parse_function_name(func_name)

    config = {}

    # Infer path
    config['path'] = infer_path_from_function(
        func,
        use_plurals=use_plurals,
        base_path=base_path,
    )

    # Infer HTTP method
    http_method = infer_http_method(func_name, parsed)
    config['methods'] = [http_method]

    # For GET requests, non-path parameters should come from query string
    if http_method == 'GET':
        from qh.rules import TransformSpec, HttpLocation
        import inspect
        import re
        from typing import get_type_hints

        # Get path parameters
        path_params = set(re.findall(r'\{(\w+)\}', config['path']))

        # Get function parameters and their types
        sig = inspect.signature(func)
        type_hints = get_type_hints(func) if hasattr(func, '__annotations__') else {}
        param_overrides = {}

        for param_name, param in sig.parameters.items():
            # Skip path parameters
            if param_name not in path_params:
                # Get the type hint for this parameter
                param_type = type_hints.get(param_name, str)

                # Create an ingress function that converts from string to the correct type
                def make_converter(target_type):
                    def convert(value):
                        if value is None:
                            return None
                        if isinstance(value, target_type):
                            return value
                        # Convert from string
                        return target_type(value)
                    return convert

                # Non-path parameters for GET should be query parameters
                param_overrides[param_name] = TransformSpec(
                    http_location=HttpLocation.QUERY,
                    ingress=make_converter(param_type) if param_type != str else None
                )

        if param_overrides:
            config['param_overrides'] = param_overrides

    # Auto-generate summary if docstring exists
    if func.__doc__:
        first_line = func.__doc__.strip().split('\n')[0]
        config['summary'] = first_line

    # Add tags based on resource
    if parsed.resource:
        config['tags'] = [parsed.resource]

    return config


def apply_conventions_to_funcs(
    funcs: List[Callable],
    *,
    use_conventions: bool = True,
    base_path: str = '',
    use_plurals: bool = True,
) -> Dict[Callable, Dict[str, Any]]:
    """
    Apply conventions to a list of functions.

    Args:
        funcs: List of functions
        use_conventions: Whether to use conventions
        base_path: Base path to prepend to all routes
        use_plurals: Whether to use plural resource names

    Returns:
        Dict mapping functions to their inferred configurations
    """
    result = {}

    for func in funcs:
        config = infer_route_config(
            func,
            use_conventions=use_conventions,
            base_path=base_path,
            use_plurals=use_plurals,
        )
        result[func] = config

    return result


# Add a helper to merge convention config with explicit config
def merge_convention_config(
    convention_config: Dict[str, Any],
    explicit_config: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Merge convention-based config with explicit config.

    Explicit config takes precedence.

    Args:
        convention_config: Config inferred from conventions
        explicit_config: User-provided config

    Returns:
        Merged config
    """
    merged = convention_config.copy()
    merged.update(explicit_config)
    return merged
