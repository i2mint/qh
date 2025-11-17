"""
Client Generation Example for qh.

This example demonstrates how to:
1. Create a qh API
2. Generate Python clients
3. Generate TypeScript clients
4. Generate JavaScript clients
5. Use clients to call the API
"""

from qh import mk_app, export_openapi
from qh.client import mk_client_from_app, mk_client_from_openapi
from qh.jsclient import export_ts_client, export_js_client
from typing import List, Dict


# ============================================================================
# Step 1: Define API Functions
# ============================================================================

def add(x: int, y: int) -> int:
    """Add two numbers."""
    return x + y


def multiply(x: int, y: int) -> int:
    """Multiply two numbers."""
    return x * y


def calculate_stats(numbers: List[int]) -> Dict[str, float]:
    """
    Calculate statistics for a list of numbers.

    Args:
        numbers: List of integers to analyze

    Returns:
        Dictionary with count, sum, mean, min, and max
    """
    if not numbers:
        return {'count': 0, 'sum': 0, 'mean': 0, 'min': 0, 'max': 0}

    return {
        'count': len(numbers),
        'sum': sum(numbers),
        'mean': sum(numbers) / len(numbers),
        'min': min(numbers),
        'max': max(numbers)
    }


# ============================================================================
# Step 2: Create the API
# ============================================================================

app = mk_app([add, multiply, calculate_stats])


# ============================================================================
# Step 3: Generate Python Clients
# ============================================================================

def demo_python_client():
    """Demonstrate Python client generation and usage."""
    print("=" * 70)
    print("Python Client Generation")
    print("=" * 70)

    # Method 1: Create client from app (for testing)
    print("\n1. Creating client from app...")
    client = mk_client_from_app(app)

    # Test add function
    result = client.add(x=10, y=20)
    print(f"   client.add(x=10, y=20) = {result}")

    # Test multiply function
    result = client.multiply(x=7, y=8)
    print(f"   client.multiply(x=7, y=8) = {result}")

    # Test calculate_stats function
    result = client.calculate_stats(numbers=[1, 2, 3, 4, 5, 10, 20])
    print(f"   client.calculate_stats([1, 2, 3, 4, 5, 10, 20]):")
    for key, value in result.items():
        print(f"     {key}: {value}")

    print("\n2. To connect to a running server:")
    print("   " + "-" * 66)
    print("""
   from qh.client import mk_client_from_url

   # Connect to running API
   client = mk_client_from_url('http://localhost:8000/openapi.json')
   result = client.add(x=10, y=20)
   """)


# ============================================================================
# Step 4: Generate TypeScript Clients
# ============================================================================

def demo_typescript_client():
    """Demonstrate TypeScript client generation."""
    print("\n" + "=" * 70)
    print("TypeScript Client Generation")
    print("=" * 70)

    # Export OpenAPI spec with Python metadata
    spec = export_openapi(app, include_python_metadata=True)

    # Generate TypeScript client with axios
    print("\n1. Generating TypeScript client with axios...")
    ts_code = export_ts_client(
        spec,
        class_name="MathClient",
        use_axios=True,
        base_url="http://localhost:8000"
    )

    # Save to file
    output_file = '/tmp/math-client.ts'
    with open(output_file, 'w') as f:
        f.write(ts_code)

    print(f"   ✓ TypeScript client saved to: {output_file}")
    print("\n   Generated code preview:")
    print("   " + "-" * 66)

    # Show first 30 lines
    lines = ts_code.split('\n')[:30]
    for line in lines:
        print(f"   {line}")

    if len(ts_code.split('\n')) > 30:
        print("   ...")
        total_lines = len(ts_code.split('\n'))
        print(f"   (Total: {total_lines} lines)")

    print("\n   Usage in TypeScript:")
    print("   " + "-" * 66)
    print("""
   import { MathClient } from './math-client';

   const client = new MathClient('http://localhost:8000');

   // All methods are type-safe!
   const sum = await client.add(10, 20);  // Type: number
   const product = await client.multiply(7, 8);  // Type: number
   const stats = await client.calculate_stats([1, 2, 3, 4, 5]);
   // Type: { count: number, sum: number, mean: number, min: number, max: number }
   """)

    # Generate TypeScript client with fetch
    print("\n2. Generating TypeScript client with fetch...")
    ts_code_fetch = export_ts_client(
        spec,
        class_name="MathClient",
        use_axios=False,  # Use fetch instead
        base_url="http://localhost:8000"
    )

    output_file_fetch = '/tmp/math-client-fetch.ts'
    with open(output_file_fetch, 'w') as f:
        f.write(ts_code_fetch)

    print(f"   ✓ TypeScript client (fetch) saved to: {output_file_fetch}")


# ============================================================================
# Step 5: Generate JavaScript Clients
# ============================================================================

def demo_javascript_client():
    """Demonstrate JavaScript client generation."""
    print("\n" + "=" * 70)
    print("JavaScript Client Generation")
    print("=" * 70)

    spec = export_openapi(app, include_python_metadata=True)

    # Generate JavaScript client with axios
    print("\n1. Generating JavaScript client with axios...")
    js_code = export_js_client(
        spec,
        class_name="MathClient",
        use_axios=True,
        base_url="http://localhost:8000"
    )

    output_file = '/tmp/math-client.js'
    with open(output_file, 'w') as f:
        f.write(js_code)

    print(f"   ✓ JavaScript client saved to: {output_file}")

    print("\n   Usage in JavaScript:")
    print("   " + "-" * 66)
    print("""
   import { MathClient } from './math-client.js';

   const client = new MathClient('http://localhost:8000');

   // Call API functions
   const sum = await client.add(10, 20);
   const product = await client.multiply(7, 8);
   const stats = await client.calculate_stats([1, 2, 3, 4, 5]);

   console.log(sum);  // 30
   console.log(product);  // 56
   console.log(stats);  // { count: 5, sum: 15, mean: 3, ... }
   """)

    # Generate JavaScript client with fetch
    print("\n2. Generating JavaScript client with fetch...")
    js_code_fetch = export_js_client(
        spec,
        class_name="MathClient",
        use_axios=False,
        base_url="http://localhost:8000"
    )

    output_file_fetch = '/tmp/math-client-fetch.js'
    with open(output_file_fetch, 'w') as f:
        f.write(js_code_fetch)

    print(f"   ✓ JavaScript client (fetch) saved to: {output_file_fetch}")


# ============================================================================
# Step 6: Export OpenAPI Spec
# ============================================================================

def demo_openapi_export():
    """Demonstrate OpenAPI spec export."""
    print("\n" + "=" * 70)
    print("OpenAPI Specification Export")
    print("=" * 70)

    # Export with all metadata
    spec = export_openapi(
        app,
        include_python_metadata=True,
        include_examples=True
    )

    # Save to file
    output_file = '/tmp/openapi-spec.json'
    export_openapi(app, output_file=output_file, include_python_metadata=True)

    print(f"\n   ✓ OpenAPI spec saved to: {output_file}")
    print("\n   The spec includes:")
    print("     • Standard OpenAPI 3.0 schema")
    print("     • x-python-signature extensions with:")
    print("       - Function names and modules")
    print("       - Parameter types and defaults")
    print("       - Return types")
    print("       - Docstrings")
    print("     • Request/response examples")
    print("     • Full type information")

    # Show sample of x-python-signature
    add_operation = spec['paths']['/add']['post']
    if 'x-python-signature' in add_operation:
        print("\n   Example x-python-signature for 'add' function:")
        print("   " + "-" * 66)
        import json
        sig = add_operation['x-python-signature']
        print("   " + json.dumps(sig, indent=4).replace('\n', '\n   '))


# ============================================================================
# Main Demo
# ============================================================================

if __name__ == '__main__':
    print("\n")
    print("╔" + "=" * 68 + "╗")
    print("║" + " " * 15 + "qh Client Generation Demo" + " " * 28 + "║")
    print("╚" + "=" * 68 + "╝")

    # Run all demos
    demo_python_client()
    demo_typescript_client()
    demo_javascript_client()
    demo_openapi_export()

    print("\n" + "=" * 70)
    print("Summary")
    print("=" * 70)
    print("\nGenerated files:")
    print("  • /tmp/math-client.ts - TypeScript client with axios")
    print("  • /tmp/math-client-fetch.ts - TypeScript client with fetch")
    print("  • /tmp/math-client.js - JavaScript client with axios")
    print("  • /tmp/math-client-fetch.js - JavaScript client with fetch")
    print("  • /tmp/openapi-spec.json - OpenAPI 3.0 specification")

    print("\nKey Benefits:")
    print("  • Type-safe clients in Python, TypeScript, and JavaScript")
    print("  • Automatic serialization/deserialization")
    print("  • Functions preserve original signatures")
    print("  • Full IDE autocomplete and type checking")
    print("  • No manual HTTP request code needed")

    print("\nNext Steps:")
    print("  1. Start the server: uvicorn examples.client_generation:app")
    print("  2. Use the generated clients in your projects")
    print("  3. Visit http://localhost:8000/docs for API documentation")

    print("\n" + "=" * 70 + "\n")
