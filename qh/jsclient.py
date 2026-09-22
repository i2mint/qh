"""
JavaScript and TypeScript client generation from OpenAPI specs.

Generates client code for calling qh HTTP services from JavaScript/TypeScript applications.
"""

from typing import Any, Dict, List, Optional
import json


#: Origin names whose parameterised form becomes a TypeScript array.
_SEQUENCE_ORIGINS = frozenset(
    {
        "list",
        "List",
        "tuple",
        "Tuple",
        "set",
        "Set",
        "frozenset",
        "FrozenSet",
        "Sequence",
        "Iterable",
        "Collection",
        "MutableSequence",
        "Iterator",
    }
)

#: Origin names whose parameterised form becomes a TypeScript Record.
_MAPPING_ORIGINS = frozenset(
    {"dict", "Dict", "Mapping", "MutableMapping", "OrderedDict"}
)


def python_type_to_ts_type(python_type: str) -> str:
    """
    Convert Python type annotation to TypeScript type.

    Args:
        python_type: Python type string (e.g., "int", "str", "list[int]")

    Returns:
        TypeScript type string
    """
    # Handle None/Optional
    if python_type == "None" or python_type == "NoneType":
        return "null"

    # Handle generics
    if python_type.startswith("Optional["):
        inner = python_type[9:-1]  # Extract inner type
        return f"{python_type_to_ts_type(inner)} | null"

    # PEP 604 unions arrive from the signature extractor as "UnionType[a, b, ...]",
    # and typing.Union as "Union[a, b, ...]". Both become a TypeScript union so an
    # `str | None` parameter types as `string | null` rather than collapsing to `any`.
    for prefix in ("UnionType[", "Union["):
        if python_type.startswith(prefix):
            members = _split_type_args(python_type[len(prefix) : -1])
            mapped = [python_type_to_ts_type(m) for m in members]
            # Dedupe while preserving order: `str | Sequence | None` has no repeats,
            # but `int | float` both map to `number` and one `number` is enough.
            seen, unique = set(), []
            for m in mapped:
                if m not in seen:
                    seen.add(m)
                    unique.append(m)
            return " | ".join(unique)

    # Sequence-ish generics: `Sequence[str]` -> `string[]`. Matching on the bare
    # origin name covers every spelling the signature extractor can produce
    # (`list`, `List`, `tuple`, `Sequence`, `Iterable`, ...) without a case each.
    if "[" in python_type:
        origin, inner = python_type.split("[", 1)
        inner = inner[:-1]
        if origin in _SEQUENCE_ORIGINS:
            members = _split_type_args(inner)
            if not members:
                return "any[]"
            if origin in ("tuple", "Tuple") and len(members) > 1:
                # A fixed-length tuple is a TS tuple type, not an array.
                if members[-1] == "...":
                    return f"{python_type_to_ts_type(members[0])}[]"
                return "[" + ", ".join(python_type_to_ts_type(m) for m in members) + "]"
            return f"{python_type_to_ts_type(members[0])}[]"
        if origin in _MAPPING_ORIGINS:
            members = _split_type_args(inner)
            value = python_type_to_ts_type(members[1]) if len(members) > 1 else "any"
            return f"Record<string, {value}>"

    # Basic types
    type_map = {
        "int": "number",
        "float": "number",
        "str": "string",
        "bool": "boolean",
        "list": "any[]",
        "tuple": "any[]",
        "set": "any[]",
        "Sequence": "any[]",
        "Iterable": "any[]",
        "dict": "Record<string, any>",
        "Mapping": "Record<string, any>",
        "Any": "any",
    }

    return type_map.get(python_type, "any")


def _split_type_args(s: str) -> List[str]:
    """Split "a, b[c, d], e" on its TOP-LEVEL commas only.

    A naive ``s.split(",")`` would cut ``dict[str, int]`` in half and produce two
    nonsense members, so nested brackets are tracked.

    >>> _split_type_args("str, NoneType")
    ['str', 'NoneType']
    >>> _split_type_args("str, dict[str, int], NoneType")
    ['str', 'dict[str, int]', 'NoneType']
    """
    parts, depth, current = [], 0, []
    for ch in s:
        if ch in "[(":
            depth += 1
        elif ch in "])":
            depth -= 1
        if ch == "," and depth == 0:
            parts.append("".join(current).strip())
            current = []
        else:
            current.append(ch)
    if "".join(current).strip():
        parts.append("".join(current).strip())
    return parts


def generate_ts_interface(name: str, signature_info: Dict[str, Any]) -> str:
    """
    Generate TypeScript interface for function parameters.

    Args:
        name: Function name
        signature_info: x-python-signature metadata

    Returns:
        TypeScript interface definition
    """
    params = signature_info.get("parameters", [])
    return_type = python_type_to_ts_type(signature_info.get("return_type", "any"))

    # Generate parameter interface
    param_props = []
    for param in params:
        param_name = param["name"]
        param_type = python_type_to_ts_type(param["type"])
        optional = "" if param.get("required", True) else "?"
        param_props.append(f"  {param_name}{optional}: {param_type};")

    interface_name = f"{name.capitalize()}Params"
    interface = f"export interface {interface_name} {{\n"
    interface += "\n".join(param_props)
    interface += "\n}\n"

    return interface, interface_name, return_type


def generate_js_function(
    name: str,
    path: str,
    method: str,
    signature_info: Optional[Dict[str, Any]] = None,
    use_axios: bool = False,
) -> str:
    """
    Generate JavaScript function for calling an endpoint.

    Args:
        name: Function name
        path: HTTP path
        method: HTTP method
        signature_info: Optional x-python-signature metadata
        use_axios: Use axios instead of fetch

    Returns:
        JavaScript function code
    """
    method_lower = method.lower()

    # Extract path parameters
    import re

    path_params = re.findall(r"\{(\w+)\}", path)

    # Generate function signature
    if signature_info:
        params = signature_info.get("parameters", [])
        param_names = [p["name"] for p in params]
    else:
        param_names = path_params + ["data"]

    # Build JSDoc comment
    jsdoc = f"  /**\n"
    if signature_info and signature_info.get("docstring"):
        jsdoc += f"   * {signature_info['docstring']}\n"
    if signature_info:
        for param in signature_info.get("parameters", []):
            param_type = python_type_to_ts_type(param["type"])
            jsdoc += f"   * @param {{{param_type}}} {param['name']}\n"
        return_type = python_type_to_ts_type(signature_info.get("return_type", "any"))
        jsdoc += f"   * @returns {{Promise<{return_type}>}}\n"
    jsdoc += "   */\n"

    # Generate function body
    func = jsdoc
    func += f"  async {name}({', '.join(param_names)}) {{\n"

    # Build URL with path parameters
    func += f"    let url = `${{this.baseUrl}}{path}`;\n"
    for param in path_params:
        func += f"    url = url.replace('{{{param}}}', {param});\n"

    # Separate path params from body/query params
    body_params = [p for p in param_names if p not in path_params]

    if use_axios:
        # Axios implementation
        if method_lower == "get" and body_params:
            func += f"    const params = {{ {', '.join(body_params)} }};\n"
            func += f"    const response = await this.axios.get(url, {{ params }});\n"
        elif method_lower in ["post", "put", "patch"] and body_params:
            func += f"    const data = {{ {', '.join(body_params)} }};\n"
            func += (
                f"    const response = await this.axios.{method_lower}(url, data);\n"
            )
        else:
            func += f"    const response = await this.axios.{method_lower}(url);\n"
        func += "    return response.data;\n"
    else:
        # Fetch implementation
        if method_lower == "get" and body_params:
            func += f"    const params = new URLSearchParams({{ {', '.join(body_params)} }});\n"
            func += "    url += '?' + params.toString();\n"
            func += "    const response = await fetch(url);\n"
        elif method_lower in ["post", "put", "patch"] and body_params:
            func += f"    const data = {{ {', '.join(body_params)} }};\n"
            func += "    const response = await fetch(url, {\n"
            func += f"      method: '{method.upper()}',\n"
            func += "      headers: { 'Content-Type': 'application/json' },\n"
            func += "      body: JSON.stringify(data)\n"
            func += "    });\n"
        else:
            func += f"    const response = await fetch(url, {{ method: '{method.upper()}' }});\n"
        func += "    if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);\n"
        func += "    return await response.json();\n"

    func += "  }\n"

    return func


def _jsdoc(docstring: str, extra: Optional[List[str]] = None) -> str:
    """Render a JSDoc block, safely.

    Two things the previous one-line version got wrong. A docstring spanning several
    lines was emitted with only its first line prefixed by ``*``, so every later line
    sat bare inside the comment; and a docstring containing ``*/`` -- a doctest or a
    regex is enough -- closed the comment early and the rest of the docstring became
    executable garbage. Neutralising ``*/`` is what makes this safe on arbitrary text.

    >>> print(_jsdoc("One line."))
      /**
       * One line.
       */
    >>> "*\u200b/" in _jsdoc("ends a comment: */ here")
    True
    """
    body = (docstring or "").replace("*/", "*\u200b/")  # zero-width space defuses it
    out = ["  /**"]
    for line in body.splitlines() or [""]:
        out.append(f"   * {line}".rstrip())
    for line in extra or []:
        out.append(f"   * {line}")
    out.append("   */")
    return "\n".join(out)


def _ts_params(params: List[Dict[str, Any]]) -> List[str]:
    """Typed parameter list, required first, optional marked ``?``.

    TypeScript requires optional parameters to follow required ones, and a parameter
    with a Python default must not be mandatory on the client -- the whole point of
    the default is that the caller may omit it. Sorting is stable, so parameters keep
    their declaration order within each group.

    >>> _ts_params([{"name": "a", "type": "str", "required": True},
    ...             {"name": "b", "type": "int", "required": False}])
    ['a: string', 'b?: number']
    >>> _ts_params([{"name": "b", "type": "int", "required": False},
    ...             {"name": "a", "type": "str", "required": True}])
    ['a: string', 'b?: number']
    """
    ordered = sorted(params, key=lambda p: not p.get("required", True))
    return [
        f"{p['name']}{'' if p.get('required', True) else '?'}: "
        f"{python_type_to_ts_type(p['type'])}"
        for p in ordered
    ]


def generate_ts_method(
    name: str,
    path: str,
    method: str,
    signature_info: Optional[Dict[str, Any]] = None,
    use_axios: bool = False,
) -> str:
    """Generate the TypeScript class method for one endpoint -- no interface.

    Split out from :func:`generate_ts_function` because the assembler needs the method
    alone. It used to get it by splitting the combined string on its first blank line,
    which silently broke on a zero-parameter function: that interface is
    ``export interface FooParams {\n\n}``, whose blank line comes first, so the split
    handed back a stray ``}`` that closed the client class early. Every method after
    the first no-argument endpoint landed outside the class.

    Args:
        name: Function name
        path: HTTP path
        method: HTTP method
        signature_info: Optional x-python-signature metadata
        use_axios: Use axios instead of fetch

    Returns:
        TypeScript method source, indented for a class body
    """
    import re

    method_lower = method.lower()
    path_params = re.findall(r"\{(\w+)\}", path)
    params = signature_info.get("parameters", []) if signature_info else []
    return_type = python_type_to_ts_type(
        (signature_info or {}).get("return_type", "any")
    )

    func = _jsdoc((signature_info or {}).get("docstring", "")) + "\n"
    func += (
        f"  async {name}({', '.join(_ts_params(params))}): Promise<{return_type}> {{\n"
    )

    func += f"    let url = `${{this.baseUrl}}{path}`;\n"
    for param in path_params:
        func += f"    url = url.replace('{{{param}}}', String({param}));\n"

    body_params = [p["name"] for p in params if p["name"] not in path_params]
    # An omitted optional parameter is `undefined`. JSON.stringify drops undefined
    # keys, so the server sees the key as absent and applies its own Python default --
    # exactly the intent. A query string has no such rule, hence the explicit filter
    # below; without it an omitted parameter is sent as the literal text "undefined".
    obj = "{ " + ", ".join(body_params) + " }"

    if use_axios:
        if method_lower == "get" and body_params:
            func += f"    const params = _defined({obj});\n"
            func += (
                f"    const response = await this.axios.get<{return_type}>"
                "(url, { params });\n"
            )
            func += "    return response.data;\n"
        elif method_lower in ["post", "put", "patch"] and body_params:
            func += f"    const data = {obj};\n"
            func += (
                f"    const response = await this.axios.{method_lower}"
                f"<{return_type}>(url, data);\n"
            )
            func += "    return response.data;\n"
        else:
            func += (
                f"    const response = await this.axios.{method_lower}"
                f"<{return_type}>(url);\n"
            )
            func += "    return response.data;\n"
    else:
        if method_lower == "get" and body_params:
            func += f"    const params = new URLSearchParams(_defined({obj}));\n"
            func += "    const qs = params.toString();\n"
            func += "    if (qs) url += '?' + qs;\n"
            func += "    const response = await fetch(url);\n"
        elif method_lower in ["post", "put", "patch"] and body_params:
            func += f"    const data = {obj};\n"
            func += "    const response = await fetch(url, {\n"
            func += f"      method: '{method.upper()}',\n"
            func += "      headers: { 'Content-Type': 'application/json' },\n"
            func += "      body: JSON.stringify(data)\n"
            func += "    });\n"
        else:
            func += (
                "    const response = await fetch(url, "
                f"{{ method: '{method.upper()}' }});\n"
            )
        func += (
            "    if (!response.ok) throw new Error("
            "`HTTP error! status: ${response.status}`);\n"
        )
        func += f"    return await response.json() as {return_type};\n"

    func += "  }\n"
    return func


def generate_ts_function(
    name: str,
    path: str,
    method: str,
    signature_info: Optional[Dict[str, Any]] = None,
    use_axios: bool = False,
) -> str:
    """
    Generate TypeScript function with type annotations, preceded by its interface.

    Args:
        name: Function name
        path: HTTP path
        method: HTTP method
        signature_info: Optional x-python-signature metadata
        use_axios: Use axios instead of fetch

    Returns:
        TypeScript function code
    """
    if not signature_info:
        # Fallback to JavaScript version
        return generate_js_function(name, path, method, signature_info, use_axios)

    interface, _interface_name, _return_type = generate_ts_interface(
        name, signature_info
    )
    return (
        interface
        + "\n"
        + generate_ts_method(name, path, method, signature_info, use_axios)
    )


def export_js_client(
    openapi_spec: Dict[str, Any],
    *,
    class_name: str = "ApiClient",
    use_axios: bool = False,
    base_url: str = "http://localhost:8000",
) -> str:
    """
    Generate JavaScript client class from OpenAPI spec.

    Args:
        openapi_spec: OpenAPI specification dictionary
        class_name: Name for the generated class
        use_axios: Use axios instead of fetch
        base_url: Default base URL

    Returns:
        JavaScript code as string

    Example:

        >>> from qh import mk_app, export_openapi  # doctest: +SKIP
        >>> from qh.jsclient import export_js_client  # doctest: +SKIP
        >>> app = mk_app([add, subtract])  # doctest: +SKIP
        >>> spec = export_openapi(app)  # doctest: +SKIP
        >>> js_code = export_js_client(spec, use_axios=True)  # doctest: +SKIP
    """
    paths = openapi_spec.get("paths", {})

    # Generate class header
    code = ""
    if use_axios:
        code = f"import axios from 'axios';\n\n"
    code += f"/**\n * Generated API client\n */\n"
    code += f"export class {class_name} {{\n"
    code += f"  constructor(baseUrl = '{base_url}') {{\n"
    code += "    this.baseUrl = baseUrl;\n"
    if use_axios:
        code += "    this.axios = axios.create({ baseURL: baseUrl });\n"
    code += "  }\n\n"

    # Generate methods
    for path, path_item in paths.items():
        if path in ["/openapi.json", "/docs", "/redoc"]:
            continue

        for method, operation in path_item.items():
            if method.upper() not in ["GET", "POST", "PUT", "DELETE", "PATCH"]:
                continue

            # Get function name from x-python-signature or operation_id
            signature_info = operation.get("x-python-signature")
            if signature_info:
                func_name = signature_info["name"]
            else:
                operation_id = operation.get("operationId", "")
                func_name = (
                    operation_id.split("_")[0]
                    if operation_id
                    else path.strip("/").replace("/", "_")
                )

            # Generate function
            func_code = generate_js_function(
                func_name, path, method.upper(), signature_info, use_axios
            )
            code += func_code + "\n"

    code += "}\n"

    return code


#: Emitted only into clients that have at least one GET endpoint with parameters.
#: A query string has no equivalent of JSON.stringify's "drop the undefined keys"
#: rule, so without this an omitted optional parameter travels as the six characters
#: "undefined" and the server parses that as a real value.
_DEFINED_HELPER_TS = """\
/** Drop keys whose value is undefined, so omitted optional parameters are not sent. */
function _defined(o: Record<string, any>): Record<string, string> {
  return Object.fromEntries(
    Object.entries(o).filter(([, v]) => v !== undefined && v !== null)
      .map(([k, v]) => [k, String(v)])
  );
}

"""


def _needs_defined_helper(paths: Dict[str, Any]) -> bool:
    """Whether any GET endpoint in ``paths`` carries parameters.

    >>> _needs_defined_helper({})
    False
    """
    for path, path_item in paths.items():
        if path in ["/openapi.json", "/docs", "/redoc"]:
            continue
        for method, operation in path_item.items():
            if method.lower() != "get":
                continue
            sig = operation.get("x-python-signature") or {}
            if [
                p
                for p in sig.get("parameters", [])
                if "{" + p["name"] + "}" not in path
            ]:
                return True
    return False


def export_ts_client(
    openapi_spec: Dict[str, Any],
    *,
    class_name: str = "ApiClient",
    use_axios: bool = False,
    base_url: str = "http://localhost:8000",
) -> str:
    """
    Generate TypeScript client class from OpenAPI spec.

    Args:
        openapi_spec: OpenAPI specification dictionary
        class_name: Name for the generated class
        use_axios: Use axios instead of fetch
        base_url: Default base URL

    Returns:
        TypeScript code as string

    Example:

        >>> from qh import mk_app, export_openapi  # doctest: +SKIP
        >>> from qh.jsclient import export_ts_client  # doctest: +SKIP
        >>> app = mk_app([add, subtract])  # doctest: +SKIP
        >>> spec = export_openapi(app, include_python_metadata=True)  # doctest: +SKIP
        >>> ts_code = export_ts_client(spec, use_axios=True)  # doctest: +SKIP
    """
    paths = openapi_spec.get("paths", {})

    # Generate imports
    code = ""
    if use_axios:
        code = "import axios, { AxiosInstance } from 'axios';\n\n"

    # Generate interfaces first
    interfaces = []
    for path, path_item in paths.items():
        if path in ["/openapi.json", "/docs", "/redoc"]:
            continue

        for method, operation in path_item.items():
            if method.upper() not in ["GET", "POST", "PUT", "DELETE", "PATCH"]:
                continue

            signature_info = operation.get("x-python-signature")
            if signature_info:
                interface, _, _ = generate_ts_interface(
                    signature_info["name"], signature_info
                )
                interfaces.append(interface)

    if interfaces:
        code += "\n".join(interfaces) + "\n"

    # Generate class
    if _needs_defined_helper(paths):
        code += _DEFINED_HELPER_TS
    code += f"/**\n * Generated API client\n */\n"
    code += f"export class {class_name} {{\n"
    code += "  private baseUrl: string;\n"
    if use_axios:
        code += "  private axios: AxiosInstance;\n"
    code += "\n"
    code += f"  constructor(baseUrl: string = '{base_url}') {{\n"
    code += "    this.baseUrl = baseUrl;\n"
    if use_axios:
        code += "    this.axios = axios.create({ baseURL: baseUrl });\n"
    code += "  }\n\n"

    # Generate methods
    for path, path_item in paths.items():
        if path in ["/openapi.json", "/docs", "/redoc"]:
            continue

        for method, operation in path_item.items():
            if method.upper() not in ["GET", "POST", "PUT", "PATCH", "DELETE"]:
                continue

            signature_info = operation.get("x-python-signature")
            if signature_info:
                func_name = signature_info["name"]
            else:
                operation_id = operation.get("operationId", "")
                func_name = (
                    operation_id.split("_")[0]
                    if operation_id
                    else path.strip("/").replace("/", "_")
                )

            # The method only -- its interface was emitted above. Asking for the
            # combined form and splitting it back apart is what used to leak a
            # stray closing brace into the class body.
            code += (
                generate_ts_method(
                    func_name, path, method.upper(), signature_info, use_axios
                )
                + "\n"
            )

    code += "}\n"

    return code
