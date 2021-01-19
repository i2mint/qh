from typing import Iterable, Callable

from py2http import mk_http_service

from qh.util import flat_callable_for


def _ascertain_flat_func_list(funcs):
    if isinstance(funcs, Callable):
        return _ascertain_flat_func_list([funcs])
    else:
        assert isinstance(funcs, Iterable) and all(map(callable, funcs)), \
            f"funcs is supposed to be a callable or an iterable of callables: {funcs}"
        return [flat_callable_for(func) for func in funcs]


def mk_http_service_app(funcs, input_trans=None):
    funcs = _ascertain_flat_func_list(funcs)
    if input_trans:
        for func in funcs:
            func.input_mapper = input_trans
    return mk_http_service(funcs)

