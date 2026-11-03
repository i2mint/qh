"""Route-path templates: ``{name}`` and ``{name:converter}``, read as Starlette reads them.

A route path such as ``/environments/{environment:path}/ambient`` names its
parameters in braces, optionally with a Starlette converter after a colon
(``path``, ``int``, ``float``, ``uuid``, ...). Every qh module that reads or fills
a path template goes through these helpers, which are built on
``starlette.routing.compile_path`` -- the parser the router itself uses -- so qh and
the router cannot disagree about a template. An unknown converter or a duplicated
parameter name is rejected here exactly as the router would reject it.

``None`` and ``""`` are both the empty template: no parameters, empty format.

>>> path_param_names('/environments/{environment:path}/ambient/{n}')
['environment', 'n']
>>> path_format('/n/{n:int}')
'/n/{n}'
>>> fill_path_params('/a/{x:path}/b/{y}', {'x': 'INT./EXT.', 'y': 'a?b#c/d'})
'/a/INT./EXT./b/a%3Fb%23c%2Fd'
>>> fill_path_params('/a/{x:path}/{y}', {'x': 'p q'})
'/a/p%20q/{y}'
"""

from functools import lru_cache
from typing import List, Mapping, Optional, Tuple
from urllib.parse import quote as _url_quote

from starlette.convertors import PathConvertor
from starlette.routing import PARAM_REGEX, compile_path


@lru_cache(maxsize=None)
def _compiled(path: str) -> Tuple[str, Tuple[Tuple[str, bool], ...]]:
    """``(path_format, ((name, is_path_converter), ...))`` for a template.

    ``compile_path`` checks converter names with an ``assert``; that becomes a
    ``ValueError`` here so the check survives ``python -O``.
    """
    try:
        _, fmt, convertors = compile_path(path)
    except (AssertionError, KeyError) as error:
        raise ValueError(f"Invalid route path {path!r}: {error}") from error
    params = tuple(
        (name, isinstance(conv, PathConvertor)) for name, conv in convertors.items()
    )
    return fmt, params


def path_param_names(path: Optional[str]) -> List[str]:
    """The parameter names of a route path template, in order of appearance."""
    return [name for name, _ in _compiled(path or "")[1]]


def path_format(path: Optional[str]) -> str:
    """The template with converters removed: ``/n/{n:int}`` -> ``/n/{n}``.

    This is the form FastAPI uses to key ``openapi()["paths"]``.
    """
    return _compiled(path or "")[0]


def fill_path_params(
    path: Optional[str],
    values: Mapping[str, object],
    *,
    quote: bool = True,
) -> str:
    """Replace each parameter of ``path`` that ``values`` names with its value.

    Each value is ``str()``-ed and, when ``quote`` is true, URL-encoded: ``/`` is
    kept only for a ``path`` converter, every other reserved character is encoded.
    Parameters ``values`` lacks are left as ``{name}`` (converter removed).
    """
    fmt, params = _compiled(path or "")
    keeps_slash = dict(params)

    def _render(match):
        name = match.group(1)
        if name not in values:
            return match.group(0)
        text = str(values[name])
        if not quote:
            return text
        return _url_quote(text, safe="/" if keeps_slash[name] else "")

    return PARAM_REGEX.sub(_render, fmt)
