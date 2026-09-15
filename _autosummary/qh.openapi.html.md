# qh.openapi

OpenAPI generation for qh — including JSON Schema derived from Python type hints.

`qh` builds every route with a generic `endpoint(request: Request)` signature
(see [`qh.endpoint`](qh.endpoint.html.md#module-qh.endpoint)): the wrapped function’s real parameters and return type
are parsed *manually* from the request body, which makes them invisible to
FastAPI’s own OpenAPI machinery. Out of the box, therefore, `/openapi.json`
lists routes and docstrings but emits empty `{}` request/response schemas and
no `components.schemas`.

This module closes that gap. It introspects each wrapped function’s Python type
hints and derives a complete OpenAPI document:

- `requestBody` — a JSON Schema object built from the JSON-body parameters,
- `parameters` — path/query parameters,
- `responses` — a JSON Schema for the return type,
- `components.schemas` — one named schema per dataclass / `TypedDict` /
  Pydantic model / `NamedTuple` / `Enum` encountered, referenced via `$ref`,
- `x-python-*` extensions — Python signature metadata for bidirectional
  Python ↔ HTTP transformation.

The whole thing is **additive**: the request-handling path is untouched, and
[`install_enhanced_openapi()`](#qh.openapi.install_enhanced_openapi) falls back to FastAPI’s plain schema if
enhancement ever raises — so a converter bug can never break `/openapi.json`.

Public surface:

- [`python_type_to_json_schema()`](#qh.openapi.python_type_to_json_schema) — the Python-type-hint → JSON Schema converter.
- [`enhance_openapi_schema()`](#qh.openapi.enhance_openapi_schema) — full enhanced OpenAPI document for an app.
- [`export_openapi()`](#qh.openapi.export_openapi) — [`enhance_openapi_schema()`](#qh.openapi.enhance_openapi_schema) plus optional file output.
- [`install_enhanced_openapi()`](#qh.openapi.install_enhanced_openapi) — make an app serve the enhanced doc at
  `/openapi.json` (and render it in `/docs`).

### Functions

| [`build_parameters`](#qh.openapi.build_parameters)(func, param_specs, schemas)       | Build OpenAPI `parameters` entries for a function's path/query arguments.   |
|-----------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------|
| [`build_request_body_schema`](#qh.openapi.build_request_body_schema)(func, param_specs, ...)  | Build the JSON Schema object for a function's JSON-body parameters.         |
| [`build_response_schema`](#qh.openapi.build_response_schema)(func, schemas)               | Build the JSON Schema for a function's return type.                         |
| [`enhance_openapi_schema`](#qh.openapi.enhance_openapi_schema)(app, \*[, ...])             | Generate an enhanced OpenAPI schema for a `qh` app.                         |
| [`export_openapi`](#qh.openapi.export_openapi)(app, \*[, include_examples, ...])   | Export the enhanced OpenAPI schema, optionally writing it to a file.        |
| [`extract_function_signature`](#qh.openapi.extract_function_signature)(func)                   | Extract detailed signature information from a function.                     |
| [`generate_examples_for_function`](#qh.openapi.generate_examples_for_function)(func)               | Generate example requests/responses for a function.                         |
| [`get_python_type_name`](#qh.openapi.get_python_type_name)(type_hint)                    | Get a string representation of a Python type.                               |
| [`install_enhanced_openapi`](#qh.openapi.install_enhanced_openapi)(app, \*\*enhance_kwargs)  | Make `app` serve the enhanced OpenAPI schema at its `/openapi.json`.        |
| [`python_type_to_json_schema`](#qh.openapi.python_type_to_json_schema)(type_hint, schemas, \*) | Convert a Python type hint to a JSON Schema fragment.                       |

### qh.openapi.build_parameters(func, param_specs, schemas)

Build OpenAPI `parameters` entries for a function’s path/query arguments.

Path parameters are always required; query parameters are required only
when the Python parameter has no default.

* **Return type:**
  [`List`](https://docs.python.org/3/library/typing.html#typing.List)[[`Dict`](https://docs.python.org/3/library/typing.html#typing.Dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)]]

### qh.openapi.build_request_body_schema(func, param_specs, schemas)

Build the JSON Schema object for a function’s JSON-body parameters.

Only parameters whose resolved HTTP location is the JSON body are included;
path/query/header parameters are emitted separately by
[`build_parameters()`](#qh.openapi.build_parameters). A parameter with no default is `required`.

* **Parameters:**
  * **func** ([`Callable`](https://docs.python.org/3/library/typing.html#typing.Callable)) – The function whose parameters are being described.
  * **param_specs** ([`Dict`](https://docs.python.org/3/library/typing.html#typing.Dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)]) – Parameter name to `TransformSpec`, deciding each
    parameter’s HTTP location (see `_param_location`).
  * **schemas** ([`Dict`](https://docs.python.org/3/library/typing.html#typing.Dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)]) – The mutable `components.schemas` accumulator, passed
    through to `python_type_to_json_schema` for composite types.
* **Return type:**
  [`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`Dict`](https://docs.python.org/3/library/typing.html#typing.Dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)]]
* **Returns:**
  an object JSON Schema, or `None` when the function has no body
  parameters (e.g. a GET route whose arguments are all query parameters).

### qh.openapi.build_response_schema(func, schemas)

Build the JSON Schema for a function’s return type.

A missing return annotation yields the permissive empty schema; a `None`
return yields `{"type": "null"}` (`qh` still replies with a JSON body).

* **Return type:**
  [`Dict`](https://docs.python.org/3/library/typing.html#typing.Dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)]

### qh.openapi.enhance_openapi_schema(app, , include_examples=True, include_python_metadata=True, include_schemas=True, include_transformers=False)

Generate an enhanced OpenAPI schema for a `qh` app.

On top of FastAPI’s base document this fills in what `qh`’s
`Request`-based endpoints hide from FastAPI:

- `requestBody` / `parameters` / `responses` JSON Schema derived from
  each wrapped function’s Python type hints (`include_schemas`),
- `components.schemas` for every dataclass / `TypedDict` / Pydantic
  model / `NamedTuple` / `Enum` referenced,
- `x-python-signature` metadata (`include_python_metadata`),
- request examples (`include_examples`).

* **Parameters:**
  * **app** (`FastAPI`) – the FastAPI application.
  * **include_examples** ([`bool`](https://docs.python.org/3/builtins/functions.html#bool)) – add example requests.
  * **include_python_metadata** ([`bool`](https://docs.python.org/3/builtins/functions.html#bool)) – add `x-python-*` extensions.
  * **include_schemas** ([`bool`](https://docs.python.org/3/builtins/functions.html#bool)) – derive `requestBody` / `responses` /
    `components.schemas` from the Python type hints.
  * **include_transformers** ([`bool`](https://docs.python.org/3/builtins/functions.html#bool)) – add (placeholder) transformation metadata.
* **Return type:**
  [`Dict`](https://docs.python.org/3/library/typing.html#typing.Dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)]
* **Returns:**
  the enhanced OpenAPI schema dictionary.

### qh.openapi.export_openapi(app, , include_examples=True, include_python_metadata=True, include_schemas=True, include_transformers=False, output_file=None)

Export the enhanced OpenAPI schema, optionally writing it to a file.

* **Parameters:**
  * **app** (`FastAPI`) – the FastAPI application.
  * **include_examples** ([`bool`](https://docs.python.org/3/builtins/functions.html#bool)) – include example requests.
  * **include_python_metadata** ([`bool`](https://docs.python.org/3/builtins/functions.html#bool)) – include `x-python-*` extensions.
  * **include_schemas** ([`bool`](https://docs.python.org/3/builtins/functions.html#bool)) – derive `requestBody` / `responses` /
    `components.schemas` from the Python type hints.
  * **include_transformers** ([`bool`](https://docs.python.org/3/builtins/functions.html#bool)) – include transformation metadata.
  * **output_file** ([`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]) – optional path to write the JSON document to.
* **Return type:**
  [`Dict`](https://docs.python.org/3/library/typing.html#typing.Dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)]
* **Returns:**
  the enhanced OpenAPI schema dictionary.

### Example

```pycon
>>> from qh import mk_app
>>> from qh.openapi import export_openapi
>>> app = mk_app([my_func])
>>> spec = export_openapi(app, include_examples=True)
```

### qh.openapi.extract_function_signature(func)

Extract detailed signature information from a function.

* **Parameters:**
  **func** ([`Callable`](https://docs.python.org/3/library/typing.html#typing.Callable)) – The function to inspect.
* **Returns:**
  - name: function name
  - module: module path
  - parameters: list of parameter info
  - return_type: return type annotation
  - docstring: function docstring
* **Return type:**
  [`Dict`](https://docs.python.org/3/library/typing.html#typing.Dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)]

### qh.openapi.generate_examples_for_function(func)

Generate example requests/responses for a function.

Uses type hints to generate sensible example values.

* **Return type:**
  [`List`](https://docs.python.org/3/library/typing.html#typing.List)[[`Dict`](https://docs.python.org/3/library/typing.html#typing.Dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)]]

### qh.openapi.get_python_type_name(type_hint)

Get a string representation of a Python type.

`inspect.Parameter.empty` and `None` map to `"Any"`. Anything else
with a `__name__` uses that name alone, with no type arguments — on
Python 3.10+ this includes builtin generic aliases (`list[int]`) and
`typing` generics (`Optional[str]`, `Dict[str, int]`), since they
all carry a `__name__` now. The bracketed-argument form only appears
for the rare origin type that lacks `__name__`.

* **Parameters:**
  **type_hint** ([`Any`](https://docs.python.org/3/library/typing.html#typing.Any)) – A type or type annotation, or `inspect.Parameter.empty`.
* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)
* **Returns:**
  The type’s bare name, e.g. `"int"` or `"list"`.

### Examples

```pycon
>>> get_python_type_name(int)
'int'
>>> get_python_type_name(str)
'str'
>>> get_python_type_name(list[int])
'list'
>>> from typing import Optional
>>> get_python_type_name(Optional[str])
'Optional'
```

### qh.openapi.install_enhanced_openapi(app, \*\*enhance_kwargs)

Make `app` serve the enhanced OpenAPI schema at its `/openapi.json`.

Overrides `app.openapi` so the document returned by FastAPI — and rendered
by `/docs` and `/redoc` — carries the request/response JSON Schema and
`components.schemas` derived from the wrapped functions’ Python type hints.

The override is **defensive**: if enhancement raises for any reason, it
falls back to FastAPI’s plain schema, so a converter bug can never turn
`/openapi.json` into a 500.

* **Parameters:**
  * **app** (`FastAPI`) – the FastAPI application (typically the result of [`qh.mk_app()`](qh.html.md#qh.mk_app)).
  * **\*\*enhance_kwargs** ([`Any`](https://docs.python.org/3/library/typing.html#typing.Any)) – forwarded to [`enhance_openapi_schema()`](#qh.openapi.enhance_openapi_schema).
* **Return type:**
  `FastAPI`
* **Returns:**
  the same `app`, for chaining.

### qh.openapi.python_type_to_json_schema(type_hint, schemas, , \_stack=None)

Convert a Python type hint to a JSON Schema fragment.

Primitives, containers and unions are inlined. Named composite types —
dataclasses, `TypedDict`s, Pydantic models, `NamedTuple`s and
`Enum`s — are registered in `schemas` (the OpenAPI
`components.schemas` table) and returned as a `$ref`, so the same type
used in several places is described once.

* **Parameters:**
  * **type_hint** ([`Any`](https://docs.python.org/3/library/typing.html#typing.Any)) – the Python type / annotation to convert. `Any` and
    `inspect.Parameter.empty` map to the empty schema `{}`
    (matches anything); `None` / `NoneType` map to `{"type": "null"}`.
  * **schemas** ([`Dict`](https://docs.python.org/3/library/typing.html#typing.Dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)]) – the mutable `components.schemas` accumulator — composite
    types encountered are added here, keyed by their class name.
  * **\_stack** ([`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`frozenset`](https://docs.python.org/3/builtins/stdtypes.html#frozenset)]) – internal — the set of composite type names currently being
    built, used to break recursion on self-referential types.
* **Return type:**
  [`Dict`](https://docs.python.org/3/library/typing.html#typing.Dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)]
* **Returns:**
  a JSON Schema dict — an inline fragment, or `{"$ref": ...}` for a
  named composite type.

### Examples

```pycon
>>> python_type_to_json_schema(int, {})
{'type': 'integer'}
>>> python_type_to_json_schema(list[str], {})
{'type': 'array', 'items': {'type': 'string'}}
>>> python_type_to_json_schema(Optional[int], {})
{'anyOf': [{'type': 'integer'}, {'type': 'null'}]}
```
