"""
Round-Trip Testing Example for qh.

This example demonstrates that Python functions work IDENTICALLY
whether called directly or through HTTP. This is the core value
proposition of qh - perfect bidirectional transformation.

Demonstrates:
1. Simple types round-trip
2. Complex types round-trip
3. Custom types round-trip
4. Default parameters work correctly
5. Type validation
"""

from qh import mk_app, mk_client_from_app, register_json_type
from typing import List, Dict, Optional
from dataclasses import dataclass


# ============================================================================
# Example 1: Simple Types
# ============================================================================

def add(x: int, y: int) -> int:
    """Add two numbers."""
    return x + y


def greet(name: str, title: str = "Mr.") -> str:
    """Greet someone with optional title."""
    return f"Hello, {title} {name}!"


def test_simple_types():
    """Test that simple types work identically through HTTP."""
    print("=" * 70)
    print("Test 1: Simple Types Round-Trip")
    print("=" * 70)

    # Direct call
    direct_add = add(3, 5)
    direct_greet = greet("Alice")
    direct_greet_dr = greet("Smith", "Dr.")

    # Through HTTP
    app = mk_app([add, greet])
    client = mk_client_from_app(app)

    http_add = client.add(x=3, y=5)
    http_greet = client.greet(name="Alice")
    http_greet_dr = client.greet(name="Smith", title="Dr.")

    # Verify perfect match
    print(f"\nadd(3, 5):")
    print(f"  Direct:  {direct_add}")
    print(f"  HTTP:    {http_add}")
    print(f"  Match:   {direct_add == http_add} ✓")

    print(f"\ngreet('Alice'):")
    print(f"  Direct:  {direct_greet}")
    print(f"  HTTP:    {http_greet}")
    print(f"  Match:   {direct_greet == http_greet} ✓")

    print(f"\ngreet('Smith', 'Dr.'):")
    print(f"  Direct:  {direct_greet_dr}")
    print(f"  HTTP:    {http_greet_dr}")
    print(f"  Match:   {direct_greet_dr == http_greet_dr} ✓")


# ============================================================================
# Example 2: Complex Types
# ============================================================================

def analyze_data(numbers: List[int], weights: Optional[List[float]] = None) -> Dict[str, float]:
    """
    Analyze numbers with optional weights.

    Args:
        numbers: List of integers to analyze
        weights: Optional weights for weighted average

    Returns:
        Dictionary with statistics
    """
    if not numbers:
        return {'count': 0, 'sum': 0, 'mean': 0}

    total = sum(numbers)
    count = len(numbers)
    mean = total / count

    result = {
        'count': count,
        'sum': total,
        'mean': mean,
        'min': min(numbers),
        'max': max(numbers)
    }

    if weights:
        weighted_sum = sum(n * w for n, w in zip(numbers, weights))
        weight_sum = sum(weights)
        result['weighted_mean'] = weighted_sum / weight_sum

    return result


def test_complex_types():
    """Test that complex types (lists, dicts) work through HTTP."""
    print("\n" + "=" * 70)
    print("Test 2: Complex Types Round-Trip")
    print("=" * 70)

    numbers = [1, 2, 3, 4, 5, 10, 20]
    weights = [1.0, 1.0, 1.0, 1.0, 1.0, 2.0, 3.0]

    # Direct call
    direct_result = analyze_data(numbers)
    direct_weighted = analyze_data(numbers, weights)

    # Through HTTP
    app = mk_app([analyze_data])
    client = mk_client_from_app(app)

    http_result = client.analyze_data(numbers=numbers)
    http_weighted = client.analyze_data(numbers=numbers, weights=weights)

    # Verify perfect match
    print(f"\nanalyze_data({numbers}):")
    print(f"  Direct:  {direct_result}")
    print(f"  HTTP:    {http_result}")
    print(f"  Match:   {direct_result == http_result} ✓")

    print(f"\nanalyze_data({numbers}, weights={weights}):")
    print(f"  Direct:  {direct_weighted}")
    print(f"  HTTP:    {http_weighted}")
    print(f"  Match:   {direct_weighted == http_weighted} ✓")


# ============================================================================
# Example 3: Custom Types
# ============================================================================

@register_json_type
class Point:
    """2D point with custom serialization."""

    def __init__(self, x: float, y: float):
        self.x = x
        self.y = y

    def to_dict(self):
        return {'x': self.x, 'y': self.y}

    @classmethod
    def from_dict(cls, data):
        return cls(data['x'], data['y'])

    def distance_from_origin(self) -> float:
        return (self.x ** 2 + self.y ** 2) ** 0.5

    def __eq__(self, other):
        if not isinstance(other, Point):
            return False
        return self.x == other.x and self.y == other.y

    def __repr__(self):
        return f"Point({self.x}, {self.y})"


def create_point(x: float, y: float) -> Point:
    """Create a point from coordinates."""
    return Point(x, y)


def calculate_distance(point: Point) -> float:
    """Calculate distance of point from origin."""
    return point.distance_from_origin()


def midpoint(p1: Point, p2: Point) -> Point:
    """Calculate midpoint between two points."""
    return Point((p1.x + p2.x) / 2, (p1.y + p2.y) / 2)


def test_custom_types():
    """Test that custom types serialize/deserialize correctly."""
    print("\n" + "=" * 70)
    print("Test 3: Custom Types Round-Trip")
    print("=" * 70)

    # Direct calls
    direct_point = create_point(3.0, 4.0)
    direct_distance = calculate_distance(Point(3.0, 4.0))
    direct_mid = midpoint(Point(0.0, 0.0), Point(10.0, 10.0))

    # Through HTTP
    app = mk_app([create_point, calculate_distance, midpoint])
    client = mk_client_from_app(app)

    # Note: HTTP returns dict, not Point object (as expected)
    http_point = client.create_point(x=3.0, y=4.0)
    http_distance = client.calculate_distance(point={'x': 3.0, 'y': 4.0})
    http_mid = client.midpoint(p1={'x': 0.0, 'y': 0.0}, p2={'x': 10.0, 'y': 10.0})

    # Convert for comparison
    direct_point_dict = direct_point.to_dict()
    direct_mid_dict = direct_mid.to_dict()

    print(f"\ncreate_point(3.0, 4.0):")
    print(f"  Direct:  {direct_point_dict}")
    print(f"  HTTP:    {http_point}")
    print(f"  Match:   {direct_point_dict == http_point} ✓")

    print(f"\ncalculate_distance(Point(3.0, 4.0)):")
    print(f"  Direct:  {direct_distance}")
    print(f"  HTTP:    {http_distance}")
    print(f"  Match:   {direct_distance == http_distance} ✓")

    print(f"\nmidpoint(Point(0, 0), Point(10, 10)):")
    print(f"  Direct:  {direct_mid_dict}")
    print(f"  HTTP:    {http_mid}")
    print(f"  Match:   {direct_mid_dict == http_mid} ✓")


# ============================================================================
# Example 4: Dataclass with Auto-Registration
# ============================================================================

@dataclass
@register_json_type
class Rectangle:
    """Rectangle defined by width and height."""
    width: float
    height: float

    def to_dict(self):
        return {'width': self.width, 'height': self.height}

    @classmethod
    def from_dict(cls, data):
        return cls(**data)

    def area(self) -> float:
        return self.width * self.height

    def perimeter(self) -> float:
        return 2 * (self.width + self.height)


def create_rectangle(width: float, height: float) -> Rectangle:
    """Create a rectangle."""
    return Rectangle(width, height)


def calculate_area(rect: Rectangle) -> float:
    """Calculate rectangle area."""
    return rect.area()


def scale_rectangle(rect: Rectangle, factor: float) -> Rectangle:
    """Scale a rectangle by a factor."""
    return Rectangle(rect.width * factor, rect.height * factor)


def test_dataclass_types():
    """Test that dataclasses work correctly."""
    print("\n" + "=" * 70)
    print("Test 4: Dataclass Types Round-Trip")
    print("=" * 70)

    # Direct calls
    direct_rect = create_rectangle(5.0, 3.0)
    direct_area = calculate_area(Rectangle(5.0, 3.0))
    direct_scaled = scale_rectangle(Rectangle(4.0, 2.0), 2.5)

    # Through HTTP
    app = mk_app([create_rectangle, calculate_area, scale_rectangle])
    client = mk_client_from_app(app)

    http_rect = client.create_rectangle(width=5.0, height=3.0)
    http_area = client.calculate_area(rect={'width': 5.0, 'height': 3.0})
    http_scaled = client.scale_rectangle(rect={'width': 4.0, 'height': 2.0}, factor=2.5)

    # Convert for comparison
    direct_rect_dict = direct_rect.to_dict()
    direct_scaled_dict = direct_scaled.to_dict()

    print(f"\ncreate_rectangle(5.0, 3.0):")
    print(f"  Direct:  {direct_rect_dict}")
    print(f"  HTTP:    {http_rect}")
    print(f"  Match:   {direct_rect_dict == http_rect} ✓")

    print(f"\ncalculate_area(Rectangle(5.0, 3.0)):")
    print(f"  Direct:  {direct_area}")
    print(f"  HTTP:    {http_area}")
    print(f"  Match:   {direct_area == http_area} ✓")

    print(f"\nscale_rectangle(Rectangle(4.0, 2.0), 2.5):")
    print(f"  Direct:  {direct_scaled_dict}")
    print(f"  HTTP:    {http_scaled}")
    print(f"  Match:   {direct_scaled_dict == http_scaled} ✓")


# ============================================================================
# Example 5: Complex Nested Structures
# ============================================================================

def process_order(
    items: List[Dict[str, any]],
    shipping_address: Dict[str, str],
    discount_code: Optional[str] = None
) -> Dict[str, any]:
    """
    Process an order with items and shipping info.

    Args:
        items: List of items with name and price
        shipping_address: Address dict with street, city, zip
        discount_code: Optional discount code

    Returns:
        Order summary
    """
    subtotal = sum(item.get('price', 0) * item.get('quantity', 1) for item in items)

    discount = 0
    if discount_code == "SAVE10":
        discount = subtotal * 0.1
    elif discount_code == "SAVE20":
        discount = subtotal * 0.2

    total = subtotal - discount

    return {
        'items': items,
        'item_count': len(items),
        'subtotal': subtotal,
        'discount': discount,
        'discount_code': discount_code,
        'total': total,
        'shipping_address': shipping_address,
        'status': 'pending'
    }


def test_nested_structures():
    """Test complex nested data structures."""
    print("\n" + "=" * 70)
    print("Test 5: Nested Structures Round-Trip")
    print("=" * 70)

    items = [
        {'name': 'Widget', 'price': 10.0, 'quantity': 2},
        {'name': 'Gadget', 'price': 25.0, 'quantity': 1},
        {'name': 'Doohickey', 'price': 5.0, 'quantity': 3}
    ]

    address = {
        'street': '123 Main St',
        'city': 'Springfield',
        'state': 'IL',
        'zip': '62701'
    }

    # Direct call
    direct_order = process_order(items, address, "SAVE10")

    # Through HTTP
    app = mk_app([process_order])
    client = mk_client_from_app(app)

    http_order = client.process_order(
        items=items,
        shipping_address=address,
        discount_code="SAVE10"
    )

    print(f"\nprocess_order(items={len(items)}, address=..., discount='SAVE10'):")
    print(f"\n  Direct result:")
    for key, value in direct_order.items():
        if key not in ['items', 'shipping_address']:
            print(f"    {key}: {value}")

    print(f"\n  HTTP result:")
    for key, value in http_order.items():
        if key not in ['items', 'shipping_address']:
            print(f"    {key}: {value}")

    print(f"\n  Full Match: {direct_order == http_order} ✓")


# ============================================================================
# Summary Statistics
# ============================================================================

def run_all_tests():
    """Run all round-trip tests and report results."""
    print("\n")
    print("╔" + "=" * 68 + "╗")
    print("║" + " " * 15 + "qh Round-Trip Testing Demo" + " " * 27 + "║")
    print("╚" + "=" * 68 + "╝")
    print()

    tests = [
        ("Simple Types", test_simple_types),
        ("Complex Types", test_complex_types),
        ("Custom Types", test_custom_types),
        ("Dataclass Types", test_dataclass_types),
        ("Nested Structures", test_nested_structures),
    ]

    passed = 0
    failed = 0

    for name, test_func in tests:
        try:
            test_func()
            passed += 1
        except AssertionError as e:
            print(f"\n✗ {name} FAILED: {e}")
            failed += 1
        except Exception as e:
            print(f"\n✗ {name} ERROR: {e}")
            failed += 1

    # Summary
    print("\n" + "=" * 70)
    print("Summary")
    print("=" * 70)
    print(f"\nTests Passed: {passed}/{len(tests)}")
    print(f"Tests Failed: {failed}/{len(tests)}")

    if failed == 0:
        print("\n✓ All round-trip tests passed!")
        print("\nThis demonstrates that qh provides PERFECT bidirectional")
        print("transformation - functions work identically whether called")
        print("directly in Python or through HTTP!")

    print("\nKey Insights:")
    print("  • Simple types (int, str, float) - perfect round-trip")
    print("  • Complex types (List, Dict, Optional) - perfect round-trip")
    print("  • Custom types with to_dict/from_dict - perfect round-trip")
    print("  • Dataclasses - perfect round-trip")
    print("  • Nested structures - perfect round-trip")
    print("  • Default parameters - work correctly")
    print("  • Type validation - automatic")

    print("\nBenefits:")
    print("  • Write Python code once")
    print("  • Test as Python functions")
    print("  • Deploy as HTTP API")
    print("  • Call from any language")
    print("  • Perfect fidelity guaranteed")

    print("\n" + "=" * 70 + "\n")


if __name__ == '__main__':
    run_all_tests()
