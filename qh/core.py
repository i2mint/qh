"""Core qh"""

from fastapi import FastAPI, Request, Response
import json
from typing import Optional, Dict, Any
from collections.abc import Iterable, Callable
from i2.wrapper import Wrap
import inspect

# Default configuration
default_configs = {
    'http_method': 'post',
    'path': lambda func: f"/{func.__name__}",
    'input_mapper': None,  # To be set below
    'output_mapper': None,  # To be set below
    'error_handler': lambda exc: Response(content=str(exc), status_code=500),
}


# Default input mapper: Extract from JSON body
async def default_input_mapper(request: Request) -> tuple[tuple, dict]:
    """Extract function arguments from request JSON body."""
    body = await request.json()
    return (), body  # All as kwargs


# Default output mapper: Serialize to JSON
def default_output_mapper(output: Any) -> Response:
    """Serialize function output to JSON response."""
    return Response(content=json.dumps(output), media_type="application/json")


# Set defaults in config
default_configs['input_mapper'] = default_input_mapper
default_configs['output_mapper'] = default_output_mapper


def get_config_for_func(
    func: Callable,
    default_configs: dict[str, Any],
    func_configs: dict[Callable, dict[str, Any]],
) -> dict[str, Any]:
    """Merge default and per-function configurations."""
    config = default_configs.copy()
    if func in func_configs:
        config.update(func_configs[func])
    return config


def mk_wrapped_func(
    func: Callable, input_mapper: Callable, output_mapper: Callable
) -> Callable:
    """Wrap a function with ingress and egress transformations."""
    is_async = inspect.iscoroutinefunction(func)

    async def ingress(request: Request):
        return await input_mapper(request)

    def egress(output: Any):
        return output_mapper(output)

    wrapped = Wrap(func, ingress=ingress, egress=egress)

    async def route_handler(request: Request):
        try:
            result = await wrapped(request)
            return result
        except Exception as e:
            config = get_config_for_func(func, default_configs, {})
            return config['error_handler'](e)

    return route_handler


def mk_fastapi_app(
    funcs: Iterable[Callable] | dict[Callable, dict[str, Any]],
    configs: dict[str, Any] | None = None,
    func_configs: dict[Callable, dict[str, Any]] | None = None,
) -> FastAPI:
    """Create a FastAPI app from a collection of functions."""
    app = FastAPI()
    configs = configs or {}
    default_configs.update(configs)
    func_configs = func_configs or {}

    # Normalize funcs to a dict
    if not hasattr(funcs, 'items'):
        funcs = {func: {} for func in funcs}

    for func, specific_config in funcs.items():
        config = get_config_for_func(func, default_configs, func_configs)
        handler = mk_wrapped_func(func, config['input_mapper'], config['output_mapper'])
        app.add_api_route(
            config['path'](func),
            handler,
            methods=[config['http_method'].upper()],
            description=func.__doc__,
        )

    return app


# Example usage
if __name__ == "__main__":

    def greeter(greeting: str, name: str = 'world', n: int = 1) -> str:
        """Return a greeting repeated n times."""
        return '\n'.join(f"{greeting}, {name}!" for _ in range(n))

    app = mk_fastapi_app([greeter])
    # Run with: uvicorn qh.base:app --reload
