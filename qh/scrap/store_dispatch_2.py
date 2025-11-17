"""Dispatching a store"""

from dataclasses import dataclass
from collections.abc import MutableMapping

backend_test_data = {'test_key': 'test_value', 'test_key_2': 2, 'test_key_3': [1, 2, 3]}


@dataclass
class StoreAccess:
    """
    Delegator for MutableMapping, providing list, read, write, and delete methods.

    This is intended to be used in web services, offering nicer method names than
    the MutableMapping interface, and an actual list instead of a generator in
    the case of list.
    """

    store: MutableMapping

    @classmethod
    def from_uri(cls, uri: str = 'test_uri'):
        """code that makes a MutableMapping interface for the data pointed to by uri"""
        if uri == 'test_uri':
            data = backend_test_data
            return cls(data)

    def list(self):
        return list(self.store.keys())

    def read(self, key):
        return self.store[key]

    def write(self, key, value):
        self.store[key] = value

    def delete(self, key):
        del self.store[key]


from fastapi import FastAPI, HTTPException, Depends, Body
from functools import partial
from typing import Dict, Any
from collections.abc import Callable


def mk_app(
    constructor: Callable, constructor_arg_name: str, routes: dict[str, dict[str, Any]]
):
    app = FastAPI()

    def endpoint_wrapper(constructor: Callable, method_name: str, *args, **kwargs):
        constructor_arg = kwargs.pop(constructor_arg_name)
        instance = constructor(constructor_arg)  # Construct the instance
        method = getattr(instance, method_name)  # Get the method
        return method(*args, **kwargs)  # Call the method with extracted args and kwargs

    for method_name, route_info in routes.items():
        route = route_info['route']
        args = route_info.get('args', [])
        http_method = route_info['method'].lower()
        endpoint_func = partial(
            endpoint_wrapper,
            constructor,
            method_name,
            **{arg: Depends() for arg in args if '.' not in arg}
        )

        if 'body' in route_info.get('args', []):  # Handle special case for body
            endpoint_func.keywords['body'] = Body(...)

        # Dynamically add endpoint to the FastAPI app
        if http_method == 'get':
            app.get(route)(endpoint_func)
        elif http_method == 'post':
            app.post(route)(endpoint_func)
        elif http_method == 'put':
            app.put(route)(endpoint_func)
        elif http_method == 'delete':
            app.delete(route)(endpoint_func)

    return app


from fastapi import FastAPI, HTTPException, Depends, Body, Query
from functools import partial
from typing import Dict, Any
from collections.abc import Callable

def mk_app(constructor: Callable, constructor_arg_name: str, routes: dict[str, dict[str, Any]]):
    app = FastAPI()

    def endpoint_wrapper(constructor: Callable, method_name: str, constructor_arg: str, **kwargs):
        instance = constructor(constructor_arg)  # Construct the instance
        method = getattr(instance, method_name)  # Get the method
        # Prepare method arguments, handling special cases like 'body.key'
        method_args = []
        for arg in kwargs.get('args', []):
            if '.' in arg:
                parts = arg.split('.')
                if parts[0] == 'body' and 'body' in kwargs:
                    method_args.append(getattr(kwargs['body'], parts[1]))
                else:
                    method_args.append(kwargs[arg])
            else:
                method_args.append(kwargs[arg])
        return method(*method_args)

    for method_name, route_info in routes.items():
        route = route_info['route']
        args_config = route_info.get('args', []) or []  # Ensure args_config is a list
        http_method = route_info['method'].lower()

        # Define dynamic dependencies based on args_config
        dependencies = {}
        for arg in args_config:
            if arg and '.' not in arg:
                dependencies[arg] = Depends()
            elif 'body' in arg:
                dependencies['body'] = Body(...)

        # Create a partial function for the endpoint
        endpoint_func = partial(endpoint_wrapper, constructor, method_name, **dependencies)

        # Register the endpoint with the FastAPI application
        if http_method == 'get':
            app.get(route)(endpoint_func)
        elif http_method == 'post':
            app.post(route)(endpoint_func)
        elif http_method == 'put':
            app.put(route)(endpoint_func)
        elif http_method == 'delete':
            app.delete(route)(endpoint_func)

    return app


from fastapi import FastAPI, HTTPException, Body, Path
from functools import partial
from typing import Dict, Any, Optional
from collections.abc import Callable

def mk_app(constructor: Callable, constructor_arg_name: str, routes: dict[str, dict[str, Any]]):
    app = FastAPI()

    def endpoint_wrapper(constructor: Callable, method_name: str, *args, **kwargs):
        # Extract the constructor_arg (e.g., uri) directly from kwargs
        constructor_arg = kwargs.pop(constructor_arg_name)
        instance = constructor(constructor_arg)  # Construct the instance

        # Prepare method arguments, excluding special handling keys
        method_args = {k: v for k, v in kwargs.items() if k not in ['args', 'body']}
        
        method = getattr(instance, method_name)  # Get the method
        # Call the method with *args and **kwargs if needed
        return method(*args, **method_args)

    for method_name, route_info in routes.items():
        route = route_info['route']
        args_config = route_info.get('args', []) or []
        http_method = route_info['method'].lower()

        # Define a route handler dynamically
        async def route_handler(*args, **kwargs):
            # Special handling for 'body' argument
            if 'body' in args_config:
                kwargs['body'] = await Body().as_form()
            return endpoint_wrapper(constructor, method_name, **kwargs)

        # Register the endpoint with the FastAPI application
        if http_method == 'get':
            app.get(route)(route_handler)
        elif http_method == 'post':
            app.post(route)(route_handler)
        elif http_method == 'put':
            app.put(route)(route_handler)
        elif http_method == 'delete':
            app.delete(route)(route_handler)

    return app


# Define a Pydantic model for the request body, assuming it's needed for your write endpoint
from pydantic import BaseModel


class WriteRequestBody(BaseModel):
    key: str
    value: str


# Adjust the constructor and routes configuration according to your actual setup
app = mk_app(
    StoreAccess.from_uri,
    constructor_arg_name='uri',
    routes={
        'list': {'route': "/list/{uri}", 'args': None, 'method': 'get'},
        'read': {'route': "/read/{uri}/{key}", 'args': ['key'], 'method': 'get'},
        'write': {'route': "/write/{uri}", 'args': ['body'], 'method': 'post'},
    },
)
