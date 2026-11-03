"""Route-path templates: the one parser for ``{name}`` and ``{name:converter}``.

A route path such as ``/environments/{environment:path}/ambient`` names its
parameters in braces, optionally with a Starlette converter after a colon
(``path``, ``int``, ``float``, ``uuid``, ...). Every qh module that reads or fills
a path template goes through these helpers, so a converter is understood
everywhere or nowhere.

>>> path_param_names('/environments/{environment:path}/ambient/{n}')
['environment', 'n']
>>> fill_path_params('/a/{x:path}/b/{y}', {'x': 'INT./EXT.', 'y': 3})
'/a/INT./EXT./b/3'
"""

import re
from typing import Callable, Mapping, Union

PATH_PARAM_PATTERN = re.compile(r"\{(\w+)(?::\w+)?\}")


def path_param_names(path: str) -> list:
    """The parameter names of a route path template, in order of appearance."""
    return PATH_PARAM_PATTERN.findall(path or "")


def fill_path_params(
    path: str,
    values: Union[Mapping[str, object], Callable[[str], str]],
) -> str:
    """Replace each ``{name}`` / ``{name:converter}`` in ``path``.

    ``values`` is either a mapping (names it lacks are left as they are) or a
    function from a parameter name to its replacement text.
    """
    if callable(values):
        render = values
    else:

        def render(name):
            return str(values[name]) if name in values else None

    def _sub(match):
        text = render(match.group(1))
        return match.group(0) if text is None else text

    return PATH_PARAM_PATTERN.sub(_sub, path)
