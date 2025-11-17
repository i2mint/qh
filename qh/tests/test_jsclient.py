"""
Tests for JavaScript and TypeScript client generation.
"""

import pytest
from typing import Optional

from qh import mk_app, export_openapi
from qh.jsclient import (
    python_type_to_ts_type,
    export_js_client,
    export_ts_client,
)


class TestTypeConversion:
    """Test Python to TypeScript type conversion."""

    def test_basic_types(self):
        """Test basic type conversions."""
        assert python_type_to_ts_type("int") == "number"
        assert python_type_to_ts_type("float") == "number"
        assert python_type_to_ts_type("str") == "string"
        assert python_type_to_ts_type("bool") == "boolean"

    def test_container_types(self):
        """Test container type conversions."""
        assert python_type_to_ts_type("list") == "any[]"
        assert python_type_to_ts_type("dict") == "Record<string, any>"

    def test_generic_types(self):
        """Test generic type conversions."""
        assert python_type_to_ts_type("list[int]") == "number[]"
        assert python_type_to_ts_type("List[str]") == "string[]"

    def test_optional_types(self):
        """Test Optional type conversions."""
        assert python_type_to_ts_type("Optional[int]") == "number | null"
        assert python_type_to_ts_type("Optional[str]") == "string | null"


class TestJavaScriptClientGeneration:
    """Test JavaScript client code generation."""

    def test_simple_js_client(self):
        """Test generating simple JavaScript client."""

        def add(x: int, y: int) -> int:
            """Add two numbers."""
            return x + y

        app = mk_app([add])
        spec = export_openapi(app, include_python_metadata=True)

        js_code = export_js_client(spec, class_name="MathClient")

        # Check class definition
        assert "export class MathClient" in js_code
        assert "constructor(baseUrl" in js_code

        # Check function exists
        assert "async add(" in js_code
        assert "x, y" in js_code

        # Check it uses fetch
        assert "fetch(" in js_code
        assert "response.json()" in js_code

    def test_js_client_with_axios(self):
        """Test generating JavaScript client with axios."""

        def multiply(x: int, y: int) -> int:
            return x * y

        app = mk_app([multiply])
        spec = export_openapi(app, include_python_metadata=True)

        js_code = export_js_client(spec, use_axios=True)

        # Check axios import and usage
        assert "import axios from 'axios'" in js_code
        assert "this.axios =" in js_code
        assert "this.axios.post" in js_code

    def test_js_client_multiple_functions(self):
        """Test generating client with multiple functions."""

        def add(x: int, y: int) -> int:
            return x + y

        def subtract(x: int, y: int) -> int:
            return x - y

        app = mk_app([add, subtract])
        spec = export_openapi(app, include_python_metadata=True)

        js_code = export_js_client(spec)

        # Both functions should be present
        assert "async add(" in js_code
        assert "async subtract(" in js_code

    def test_js_client_with_defaults(self):
        """Test client generation with default parameters."""

        def greet(name: str, title: str = "Mr.") -> str:
            return f"Hello, {title} {name}!"

        app = mk_app([greet])
        spec = export_openapi(app, include_python_metadata=True)

        js_code = export_js_client(spec)

        assert "async greet(" in js_code
        assert "name, title" in js_code


class TestTypeScriptClientGeneration:
    """Test TypeScript client code generation."""

    def test_simple_ts_client(self):
        """Test generating simple TypeScript client."""

        def add(x: int, y: int) -> int:
            """Add two numbers."""
            return x + y

        app = mk_app([add])
        spec = export_openapi(app, include_python_metadata=True)

        ts_code = export_ts_client(spec, class_name="MathClient")

        # Check class definition with types
        assert "export class MathClient" in ts_code
        assert "private baseUrl: string" in ts_code

        # Check function with type annotations
        assert "async add(x: number, y: number): Promise<number>" in ts_code

        # Check interface
        assert "export interface AddParams" in ts_code

    def test_ts_client_with_axios(self):
        """Test generating TypeScript client with axios."""

        def multiply(x: int, y: int) -> int:
            return x * y

        app = mk_app([multiply])
        spec = export_openapi(app, include_python_metadata=True)

        ts_code = export_ts_client(spec, use_axios=True)

        # Check axios imports
        assert "import axios" in ts_code
        assert "AxiosInstance" in ts_code
        assert "private axios: AxiosInstance" in ts_code

    def test_ts_client_optional_params(self):
        """Test TypeScript client with optional parameters."""

        def greet(name: str, title: Optional[str] = None) -> str:
            """Greet someone."""
            if title:
                return f"Hello, {title} {name}!"
            return f"Hello, {name}!"

        app = mk_app([greet])
        spec = export_openapi(app, include_python_metadata=True)

        ts_code = export_ts_client(spec)

        # Check optional parameter syntax (? indicates optional)
        assert "title?:" in ts_code or "title: " in ts_code
        # Function should have title parameter
        assert "greet(name: string, title:" in ts_code

    def test_ts_client_complex_types(self):
        """Test TypeScript client with complex return types."""

        def analyze(numbers: list) -> dict:
            """Analyze a list of numbers."""
            return {
                'count': len(numbers),
                'sum': sum(numbers),
            }

        app = mk_app([analyze])
        spec = export_openapi(app, include_python_metadata=True)

        ts_code = export_ts_client(spec)

        # Check array and record types
        assert "numbers: any[]" in ts_code or "numbers: " in ts_code
        assert "Promise<Record<string, any>>" in ts_code or "Promise<any>" in ts_code

    def test_ts_client_with_conventions(self):
        """Test TypeScript client with convention-based routing."""

        def get_user(user_id: str) -> dict:
            return {'user_id': user_id, 'name': 'Test User'}

        app = mk_app([get_user], use_conventions=True)
        spec = export_openapi(app, include_python_metadata=True)

        ts_code = export_ts_client(spec)

        # Check function is generated
        assert "async get_user" in ts_code or "async getUser" in ts_code
        assert "user_id: string" in ts_code


class TestCodeQuality:
    """Test quality of generated code."""

    def test_js_has_jsdoc(self):
        """Test that JavaScript includes JSDoc comments."""

        def add(x: int, y: int) -> int:
            """Add two numbers."""
            return x + y

        app = mk_app([add])
        spec = export_openapi(app, include_python_metadata=True)

        js_code = export_js_client(spec)

        # Check for JSDoc
        assert "/**" in js_code
        assert " * Add two numbers" in js_code

    def test_ts_has_jsdoc(self):
        """Test that TypeScript includes JSDoc comments."""

        def add(x: int, y: int) -> int:
            """Add two numbers."""
            return x + y

        app = mk_app([add])
        spec = export_openapi(app, include_python_metadata=True)

        ts_code = export_ts_client(spec)

        # Check for JSDoc
        assert "/**" in ts_code
        assert " * Add two numbers" in ts_code

    def test_generated_code_is_valid_syntax(self):
        """Test that generated code has valid syntax structure."""

        def test_func(a: int, b: str, c: bool) -> dict:
            return {'a': a, 'b': b, 'c': c}

        app = mk_app([test_func])
        spec = export_openapi(app, include_python_metadata=True)

        js_code = export_js_client(spec)
        ts_code = export_ts_client(spec)

        # Basic syntax checks
        assert js_code.count("{") == js_code.count("}")
        assert ts_code.count("{") == ts_code.count("}")

        # Check for common syntax elements
        for code in [js_code, ts_code]:
            assert "export class" in code
            assert "constructor(" in code
            assert "async " in code
            assert "return " in code


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
