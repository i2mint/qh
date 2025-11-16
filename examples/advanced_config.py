"""
Advanced configuration examples for qh.

Shows how to customize paths, methods, and use advanced features.
"""

from qh import mk_app, AppConfig, RouteConfig, print_routes


def add(x: int, y: int) -> int:
    """Add two integers."""
    return x + y


def subtract(x: int, y: int) -> int:
    """Subtract y from x."""
    return x - y


def get_status() -> dict:
    """Get system status."""
    return {"status": "ok", "version": "0.2.0"}


# Example 1: Using AppConfig for global settings
print("Example 1: Global configuration")
print("-" * 60)

app1 = mk_app(
    [add, subtract],
    config=AppConfig(
        path_prefix="/api/v1",
        default_methods=["POST"],
        title="Calculator API",
        version="1.0.0",
    )
)

print_routes(app1)
print()


# Example 2: Per-function configuration with dict
print("Example 2: Per-function configuration")
print("-" * 60)

app2 = mk_app({
    add: {
        'path': '/calculator/add',
        'methods': ['POST', 'PUT'],
        'summary': 'Add two numbers',
    },
    subtract: {
        'path': '/calculator/subtract',
        'methods': ['POST'],
    },
    get_status: {
        'path': '/status',
        'methods': ['GET'],
        'tags': ['system'],
    },
})

print_routes(app2)
print()


# Example 3: Using RouteConfig objects for more control
print("Example 3: RouteConfig objects")
print("-" * 60)

app3 = mk_app({
    add: RouteConfig(
        path='/math/add',
        methods=['POST', 'GET'],
        summary='Addition endpoint',
        tags=['math', 'arithmetic'],
    ),
    get_status: RouteConfig(
        path='/health',
        methods=['GET', 'HEAD'],
        summary='Health check endpoint',
        tags=['monitoring'],
    ),
})

print_routes(app3)
print()


# Example 4: Combining global and per-function config
print("Example 4: Combined configuration")
print("-" * 60)

app4 = mk_app(
    {
        add: {'path': '/custom/add'},  # Override path only
        subtract: None,  # Use all defaults
    },
    config={
        'path_prefix': '/api',
        'default_methods': ['POST', 'PUT'],
    }
)

print_routes(app4)
print()

print("All examples created successfully!")
print("Run any of these apps with: uvicorn examples.advanced_config:app1 --reload")
