from typing import Optional
from collections.abc import Mapping, Callable, Iterable
from py2http.decorators import mk_flat, handle_json_req

def _name_func_relationships_to_name_func_pairs(name_func_relationships):
    for k, v in name_func_relationships.items():
        if isinstance(k, str):
            name = k
            if isinstance(v, Callable):
                yield name, v
            elif isinstance(v, Iterable):
                for func in v:
                    assert isinstance(func, Callable), f"Should have been a callable: {func}"
                    yield name, func
            else:
                raise TypeError(f"value should have been a callable or an iterable of callables: {v}")
        elif isinstance(k, Callable):
            func = k
            if isinstance(v, str):
                yield v, func
            elif isinstance(v, Iterable):
                for name in v:
                    assert isinstance(name, str), f"Should have been a string: {name}"
                    yield name, func
            else:
                raise TypeError(f"value should have been a string or an iterable of strings: {v}")
        else:
            raise TypeError(f"key should have been a string or a callable: {k}")


def _name_func_relationships_to_name_func_map(name_func_relationships) -> dict:
    assert isinstance(name_func_relationships, Mapping), \
        f"name_func_relationships should be a Mapping of `name: func(s)` or `func: name(s)` pairs: " \
        f"{name_func_relationships}"
    name_func_items = list(_name_func_relationships_to_name_func_pairs(name_func_relationships))
    n = len(name_func_items)
    name_func_map = dict(name_func_items)
    assert len(name_func_map) == n, f"There were some duplicate names in name_func_relationships"
    return name_func_map


def transform_mapping_vals_with_name_func_map(mapping, name_func_map: Mapping[str, Callable]) -> dict:
    for name, val in mapping.items():
        if name in name_func_map:
            yield name, name_func_map[name](val)
        else:
            yield name, val


def mk_json_handler_from_name_mapping(name_func_relationships: Mapping | None = None) -> dict:
    if name_func_relationships is None:
        @handle_json_req  # extracts the JSON body and passes it to the input mapper as a dict
        def input_trans(input_kwargs):
            return dict(input_kwargs)
    else:
        name_func_map = _name_func_relationships_to_name_func_map(name_func_relationships)

        @handle_json_req  # extracts the JSON body and passes it to the input mapper as a dict
        def input_trans(input_kwargs):
            return dict(transform_mapping_vals_with_name_func_map(input_kwargs, name_func_map))

        return input_trans
