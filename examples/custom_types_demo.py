"""
Custom type handling demonstration for qh.

Shows how to register custom types for automatic serialization/deserialization.
"""

from qh import mk_app, print_routes
from qh.types import register_type, register_json_type
from dataclasses import dataclass
from datetime import datetime


# Example 1: Register a simple custom type with explicit serializers

@dataclass
class Point:
    """A 2D point."""
    x: float
    y: float


# Register Point type
register_type(
    Point,
    to_json=lambda p: {'x': p.x, 'y': p.y},
    from_json=lambda d: Point(x=d['x'], y=d['y'])
)


def create_point(x: float, y: float) -> Point:
    """Create a point from coordinates."""
    return Point(x=x, y=y)


def distance_from_origin(point: Point) -> float:
    """Calculate distance from origin."""
    return (point.x ** 2 + point.y ** 2) ** 0.5


# Example 2: Use decorator for automatic registration

@register_json_type
class User:
    """A user with automatic JSON conversion."""

    def __init__(self, user_id: str, name: str, email: str):
        self.user_id = user_id
        self.name = name
        self.email = email
        self.created_at = datetime.now()

    def to_dict(self):
        """Convert to dictionary."""
        return {
            'user_id': self.user_id,
            'name': self.name,
            'email': self.email,
            'created_at': self.created_at.isoformat()
        }

    @classmethod
    def from_dict(cls, data):
        """Create from dictionary."""
        user = cls(
            user_id=data['user_id'],
            name=data['name'],
            email=data['email']
        )
        if 'created_at' in data:
            user.created_at = datetime.fromisoformat(data['created_at'])
        return user


def create_user(name: str, email: str) -> User:
    """Create a user."""
    return User(
        user_id='123',
        name=name,
        email=email
    )


def process_user(user: User) -> dict:
    """Process a user object."""
    return {
        'processed': True,
        'user_name': user.name,
        'user_email': user.email
    }


# Example 3: NumPy arrays (if available)
try:
    import numpy as np

    def multiply_array(data: np.ndarray, factor: float = 2.0) -> np.ndarray:
        """Multiply a NumPy array by a factor."""
        return data * factor

    def array_stats(data: np.ndarray) -> dict:
        """Get statistics for an array."""
        return {
            'mean': float(np.mean(data)),
            'std': float(np.std(data)),
            'min': float(np.min(data)),
            'max': float(np.max(data))
        }

    numpy_funcs = [multiply_array, array_stats]
except ImportError:
    numpy_funcs = []
    print("NumPy not available - skipping NumPy examples")


# Create the app
app = mk_app([
    create_point,
    distance_from_origin,
    create_user,
    process_user,
] + numpy_funcs)

if __name__ == '__main__':
    print("=" * 70)
    print("Custom Type Handling Demo")
    print("=" * 70)
    print("\nRegistered Custom Types:")
    print("  - Point: 2D coordinate")
    print("  - User: User object with auto-conversion")
    if numpy_funcs:
        print("  - numpy.ndarray: Numeric arrays")
    print("\n" + "=" * 70)
    print("Routes:")
    print("=" * 70)
    print()
    print_routes(app)
    print("\n" + "=" * 70)
    print("Try it out:")
    print("=" * 70)
    print("\n# Create a point")
    print("curl -X POST http://localhost:8000/create_point \\")
    print("  -H 'Content-Type: application/json' \\")
    print("  -d '{\"x\": 3.0, \"y\": 4.0}'\n")
    print("# Calculate distance (Point object in request)")
    print("curl -X POST http://localhost:8000/distance_from_origin \\")
    print("  -H 'Content-Type: application/json' \\")
    print("  -d '{\"point\": {\"x\": 3.0, \"y\": 4.0}}'\n")
    print("# Create a user")
    print("curl -X POST http://localhost:8000/create_user \\")
    print("  -H 'Content-Type: application/json' \\")
    print("  -d '{\"name\": \"Alice\", \"email\": \"alice@example.com\"}'\n")

    if numpy_funcs:
        print("# Multiply array")
        print("curl -X POST http://localhost:8000/multiply_array \\")
        print("  -H 'Content-Type: application/json' \\")
        print("  -d '{\"data\": [1, 2, 3, 4, 5], \"factor\": 3.0}'\n")

    print("=" * 70)
    print("\nStarting server...")
    print("Visit http://localhost:8000/docs for interactive API documentation\n")

    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
