from fastapi import FastAPI, Depends
from typing import List, get_type_hints
from collections.abc import Callable
from inspect import signature
from i2 import Sig


def mk_http_service_app(functions: list[Callable]):
    app = FastAPI()

    for func in functions:
        sig = Sig(func)
        # Determine if the function should be a GET or POST endpoint based on its signature
        if len(sig) >= 0:
            # Create a GET endpoint if the function has no parameters
            endpoint_path = f"/{func.__name__}"
            for name in sig.names:
                endpoint_path += f"/{{{name}}}"

            @app.get(endpoint_path)
            @sig
            async def endpoint(*args, **kwargs):
                sig.map_arguments(*args, **kwargs)
                return func(*args, **kwargs)

        else:
            # Create a POST endpoint for functions with parameters
            # Uses the function signature to define expected input model
            endpoint_path = f"/{func.__name__}"

            @app.post(endpoint_path)
            async def endpoint(body):
                return body

    return app


# Example functions to expose
def poke():
    return 'here is a peek'


def foo(x: int):
    return x + 2


def bar(name: str = 'world'):
    return f"Hello {name}!"


# Create the FastAPI app
app = mk_http_service_app([foo, bar, poke])
