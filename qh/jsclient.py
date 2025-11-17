"""
JavaScript and TypeScript client generation from OpenAPI specs.

Generates client code for calling qh HTTP services from JavaScript/TypeScript applications.
"""

from typing import Any, Dict, List, Optional
import json


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

    if python_type.startswith("list[") or python_type.startswith("List["):
        inner = python_type.split("[")[1][:-1]
        return f"{python_type_to_ts_type(inner)}[]"

    if python_type.startswith("dict[") or python_type.startswith("Dict["):
        # Simplified - could be more sophisticated
        return "Record<string, any>"

    # Basic types
    type_map = {
        "int": "number",
        "float": "number",
        "str": "string",
        "bool": "boolean",
        "list": "any[]",
        "dict": "Record<string, any>",
        "Any": "any",
    }

    return type_map.get(python_type, "any")


def generate_ts_interface(
    name: str,
    signature_info: Dict[str, Any]
) -> str:
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
    path_params = re.findall(r'\{(\w+)\}', path)

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
        if method_lower == 'get' and body_params:
            func += f"    const params = {{ {', '.join(body_params)} }};\n"
            func += f"    const response = await this.axios.get(url, {{ params }});\n"
        elif method_lower in ['post', 'put', 'patch'] and body_params:
            func += f"    const data = {{ {', '.join(body_params)} }};\n"
            func += f"    const response = await this.axios.{method_lower}(url, data);\n"
        else:
            func += f"    const response = await this.axios.{method_lower}(url);\n"
        func += "    return response.data;\n"
    else:
        # Fetch implementation
        if method_lower == 'get' and body_params:
            func += f"    const params = new URLSearchParams({{ {', '.join(body_params)} }});\n"
            func += "    url += '?' + params.toString();\n"
            func += "    const response = await fetch(url);\n"
        elif method_lower in ['post', 'put', 'patch'] and body_params:
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


def generate_ts_function(
    name: str,
    path: str,
    method: str,
    signature_info: Optional[Dict[str, Any]] = None,
    use_axios: bool = False,
) -> str:
    """
    Generate TypeScript function for calling an endpoint.

    Args:
        name: Function name
        path: HTTP path
        method: HTTP method
        signature_info: Optional x-python-signature metadata
        use_axios: Use axios instead of fetch

    Returns:
        TypeScript function code with type annotations
    """
    if not signature_info:
        # Fallback to JavaScript version
        return generate_js_function(name, path, method, signature_info, use_axios)

    # Generate interface
    interface, interface_name, return_type = generate_ts_interface(name, signature_info)

    # Generate function with types
    method_lower = method.lower()
    import re
    path_params = re.findall(r'\{(\w+)\}', path)

    params = signature_info.get("parameters", [])

    # Build function signature with types
    func_params = []
    for param in params:
        param_name = param["name"]
        param_type = python_type_to_ts_type(param["type"])
        func_params.append(f"{param_name}: {param_type}")

    # Generate JSDoc
    jsdoc = f"  /**\n"
    if signature_info.get("docstring"):
        jsdoc += f"   * {signature_info['docstring']}\n"
    jsdoc += "   */\n"

    func = jsdoc
    func += f"  async {name}({', '.join(func_params)}): Promise<{return_type}> {{\n"

    # Build URL
    func += f"    let url = `${{this.baseUrl}}{path}`;\n"
    for param in path_params:
        func += f"    url = url.replace('{{{param}}}', String({param}));\n"

    # Separate params
    param_names = [p["name"] for p in params]
    body_params = [p for p in param_names if p not in path_params]

    if use_axios:
        # Axios implementation
        if method_lower == 'get' and body_params:
            func += f"    const params = {{ {', '.join(body_params)} }};\n"
            func += f"    const response = await this.axios.get<{return_type}>(url, {{ params }});\n"
            func += "    return response.data;\n"
        elif method_lower in ['post', 'put', 'patch'] and body_params:
            func += f"    const data = {{ {', '.join(body_params)} }};\n"
            func += f"    const response = await this.axios.{method_lower}<{return_type}>(url, data);\n"
            func += "    return response.data;\n"
        else:
            func += f"    const response = await this.axios.{method_lower}<{return_type}>(url);\n"
            func += "    return response.data;\n"
    else:
        # Fetch implementation
        if method_lower == 'get' and body_params:
            func += f"    const params = new URLSearchParams({{ {', '.join(body_params)} }});\n"
            func += "    url += '?' + params.toString();\n"
            func += "    const response = await fetch(url);\n"
        elif method_lower in ['post', 'put', 'patch'] and body_params:
            func += f"    const data = {{ {', '.join(body_params)} }};\n"
            func += "    const response = await fetch(url, {\n"
            func += f"      method: '{method.upper()}',\n"
            func += "      headers: {{ 'Content-Type': 'application/json' }},\n"
            func += "      body: JSON.stringify(data)\n"
            func += "    });\n"
        else:
            func += f"    const response = await fetch(url, {{ method: '{method.upper()}' }});\n"
        func += "    if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);\n"
        func += f"    return await response.json() as {return_type};\n"

    func += "  }\n"

    return interface + "\n" + func


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
        >>> from qh import mk_app, export_openapi
        >>> from qh.jsclient import export_js_client
        >>> app = mk_app([add, subtract])
        >>> spec = export_openapi(app)
        >>> js_code = export_js_client(spec, use_axios=True)
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
        if path in ['/openapi.json', '/docs', '/redoc']:
            continue

        for method, operation in path_item.items():
            if method.upper() not in ['GET', 'POST', 'PUT', 'DELETE', 'PATCH']:
                continue

            # Get function name from x-python-signature or operation_id
            signature_info = operation.get('x-python-signature')
            if signature_info:
                func_name = signature_info['name']
            else:
                operation_id = operation.get('operationId', '')
                func_name = operation_id.split('_')[0] if operation_id else path.strip('/').replace('/', '_')

            # Generate function
            func_code = generate_js_function(
                func_name, path, method.upper(), signature_info, use_axios
            )
            code += func_code + "\n"

    code += "}\n"

    return code


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
        >>> from qh import mk_app, export_openapi
        >>> from qh.jsclient import export_ts_client
        >>> app = mk_app([add, subtract])
        >>> spec = export_openapi(app, include_python_metadata=True)
        >>> ts_code = export_ts_client(spec, use_axios=True)
    """
    paths = openapi_spec.get("paths", {})

    # Generate imports
    code = ""
    if use_axios:
        code = "import axios, { AxiosInstance } from 'axios';\n\n"

    # Generate interfaces first
    interfaces = []
    for path, path_item in paths.items():
        if path in ['/openapi.json', '/docs', '/redoc']:
            continue

        for method, operation in path_item.items():
            if method.upper() not in ['GET', 'POST', 'PUT', 'DELETE', 'PATCH']:
                continue

            signature_info = operation.get('x-python-signature')
            if signature_info:
                interface, _, _ = generate_ts_interface(
                    signature_info['name'], signature_info
                )
                interfaces.append(interface)

    if interfaces:
        code += "\n".join(interfaces) + "\n"

    # Generate class
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
        if path in ['/openapi.json', '/docs', '/redoc']:
            continue

        for method, operation in path_item.items():
            if method.upper() not in ['GET', 'POST', 'PUT', 'PATCH', 'DELETE']:
                continue

            signature_info = operation.get('x-python-signature')
            if signature_info:
                func_name = signature_info['name']
            else:
                operation_id = operation.get('operationId', '')
                func_name = operation_id.split('_')[0] if operation_id else path.strip('/').replace('/', '_')

            func_code = generate_ts_function(
                func_name, path, method.upper(), signature_info, use_axios
            )
            # Extract just the function part (skip interface)
            if '\n\n' in func_code:
                func_code = func_code.split('\n\n', 1)[1]
            code += func_code + "\n"

    code += "}\n"

    return code
