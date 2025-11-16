"""
Quickstart example for qh - the new convention-over-configuration API.

This example shows how easy it is to expose Python functions as HTTP endpoints.
"""

from qh import mk_app, print_routes


# Example 1: Simple functions
def add(x: int, y: int) -> int:
    """Add two numbers together."""
    return x + y


def greet(name: str = "World") -> str:
    """Greet someone by name."""
    return f"Hello, {name}!"


def multiply(x: int, y: int) -> int:
    """Multiply two numbers."""
    return x * y


# Create the FastAPI app - that's it!
app = mk_app([add, greet, multiply])

if __name__ == "__main__":
    # Print the available routes
    print("=" * 60)
    print("Available Routes:")
    print("=" * 60)
    print_routes(app)
    print("=" * 60)

    print("\nStarting server...")
    print("Try these commands in another terminal:\n")
    print("curl -X POST http://localhost:8000/add -H 'Content-Type: application/json' -d '{\"x\": 3, \"y\": 5}'")
    print("curl -X POST http://localhost:8000/greet -H 'Content-Type: application/json' -d '{\"name\": \"qh\"}'")
    print("curl -X POST http://localhost:8000/multiply -H 'Content-Type: application/json' -d '{\"x\": 4, \"y\": 7}'")
    print("\nOr visit http://localhost:8000/docs for interactive API documentation\n")

    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
