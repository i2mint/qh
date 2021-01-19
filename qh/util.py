"""General utils"""

import inspect
from functools import partial

from py2http.decorators import mk_flat


def get_class_that_defined_method(meth):
    """Get the class from a method function object"""
    if isinstance(meth, partial):
        return get_class_that_defined_method(meth.func)
    if inspect.ismethod(meth) or (
            inspect.isbuiltin(meth) and getattr(meth, '__self__', None) is not None and getattr(meth.__self__,
                                                                                                '__class__', None)):
        for cls in inspect.getmro(meth.__self__.__class__):
            if meth.__name__ in cls.__dict__:
                return cls
        meth = getattr(meth, '__func__', meth)  # fallback to __qualname__ parsing
    if inspect.isfunction(meth):
        cls = getattr(inspect.getmodule(meth),
                      meth.__qualname__.split('.<locals>', 1)[0].rsplit('.', 1)[0],
                      None)
        if isinstance(cls, type):
            return cls
    return getattr(meth, '__objclass__', None)  # handle special descriptor objects


def flat_callable_for(func, func_name=None, cls=None):
    """
    Flatten a simple cls->instance->method call pipeline into one function,
    or just return the input func (possibly with the func_name changed), if the function is already flat.

    That is, a function mk_flat(cls, method) that returns a "flat function" such that
    ```
    cls(**init_kwargs).method(**method_kwargs) == flat_func(**init_kwargs, **method_kwargs)
    ```

    :param method: The method object to get a flat function from
    :param func_name: The name to give the function
    :param cls: 
    :return: A flat function
    
    
    """
    containing_cls = get_class_that_defined_method(method)
    if not containing_cls:  # then it's just a "normal" function, so return it:
        if func_name is not None:
            func.__name__ = func_name
        return func
    else:
        if cls is None:
            cls = containing_cls
        if func_name is None:
            func_name = getattr(method, '__name__', 'flat_func')

        func = mk_flat(cls=cls, method=method, func_name=func_name)
        func.__qualname__ = getattr(method, '__qualname__', None)
        return func
