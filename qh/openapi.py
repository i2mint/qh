"""
OpenAPI generation for qh — including JSON Schema derived from Python type hints.

``qh`` builds every route with a generic ``endpoint(request: Request)`` signature
(see :mod:`qh.endpoint`): the wrapped function's real parameters and return type
are parsed *manually* from the request body, which makes them invisible to
FastAPI's own OpenAPI machinery. Out of the box, therefore, ``/openapi.json``
lists routes and docstrings but emits empty ``{}`` request/response schemas and
no ``components.schemas``.

This module closes that gap. It introspects each wrapped function's Python type
hints and derives a complete OpenAPI document:

- ``requestBody`` — a JSON Schema object built from the JSON-body parameters,
- ``parameters`` — path/query parameters,
- ``responses`` — a JSON Schema for the return type,
- ``components.schemas`` — one named schema per dataclass / ``TypedDict`` /
  Pydantic model / ``NamedTuple`` / ``Enum`` encountered, referenced via ``$ref``,
- ``x-python-*`` extensions — Python signature metadata for bidirectional
  Python ↔ HTTP transformation.

The whole thing is **additive**: the request-handling path is untouched, and
:func:`install_enhanced_openapi` falls back to FastAPI's plain schema if
enhancement ever raises — so a converter bug can never break ``/openapi.json``.

Public surface:

- :func:`python_type_to_json_schema` — the Python-type-hint → JSON Schema converter.
- :func:`enhance_openapi_schema` — full enhanced OpenAPI document for an app.
- :func:`export_openapi` — :func:`enhance_openapi_schema` plus optional file output.
- :func:`install_enhanced_openapi` — make an app serve the enhanced doc at
  ``/openapi.json`` (and render it in ``/docs``).
"""

import collections.abc
import dataclasses
import enum
import inspect
import json
from typing import (
    Any,
    Callable,
    Dict,
    ForwardRef,
    List,
    Literal,
    Optional,
    Union,
    get_args,
    get_origin,
    get_type_hints,
)

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

try:  # PEP 604 unions (``int | None``) — Python 3.10+
    from types import UnionType  # type: ignore
except ImportError:  # pragma: no cover - Python < 3.10
    UnionType = None  # type: ignore

NoneType = type(None)

#: Exact-match JSON Schema for Python primitives. ``bool`` is listed before
#: ``int`` only for readability — lookup is by exact type, so order is moot.
_PRIMITIVE_SCHEMAS: Dict[type, Dict[str, Any]] = {
    bool: {"type": "boolean"},
    int: {"type": "integer"},
    float: {"type": "number"},
    str: {"type": "string"},
    bytes: {"type": "string", "format": "byte"},
    NoneType: {"type": "null"},
}

#: Generic origins treated as JSON arrays.
_ARRAY_ORIGINS = (
    list,
    tuple,
    set,
    frozenset,
    collections.abc.Sequence,
    collections.abc.MutableSequence,
    collections.abc.Set,
    collections.abc.MutableSet,
    collections.abc.Collection,
    collections.abc.Iterable,
)

#: Generic origins treated as JSON objects (free-form maps).
_MAPPING_ORIGINS = (
    dict,
    collections.abc.Mapping,
    collections.abc.MutableMapping,
)


# ---------------------------------------------------------------------------
# Python type → JSON Schema
# ---------------------------------------------------------------------------


def _ref(name: str) -> Dict[str, str]:
    """A JSON Schema ``$ref`` into ``components.schemas``."""
    return {"$ref": f"#/components/schemas/{name}"}


def _safe_type_hints(obj: Any) -> Dict[str, Any]:
    """Resolve type hints, degrading gracefully when annotations don't resolve.

    ``get_type_hints`` raises ``NameError`` for string annotations referring to
    names not in the object's module globals (e.g. types defined inside a
    function). In that case fall back to the raw ``__annotations__`` mapping —
    the converter treats any leftover string as an unknown (empty) schema.
    """
    try:
        return get_type_hints(obj)
    except Exception:
        return dict(getattr(obj, "__annotations__", {}) or {})


def _is_typed_dict(tp: Any) -> bool:
    """Whether ``tp`` is a ``typing.TypedDict`` subclass."""
    # ``__required_keys__`` / ``__optional_keys__`` are the stable markers.
    return (
        isinstance(tp, type)
        and hasattr(tp, "__required_keys__")
        and hasattr(tp, "__annotations__")
    )


def _is_namedtuple(tp: Any) -> bool:
    """Whether ``tp`` is a ``typing.NamedTuple`` / ``collections.namedtuple``."""
    return (
        isinstance(tp, type)
        and issubclass(tp, tuple)
        and hasattr(tp, "_fields")
        and hasattr(tp, "__annotations__")
    )


def _is_pydantic_model(tp: Any) -> bool:
    """Whether ``tp`` is a Pydantic model (v2 ``model_json_schema`` or v1 ``schema``)."""
    return isinstance(tp, type) and (
        hasattr(tp, "model_json_schema") or hasattr(tp, "schema")
    ) and hasattr(tp, "__fields__")


def python_type_to_json_schema(
    type_hint: Any,
    schemas: Dict[str, Any],
    *,
    _stack: Optional[frozenset] = None,
) -> Dict[str, Any]:
    """Convert a Python type hint to a JSON Schema fragment.

    Primitives, containers and unions are inlined. Named composite types —
    dataclasses, ``TypedDict``\\ s, Pydantic models, ``NamedTuple``\\ s and
    ``Enum``\\ s — are registered in ``schemas`` (the OpenAPI
    ``components.schemas`` table) and returned as a ``$ref``, so the same type
    used in several places is described once.

    Args:
        type_hint: the Python type / annotation to convert. ``Any`` and
            :data:`inspect.Parameter.empty` map to the empty schema ``{}``
            (matches anything); ``None`` / ``NoneType`` map to ``{"type": "null"}``.
        schemas: the mutable ``components.schemas`` accumulator — composite
            types encountered are added here, keyed by their class name.
        _stack: internal — the set of composite type names currently being
            built, used to break recursion on self-referential types.

    Returns:
        a JSON Schema dict — an inline fragment, or ``{"$ref": ...}`` for a
        named composite type.

    Examples:
        >>> python_type_to_json_schema(int, {})
        {'type': 'integer'}
        >>> python_type_to_json_schema(list[str], {})
        {'type': 'array', 'items': {'type': 'string'}}
        >>> python_type_to_json_schema(Optional[int], {})
        {'anyOf': [{'type': 'integer'}, {'type': 'null'}]}
    """
    stack = _stack if _stack is not None else frozenset()

    # Unknowns → permissive empty schema.
    if type_hint is inspect.Parameter.empty or type_hint is Any:
        return {}

    # Forward references — a bare string or a typing.ForwardRef. These appear
    # for self-referential types: ``get_type_hints`` leaves the inner type of
    # ``list["TreeNode"]`` unresolved (a bare ``str`` on Python 3.10, a
    # ``ForwardRef`` elsewhere). Resolve only against names already known to
    # the schema registry or currently on the recursion stack; an otherwise
    # unresolvable reference degrades to the permissive empty schema.
    if isinstance(type_hint, (str, ForwardRef)):
        name = (
            type_hint
            if isinstance(type_hint, str)
            else type_hint.__forward_arg__
        )
        return _ref(name) if (name in schemas or name in stack) else {}

    # Exact primitive match (covers ``NoneType`` too).
    if type_hint in _PRIMITIVE_SCHEMAS:
        return dict(_PRIMITIVE_SCHEMAS[type_hint])
    if type_hint is None:  # a bare ``None`` annotation means ``NoneType``
        return {"type": "null"}

    origin = get_origin(type_hint)
    args = get_args(type_hint)

    # Unions (``typing.Union`` and PEP 604 ``X | Y``), incl. ``Optional``.
    if origin is Union or (UnionType is not None and origin is UnionType):
        non_none = [a for a in args if a is not NoneType]
        sub = [python_type_to_json_schema(a, schemas, _stack=stack) for a in non_none]
        if len(non_none) != len(args):  # had ``None`` → nullable
            sub.append({"type": "null"})
        return sub[0] if len(sub) == 1 else {"anyOf": sub}

    # ``Literal[...]`` → enum of the literal values.
    if origin is Literal:
        return {"enum": list(args)}

    # Arrays.
    if origin in _ARRAY_ORIGINS:
        item_args = [a for a in args if a is not Ellipsis]
        item = (
            python_type_to_json_schema(item_args[0], schemas, _stack=stack)
            if item_args
            else {}
        )
        return {"type": "array", "items": item}

    # Free-form objects (maps). JSON object keys are always strings, so the key
    # type is ignored; only the value type informs ``additionalProperties``.
    if origin in _MAPPING_ORIGINS:
        value = (
            python_type_to_json_schema(args[1], schemas, _stack=stack)
            if len(args) == 2
            else {}
        )
        return {"type": "object", "additionalProperties": value}

    # Bare ``list`` / ``dict`` (no parameters).
    if type_hint is list:
        return {"type": "array", "items": {}}
    if type_hint is dict:
        return {"type": "object", "additionalProperties": {}}

    # Named composite types → registered in ``schemas``, returned as ``$ref``.
    if _is_typed_dict(type_hint):
        return _register_object(type_hint, schemas, stack, _typed_dict_fields)
    if dataclasses.is_dataclass(type_hint) and isinstance(type_hint, type):
        return _register_object(type_hint, schemas, stack, _dataclass_fields)
    if _is_pydantic_model(type_hint):
        return _register_pydantic(type_hint, schemas)
    if _is_namedtuple(type_hint):
        return _register_object(type_hint, schemas, stack, _namedtuple_fields)
    if isinstance(type_hint, type) and issubclass(type_hint, enum.Enum):
        return {"enum": [member.value for member in type_hint]}

    # Primitive subclasses (e.g. ``class UserId(str)``).
    if isinstance(type_hint, type):
        for prim, prim_schema in _PRIMITIVE_SCHEMAS.items():
            if prim is not NoneType and issubclass(type_hint, prim):
                return dict(prim_schema)

    # Unknown — permissive empty schema.
    return {}


def _register_object(
    tp: type,
    schemas: Dict[str, Any],
    stack: frozenset,
    fields_fn: Callable[[type], List[tuple]],
) -> Dict[str, str]:
    """Register an object-shaped composite type and return a ``$ref`` to it.

    ``fields_fn`` yields ``(name, type_hint, required)`` triples. The type name
    is added to the recursion ``stack`` *before* its fields are converted, so a
    self-referential field resolves to a ``$ref`` instead of recursing forever.
    """
    name = tp.__name__
    if name in schemas or name in stack:
        return _ref(name)

    child_stack = stack | {name}
    properties: Dict[str, Any] = {}
    required: List[str] = []
    for field_name, field_type, is_required in fields_fn(tp):
        properties[field_name] = python_type_to_json_schema(
            field_type, schemas, _stack=child_stack
        )
        if is_required:
            required.append(field_name)

    obj: Dict[str, Any] = {"type": "object", "properties": properties}
    if required:
        obj["required"] = required
    doc = inspect.getdoc(tp)
    if doc:
        obj["description"] = doc
    schemas[name] = obj
    return _ref(name)


def _typed_dict_fields(tp: type) -> List[tuple]:
    """``(name, type, required)`` triples for a ``TypedDict``.

    Honours ``total=False`` and per-key ``Required`` / ``NotRequired`` via the
    ``__required_keys__`` / ``__optional_keys__`` markers.
    """
    hints = _safe_type_hints(tp)
    required_keys = set(getattr(tp, "__required_keys__", set()))
    return [
        (key, hints.get(key, Any), key in required_keys) for key in hints
    ]


def _dataclass_fields(tp: type) -> List[tuple]:
    """``(name, type, required)`` triples for a dataclass — required = no default."""
    hints = _safe_type_hints(tp)
    triples = []
    for field in dataclasses.fields(tp):
        has_default = (
            field.default is not dataclasses.MISSING
            or field.default_factory is not dataclasses.MISSING  # type: ignore[misc]
        )
        triples.append((field.name, hints.get(field.name, field.type), not has_default))
    return triples


def _namedtuple_fields(tp: type) -> List[tuple]:
    """``(name, type, required)`` triples for a ``NamedTuple`` — required = no default."""
    hints = _safe_type_hints(tp)
    defaults = getattr(tp, "_field_defaults", {})
    return [
        (name, hints.get(name, Any), name not in defaults)
        for name in getattr(tp, "_fields", ())
    ]


def _register_pydantic(tp: type, schemas: Dict[str, Any]) -> Dict[str, str]:
    """Register a Pydantic model via its own JSON Schema export, return a ``$ref``.

    Pydantic emits a self-contained schema; its nested-model definitions
    (``$defs`` in v2, ``definitions`` in v1) are lifted into ``components.schemas``.
    """
    name = tp.__name__
    if name in schemas:
        return _ref(name)
    if hasattr(tp, "model_json_schema"):  # Pydantic v2
        doc = tp.model_json_schema(ref_template="#/components/schemas/{model}")
    else:  # Pydantic v1
        doc = tp.schema(ref_template="#/components/schemas/{model}")
    defs = doc.pop("$defs", None) or doc.pop("definitions", None) or {}
    schemas[name] = doc  # reserve the name before recursing into nested defs
    for def_name, def_schema in defs.items():
        schemas.setdefault(def_name, def_schema)
    return _ref(name)


# ---------------------------------------------------------------------------
# Operation-level schema construction
# ---------------------------------------------------------------------------


def _param_location(param_specs: Dict[str, Any], param_name: str) -> str:
    """The HTTP location (``json_body`` / ``path`` / ``query`` / …) of a parameter.

    Reads :class:`qh.rules.TransformSpec.http_location` from the resolved
    ``param_specs`` map attached to the endpoint (the single source of truth).
    Defaults to ``json_body`` when unknown.
    """
    spec = param_specs.get(param_name) if param_specs else None
    location = getattr(spec, "http_location", None)
    return getattr(location, "value", "json_body")


def build_request_body_schema(
    func: Callable,
    param_specs: Dict[str, Any],
    schemas: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    """Build the JSON Schema object for a function's JSON-body parameters.

    Only parameters whose resolved HTTP location is the JSON body are included;
    path/query/header parameters are emitted separately by
    :func:`build_parameters`. A parameter with no default is ``required``.

    Returns:
        an object JSON Schema, or ``None`` when the function has no body
        parameters (e.g. a GET route whose arguments are all query parameters).
    """
    sig = inspect.signature(func)
    hints = _safe_type_hints(func)

    properties: Dict[str, Any] = {}
    required: List[str] = []
    for name, param in sig.parameters.items():
        if _param_location(param_specs, name) != "json_body":
            continue
        properties[name] = python_type_to_json_schema(hints.get(name, Any), schemas)
        if param.default is inspect.Parameter.empty:
            required.append(name)

    if not properties:
        return None
    obj: Dict[str, Any] = {"type": "object", "properties": properties}
    if required:
        obj["required"] = required
    return obj


def build_parameters(
    func: Callable,
    param_specs: Dict[str, Any],
    schemas: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Build OpenAPI ``parameters`` entries for a function's path/query arguments.

    Path parameters are always required; query parameters are required only
    when the Python parameter has no default.
    """
    sig = inspect.signature(func)
    hints = _safe_type_hints(func)

    parameters: List[Dict[str, Any]] = []
    for name, param in sig.parameters.items():
        location = _param_location(param_specs, name)
        if location not in ("path", "query"):
            continue
        spec = param_specs.get(name)
        parameters.append(
            {
                "name": getattr(spec, "http_name", None) or name,
                "in": location,
                "required": location == "path"
                or param.default is inspect.Parameter.empty,
                "schema": python_type_to_json_schema(hints.get(name, Any), schemas),
            }
        )
    return parameters


def build_response_schema(
    func: Callable,
    schemas: Dict[str, Any],
) -> Dict[str, Any]:
    """Build the JSON Schema for a function's return type.

    A missing return annotation yields the permissive empty schema; a ``None``
    return yields ``{"type": "null"}`` (``qh`` still replies with a JSON body).
    """
    hints = _safe_type_hints(func)
    return python_type_to_json_schema(hints.get("return", Any), schemas)


# ---------------------------------------------------------------------------
# Python signature metadata (x-python-* extensions)
# ---------------------------------------------------------------------------


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
    if hasattr(type_hint, "__name__"):
        return type_hint.__name__

    # Handle typing generics
    origin = get_origin(type_hint)
    args = get_args(type_hint)

    if origin is not None:
        origin_name = getattr(origin, "__name__", str(origin))
        if args:
            args_str = ", ".join(get_python_type_name(arg) for arg in args)
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
    type_hints = _safe_type_hints(func)

    parameters = []
    for param_name, param in sig.parameters.items():
        param_type = type_hints.get(param_name, param.annotation)

        param_info = {
            "name": param_name,
            "type": get_python_type_name(param_type),
            "required": param.default is inspect.Parameter.empty,
        }

        if param.default is not inspect.Parameter.empty:
            # Try to serialize default value
            default = param.default
            if isinstance(default, (str, int, float, bool, type(None))):
                param_info["default"] = default
            else:
                param_info["default"] = str(default)

        parameters.append(param_info)

    return_type = type_hints.get("return", sig.return_annotation)

    return {
        "name": func.__name__,
        "module": func.__module__,
        "parameters": parameters,
        "return_type": get_python_type_name(return_type),
        "docstring": inspect.getdoc(func),
    }


def generate_examples_for_function(func: Callable) -> List[Dict[str, Any]]:
    """
    Generate example requests/responses for a function.

    Uses type hints to generate sensible example values.
    """
    sig = inspect.signature(func)
    type_hints = _safe_type_hints(func)

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
        examples.append({"summary": "Basic example", "value": example_request})

    return examples


def _generate_example_value(type_hint: Any, param_name: str) -> Any:
    """Generate an example value for a given type."""
    if type_hint is inspect.Parameter.empty or type_hint is None:
        return "example_value"

    # Handle basic types
    if type_hint == int or type_hint == "int":
        # Use param name hints
        if "id" in param_name.lower():
            return 123
        elif "count" in param_name.lower() or "num" in param_name.lower():
            return 10
        return 42
    elif type_hint == str or type_hint == "str":
        if "name" in param_name.lower():
            return "example_name"
        elif "id" in param_name.lower():
            return "abc123"
        return "example"
    elif type_hint == float or type_hint == "float":
        return 3.14
    elif type_hint == bool or type_hint == "bool":
        return True
    elif type_hint == list or get_origin(type_hint) == list:
        args = get_args(type_hint)
        if args:
            item_example = _generate_example_value(args[0], "item")
            return [item_example] if item_example is not None else []
        return []
    elif type_hint == dict or get_origin(type_hint) == dict:
        return {"key": "value"}

    # For custom types, return a placeholder
    return None


# ---------------------------------------------------------------------------
# Whole-document enhancement
# ---------------------------------------------------------------------------


def enhance_openapi_schema(
    app: FastAPI,
    *,
    include_examples: bool = True,
    include_python_metadata: bool = True,
    include_schemas: bool = True,
    include_transformers: bool = False,
) -> Dict[str, Any]:
    """
    Generate an enhanced OpenAPI schema for a ``qh`` app.

    On top of FastAPI's base document this fills in what ``qh``'s
    ``Request``-based endpoints hide from FastAPI:

    - ``requestBody`` / ``parameters`` / ``responses`` JSON Schema derived from
      each wrapped function's Python type hints (``include_schemas``),
    - ``components.schemas`` for every dataclass / ``TypedDict`` / Pydantic
      model / ``NamedTuple`` / ``Enum`` referenced,
    - ``x-python-signature`` metadata (``include_python_metadata``),
    - request examples (``include_examples``).

    Args:
        app: the FastAPI application.
        include_examples: add example requests.
        include_python_metadata: add ``x-python-*`` extensions.
        include_schemas: derive ``requestBody`` / ``responses`` /
            ``components.schemas`` from the Python type hints.
        include_transformers: add (placeholder) transformation metadata.

    Returns:
        the enhanced OpenAPI schema dictionary.
    """
    schema = get_openapi(
        title=app.title,
        version=app.version,
        openapi_version=app.openapi_version,
        description=app.description,
        routes=app.routes,
    )

    from qh.app import inspect_routes

    routes = inspect_routes(app)
    component_schemas: Dict[str, Any] = {}

    for route_info in routes:
        func = route_info.get("function")
        if not func:
            continue

        path = route_info["path"]
        methods = route_info.get("methods", ["POST"])
        param_specs = route_info.get("param_specs", {}) or {}

        if path in ["/openapi.json", "/docs", "/redoc"]:
            continue

        path_item = schema.get("paths", {}).get(path, {})

        for method in methods:
            method_lower = method.lower()
            operation = path_item.get(method_lower, {})
            if not operation:
                continue

            if include_python_metadata:
                operation["x-python-signature"] = extract_function_signature(func)

            if include_schemas:
                _apply_operation_schemas(
                    operation, func, param_specs, method_lower, component_schemas
                )

            if include_examples:
                examples = generate_examples_for_function(func)
                if examples and "requestBody" in operation:
                    content = operation["requestBody"].setdefault("content", {})
                    json_content = content.setdefault("application/json", {})
                    json_content["examples"] = {
                        f"example_{i}": ex for i, ex in enumerate(examples)
                    }

            if include_transformers:
                operation["x-python-transformers"] = {
                    "note": "Type transformation metadata would go here"
                }

            path_item[method_lower] = operation

        schema["paths"][path] = path_item

    if include_schemas and component_schemas:
        components = schema.setdefault("components", {})
        components.setdefault("schemas", {}).update(component_schemas)

    return schema


def _apply_operation_schemas(
    operation: Dict[str, Any],
    func: Callable,
    param_specs: Dict[str, Any],
    method_lower: str,
    component_schemas: Dict[str, Any],
) -> None:
    """Fill an operation's ``requestBody`` / ``parameters`` / ``responses`` in place."""
    parameters = build_parameters(func, param_specs, component_schemas)
    if parameters:
        existing = operation.get("parameters", [])
        operation["parameters"] = existing + parameters

    if method_lower in ("post", "put", "patch"):
        body = build_request_body_schema(func, param_specs, component_schemas)
        if body is not None:
            request_body = operation.setdefault("requestBody", {})
            request_body["required"] = bool(body.get("required"))
            content = request_body.setdefault("content", {})
            content["application/json"] = {"schema": body}

    response = build_response_schema(func, component_schemas)
    responses = operation.setdefault("responses", {})
    ok = responses.setdefault("200", {"description": "Successful Response"})
    ok.setdefault("content", {})["application/json"] = {"schema": response}


def export_openapi(
    app: FastAPI,
    *,
    include_examples: bool = True,
    include_python_metadata: bool = True,
    include_schemas: bool = True,
    include_transformers: bool = False,
    output_file: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Export the enhanced OpenAPI schema, optionally writing it to a file.

    Args:
        app: the FastAPI application.
        include_examples: include example requests.
        include_python_metadata: include ``x-python-*`` extensions.
        include_schemas: derive ``requestBody`` / ``responses`` /
            ``components.schemas`` from the Python type hints.
        include_transformers: include transformation metadata.
        output_file: optional path to write the JSON document to.

    Returns:
        the enhanced OpenAPI schema dictionary.

    Example:
        >>> from qh import mk_app  # doctest: +SKIP
        >>> from qh.openapi import export_openapi  # doctest: +SKIP
        >>> app = mk_app([my_func])  # doctest: +SKIP
        >>> spec = export_openapi(app, include_examples=True)  # doctest: +SKIP
    """
    schema = enhance_openapi_schema(
        app,
        include_examples=include_examples,
        include_python_metadata=include_python_metadata,
        include_schemas=include_schemas,
        include_transformers=include_transformers,
    )

    if output_file:
        with open(output_file, "w") as f:
            json.dump(schema, f, indent=2)

    return schema


def install_enhanced_openapi(app: FastAPI, **enhance_kwargs: Any) -> FastAPI:
    """Make ``app`` serve the enhanced OpenAPI schema at its ``/openapi.json``.

    Overrides ``app.openapi`` so the document returned by FastAPI — and rendered
    by ``/docs`` and ``/redoc`` — carries the request/response JSON Schema and
    ``components.schemas`` derived from the wrapped functions' Python type hints.

    The override is **defensive**: if enhancement raises for any reason, it
    falls back to FastAPI's plain schema, so a converter bug can never turn
    ``/openapi.json`` into a 500.

    Args:
        app: the FastAPI application (typically the result of :func:`qh.mk_app`).
        **enhance_kwargs: forwarded to :func:`enhance_openapi_schema`.

    Returns:
        the same ``app``, for chaining.
    """

    def custom_openapi() -> Dict[str, Any]:
        if app.openapi_schema:
            return app.openapi_schema
        try:
            app.openapi_schema = enhance_openapi_schema(app, **enhance_kwargs)
        except Exception:
            app.openapi_schema = get_openapi(
                title=app.title,
                version=app.version,
                openapi_version=app.openapi_version,
                description=app.description,
                routes=app.routes,
            )
        return app.openapi_schema

    app.openapi = custom_openapi  # type: ignore[method-assign]
    return app
