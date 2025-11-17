"""
Convention-based routing demonstration for qh.

Shows how function names automatically map to RESTful endpoints.
"""

from qh import mk_app, print_routes


# Example: User management API with conventions

def get_user(user_id: str) -> dict:
    """Get a specific user by ID."""
    return {
        'user_id': user_id,
        'name': 'John Doe',
        'email': 'john@example.com'
    }


def list_users(limit: int = 10, offset: int = 0) -> list:
    """List all users with pagination."""
    return [
        {'user_id': str(i), 'name': f'User {i}'}
        for i in range(offset, offset + limit)
    ]


def create_user(name: str, email: str) -> dict:
    """Create a new user."""
    return {
        'user_id': '123',
        'name': name,
        'email': email,
        'created': True
    }


def update_user(user_id: str, name: str = None, email: str = None) -> dict:
    """Update an existing user."""
    return {
        'user_id': user_id,
        'name': name or 'Updated Name',
        'email': email or 'updated@example.com',
        'updated': True
    }


def delete_user(user_id: str) -> dict:
    """Delete a user."""
    return {
        'user_id': user_id,
        'deleted': True
    }


# Create the app with conventions enabled
app = mk_app(
    [get_user, list_users, create_user, update_user, delete_user],
    use_conventions=True
)

if __name__ == '__main__':
    print("=" * 70)
    print("Convention-Based Routing Demo")
    print("=" * 70)
    print("\nFunction names automatically map to REST endpoints:\n")
    print("  get_user(user_id)  → GET /users/{user_id}")
    print("  list_users(...)    → GET /users")
    print("  create_user(...)   → POST /users")
    print("  update_user(...)   → PUT /users/{user_id}")
    print("  delete_user(...)   → DELETE /users/{user_id}")
    print("\n" + "=" * 70)
    print("Actual Routes Created:")
    print("=" * 70)
    print()
    print_routes(app)
    print("\n" + "=" * 70)
    print("Try it out:")
    print("=" * 70)
    print("\n# Get a user")
    print("curl http://localhost:8000/users/42\n")
    print("# List users with pagination")
    print("curl 'http://localhost:8000/users?limit=5&offset=10'\n")
    print("# Create a user")
    print("curl -X POST http://localhost:8000/users \\")
    print("  -H 'Content-Type: application/json' \\")
    print("  -d '{\"name\": \"Jane Doe\", \"email\": \"jane@example.com\"}'\n")
    print("# Update a user")
    print("curl -X PUT http://localhost:8000/users/42 \\")
    print("  -H 'Content-Type: application/json' \\")
    print("  -d '{\"name\": \"Jane Smith\"}'\n")
    print("# Delete a user")
    print("curl -X DELETE http://localhost:8000/users/42\n")
    print("=" * 70)
    print("\nStarting server...")
    print("Visit http://localhost:8000/docs for interactive API documentation\n")

    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
