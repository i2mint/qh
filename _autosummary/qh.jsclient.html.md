# qh.jsclient

JavaScript and TypeScript client generation from OpenAPI specs.

Generates client code for calling qh HTTP services from JavaScript/TypeScript applications.

### Functions

| [`export_js_client`](#qh.jsclient.export_js_client)(openapi_spec, \*[, ...])       | Generate JavaScript client class from OpenAPI spec.    |
|--------------------------------------------------------------------------------------------------|--------------------------------------------------------|
| [`export_ts_client`](#qh.jsclient.export_ts_client)(openapi_spec, \*[, ...])       | Generate TypeScript client class from OpenAPI spec.    |
| [`generate_js_function`](#qh.jsclient.generate_js_function)(name, path, method[, ...]) | Generate JavaScript function for calling an endpoint.  |
| [`generate_ts_function`](#qh.jsclient.generate_ts_function)(name, path, method[, ...]) | Generate TypeScript function for calling an endpoint.  |
| [`generate_ts_interface`](#qh.jsclient.generate_ts_interface)(name, signature_info)     | Generate TypeScript interface for function parameters. |
| [`python_type_to_ts_type`](#qh.jsclient.python_type_to_ts_type)(python_type)             | Convert Python type annotation to TypeScript type.     |

### qh.jsclient.export_js_client(openapi_spec, , class_name='ApiClient', use_axios=False, base_url='http://localhost:8000')

Generate JavaScript client class from OpenAPI spec.

* **Parameters:**
  * **openapi_spec** ([`Dict`](https://docs.python.org/3/library/typing.html#typing.Dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)]) – OpenAPI specification dictionary
  * **class_name** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – Name for the generated class
  * **use_axios** ([`bool`](https://docs.python.org/3/builtins/functions.html#bool)) – Use axios instead of fetch
  * **base_url** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – Default base URL
* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)
* **Returns:**
  JavaScript code as string

### Example

```pycon
>>> from qh import mk_app, export_openapi
>>> from qh.jsclient import export_js_client
>>> app = mk_app([add, subtract])
>>> spec = export_openapi(app)
>>> js_code = export_js_client(spec, use_axios=True)
```

### qh.jsclient.export_ts_client(openapi_spec, , class_name='ApiClient', use_axios=False, base_url='http://localhost:8000')

Generate TypeScript client class from OpenAPI spec.

* **Parameters:**
  * **openapi_spec** ([`Dict`](https://docs.python.org/3/library/typing.html#typing.Dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)]) – OpenAPI specification dictionary
  * **class_name** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – Name for the generated class
  * **use_axios** ([`bool`](https://docs.python.org/3/builtins/functions.html#bool)) – Use axios instead of fetch
  * **base_url** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – Default base URL
* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)
* **Returns:**
  TypeScript code as string

### Example

```pycon
>>> from qh import mk_app, export_openapi
>>> from qh.jsclient import export_ts_client
>>> app = mk_app([add, subtract])
>>> spec = export_openapi(app, include_python_metadata=True)
>>> ts_code = export_ts_client(spec, use_axios=True)
```

### qh.jsclient.generate_js_function(name, path, method, signature_info=None, use_axios=False)

Generate JavaScript function for calling an endpoint.

* **Parameters:**
  * **name** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – Function name
  * **path** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – HTTP path
  * **method** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – HTTP method
  * **signature_info** ([`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`Dict`](https://docs.python.org/3/library/typing.html#typing.Dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)]]) – Optional x-python-signature metadata
  * **use_axios** ([`bool`](https://docs.python.org/3/builtins/functions.html#bool)) – Use axios instead of fetch
* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)
* **Returns:**
  JavaScript function code

### qh.jsclient.generate_ts_function(name, path, method, signature_info=None, use_axios=False)

Generate TypeScript function for calling an endpoint.

* **Parameters:**
  * **name** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – Function name
  * **path** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – HTTP path
  * **method** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – HTTP method
  * **signature_info** ([`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`Dict`](https://docs.python.org/3/library/typing.html#typing.Dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)]]) – Optional x-python-signature metadata
  * **use_axios** ([`bool`](https://docs.python.org/3/builtins/functions.html#bool)) – Use axios instead of fetch
* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)
* **Returns:**
  TypeScript function code with type annotations

### qh.jsclient.generate_ts_interface(name, signature_info)

Generate TypeScript interface for function parameters.

* **Parameters:**
  * **name** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – Function name
  * **signature_info** ([`Dict`](https://docs.python.org/3/library/typing.html#typing.Dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)]) – x-python-signature metadata
* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)
* **Returns:**
  TypeScript interface definition

### qh.jsclient.python_type_to_ts_type(python_type)

Convert Python type annotation to TypeScript type.

* **Parameters:**
  **python_type** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – Python type string (e.g., “int”, “str”, “list[int]”)
* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)
* **Returns:**
  TypeScript type string
