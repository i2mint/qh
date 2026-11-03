# qh.paths

Route-path templates: `{name}` and `{name:converter}`, read as Starlette reads them.

A route path such as `/environments/{environment:path}/ambient` names its
parameters in braces, optionally with a Starlette converter after a colon
(`path`, `int`, `float`, `uuid`, …). Every qh module that reads or fills
a path template goes through these helpers, which are built on
`starlette.routing.compile_path` – the parser the router itself uses – so qh and
the router cannot disagree about a template. An unknown converter or a duplicated
parameter name is rejected here exactly as the router would reject it.

`None` and `""` are both the empty template: no parameters, empty format.

```pycon
>>> path_param_names('/environments/{environment:path}/ambient/{n}')
['environment', 'n']
>>> path_format('/n/{n:int}')
'/n/{n}'
>>> fill_path_params('/a/{x:path}/b/{y}', {'x': 'INT./EXT.', 'y': 'a?b#c/d'})
'/a/INT./EXT./b/a%3Fb%23c%2Fd'
>>> fill_path_params('/a/{x:path}/{y}', {'x': 'p q'})
'/a/p%20q/{y}'
```

### Functions

| [`fill_path_params`](#qh.paths.fill_path_params)(path, values, \*[, quote])   | Replace each parameter of `path` that `values` names with its value.   |
|------------------------------------------------------------------------------------------------|------------------------------------------------------------------------|
| [`path_format`](#qh.paths.path_format)(path)                             | The template with converters removed: `/n/{n:int}` -> `/n/{n}`.        |
| [`path_param_names`](#qh.paths.path_param_names)(path)                        | The parameter names of a route path template, in order of appearance.  |

### qh.paths.fill_path_params(path, values, , quote=True)

Replace each parameter of `path` that `values` names with its value.

Each value is `str()`-ed and, when `quote` is true, URL-encoded: `/` is
kept only for a `path` converter, every other reserved character is encoded.
Parameters `values` lacks are left as `{name}` (converter removed).

* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

### qh.paths.path_format(path)

The template with converters removed: `/n/{n:int}` -> `/n/{n}`.

This is the form FastAPI uses to key `openapi()["paths"]`.

* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

### qh.paths.path_param_names(path)

The parameter names of a route path template, in order of appearance.

* **Return type:**
  [`List`](https://docs.python.org/3/library/typing.html#typing.List)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]
