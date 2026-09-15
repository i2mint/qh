# qh.conventions

Convention-based routing for qh.

Automatically infer HTTP paths and methods from function names and signatures.

Supports patterns like:

- get_user(user_id: str) → GET /users/{user_id}
- list_users(limit: int = 100) → GET /users?limit=100
- create_user(user: User) → POST /users
- update_user(user_id: str, user: User) → PUT /users/{user_id}
- delete_user(user_id: str) → DELETE /users/{user_id}

### Functions

| [`apply_conventions_to_funcs`](#qh.conventions.apply_conventions_to_funcs)(funcs, \*[, ...])    | Apply conventions to a list of functions.                      |
|--------------------------------------------------------------------------------------------------|----------------------------------------------------------------|
| [`get_id_params`](#qh.conventions.get_id_params)(func)                             | Extract parameters that look like IDs from function signature. |
| [`infer_http_method`](#qh.conventions.infer_http_method)(func_name[, parsed])          | Infer HTTP method from function name.                          |
| [`infer_path_from_function`](#qh.conventions.infer_path_from_function)(func, \*[, ...])       | Infer RESTful path from function name and signature.           |
| [`infer_route_config`](#qh.conventions.infer_route_config)(func, \*[, ...])             | Infer complete route configuration from function.              |
| [`merge_convention_config`](#qh.conventions.merge_convention_config)(convention_config, ...) | Merge convention-based config with explicit config.            |
| [`parse_function_name`](#qh.conventions.parse_function_name)(func_name)                  | Parse a function name to extract verb and resource.            |
| [`pluralize`](#qh.conventions.pluralize)(word)                                 | Simple pluralization.                                          |
| [`singularize`](#qh.conventions.singularize)(word)                               | Simple singularization (just removes trailing 's' for now).    |

### Classes

| [`ParsedFunctionName`](#qh.conventions.ParsedFunctionName)(verb, resource, ...)   | Result of parsing a function name.   |
|--------------------------------------------------------------------------------------------|--------------------------------------|

### *class* qh.conventions.ParsedFunctionName(verb, resource, is_plural, is_collection_operation)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

Result of parsing a function name.

### qh.conventions.apply_conventions_to_funcs(funcs, , use_conventions=True, base_path='', use_plurals=True)

Apply conventions to a list of functions.

* **Parameters:**
  * **funcs** ([`List`](https://docs.python.org/3/library/typing.html#typing.List)[[`Callable`](https://docs.python.org/3/library/typing.html#typing.Callable)]) – The functions to route.
  * **use_conventions** ([`bool`](https://docs.python.org/3/builtins/functions.html#bool)) – Whether to use conventions
  * **base_path** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – Base path to prepend to all routes
  * **use_plurals** ([`bool`](https://docs.python.org/3/builtins/functions.html#bool)) – Whether to use plural resource names
* **Return type:**
  [`Dict`](https://docs.python.org/3/library/typing.html#typing.Dict)[[`Callable`](https://docs.python.org/3/library/typing.html#typing.Callable), [`Dict`](https://docs.python.org/3/library/typing.html#typing.Dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)]]
* **Returns:**
  Dict mapping functions to their inferred configurations

### qh.conventions.get_id_params(func)

Extract parameters that look like IDs from function signature.

ID parameters typically:

- End with ‘_id’
- Are named ‘id’
- Are the first parameter (for item operations)

* **Parameters:**
  **func** ([`Callable`](https://docs.python.org/3/library/typing.html#typing.Callable)) – Function to analyze
* **Return type:**
  [`List`](https://docs.python.org/3/library/typing.html#typing.List)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]
* **Returns:**
  List of parameter names that are likely IDs

### qh.conventions.infer_http_method(func_name, parsed=None)

Infer HTTP method from function name.

* **Parameters:**
  * **func_name** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – Function name
  * **parsed** ([`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`ParsedFunctionName`](#qh.conventions.ParsedFunctionName)]) – Optional pre-parsed function name
* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)
* **Returns:**
  HTTP method (‘GET’, ‘POST’, ‘PUT’, ‘PATCH’, ‘DELETE’)

### Examples

```pycon
>>> infer_http_method('get_user')
'GET'
>>> infer_http_method('create_user')
'POST'
>>> infer_http_method('update_user')
'PUT'
>>> infer_http_method('delete_user')
'DELETE'
```

### qh.conventions.infer_path_from_function(func, , use_plurals=True, base_path='')

Infer RESTful path from function name and signature.

* **Parameters:**
  * **func** ([`Callable`](https://docs.python.org/3/library/typing.html#typing.Callable)) – Function to analyze
  * **use_plurals** ([`bool`](https://docs.python.org/3/builtins/functions.html#bool)) – Whether to use plural resource names for collections
  * **base_path** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – Base path to prepend
* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)
* **Returns:**
  Inferred path

### Examples

```pycon
>>> def get_user(user_id: str): pass
>>> infer_path_from_function(get_user)
'/users/{user_id}'
```

```pycon
>>> def list_users(limit: int = 100): pass
>>> infer_path_from_function(list_users)
'/users'
```

```pycon
>>> def create_user(name: str, email: str): pass
>>> infer_path_from_function(create_user)
'/users'
```

```pycon
>>> def update_user(user_id: str, name: str): pass
>>> infer_path_from_function(update_user)
'/users/{user_id}'
```

### qh.conventions.infer_route_config(func, , use_conventions=True, base_path='', use_plurals=True)

Infer complete route configuration from function.

* **Parameters:**
  * **func** ([`Callable`](https://docs.python.org/3/library/typing.html#typing.Callable)) – Function to analyze
  * **use_conventions** ([`bool`](https://docs.python.org/3/builtins/functions.html#bool)) – Whether to use conventions (if False, returns empty dict)
  * **base_path** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – Base path to prepend
  * **use_plurals** ([`bool`](https://docs.python.org/3/builtins/functions.html#bool)) – Whether to use plural resource names
* **Return type:**
  [`Dict`](https://docs.python.org/3/library/typing.html#typing.Dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)]
* **Returns:**
  Route configuration dict

### qh.conventions.merge_convention_config(convention_config, explicit_config)

Merge convention-based config with explicit config.

Explicit config takes precedence.

* **Parameters:**
  * **convention_config** ([`Dict`](https://docs.python.org/3/library/typing.html#typing.Dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)]) – Config inferred from conventions
  * **explicit_config** ([`Dict`](https://docs.python.org/3/library/typing.html#typing.Dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)]) – User-provided config
* **Return type:**
  [`Dict`](https://docs.python.org/3/library/typing.html#typing.Dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)]
* **Returns:**
  Merged config

### qh.conventions.parse_function_name(func_name)

Parse a function name to extract verb and resource.

* **Parameters:**
  **func_name** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – The function’s name, e.g. `'get_user'`.
* **Return type:**
  [`ParsedFunctionName`](#qh.conventions.ParsedFunctionName)
* **Returns:**
  A `ParsedFunctionName`. When the name is `<verb>_<rest>` and
  `verb` is a known CRUD verb, `resource` is `rest`; otherwise
  the whole name is the resource and `verb` is `""`.

### Examples

```pycon
>>> parse_function_name('get_user')
ParsedFunctionName(verb='get', resource='user', is_plural=False, is_collection_operation=False)
```

```pycon
>>> parse_function_name('list_users')
ParsedFunctionName(verb='list', resource='users', is_plural=True, is_collection_operation=True)
```

```pycon
>>> parse_function_name('create_order_item')
ParsedFunctionName(verb='create', resource='order_item', is_plural=True, is_collection_operation=True)
```

### qh.conventions.pluralize(word)

Simple pluralization.

More sophisticated rules can be added later.

* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

### qh.conventions.singularize(word)

Simple singularization (just removes trailing ‘s’ for now).

More sophisticated rules can be added later.

* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)
