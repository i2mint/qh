"""
test_qh_base.py - Tests for qh.base module
"""

import pytest
from fastapi.testclient import TestClient
from typing import Dict, Any, List
import json

from qh.base import (
    mk_fastapi_app,
    mk_json_ingress,
    mk_json_egress,
    name_based_ingress,
    mk_store_dispatcher,
    RouteConfig,
    AppConfig,
)


# Test fixtures and helper functions


@pytest.fixture
def simple_functions():
    """Collection of simple test functions"""

    def add(a: int, b: int = 2) -> int:
        """Add two numbers"""
        return a + b

    def greet(name: str = "world", greeting: str = "Hello") -> str:
        """Generate a greeting"""
        return f"{greeting}, {name}!"

    def echo(data: Any) -> Any:
        """Echo back the input"""
        return data

    return [add, greet, echo]


@pytest.fixture
def typed_function():
    """Function with complex types for testing transformations"""

    def process_data(
        numbers: list[int], multiplier: float = 1.0, metadata: dict[str, Any] = None
    ) -> dict[str, Any]:
        """Process a list of numbers"""
        result = [n * multiplier for n in numbers]
        return {"result": result, "sum": sum(result), "metadata": metadata or {}}

    return process_data


@pytest.fixture
def test_store():
    """Test store for store dispatcher tests"""
    store_data = {
        "store1": {"key1": "value1", "key2": 42},
        "store2": {"item1": [1, 2, 3], "item2": {"nested": "data"}},
    }

    def store_getter(store_id: str):
        if store_id not in store_data:
            store_data[store_id] = {}
        return store_data[store_id]

    return store_getter, store_data


# Basic functionality tests


def test_simple_function_dispatch(simple_functions):
    """Test basic function to endpoint conversion"""
    app = mk_fastapi_app(simple_functions)
    client = TestClient(app)

    # Test add function
    response = client.post("/add", json={"a": 5, "b": 3})
    assert response.status_code == 200
    assert response.json() == 8

    # Test with default
    response = client.post("/add", json={"a": 5})
    assert response.status_code == 200
    assert response.json() == 7

    # Test greet function
    response = client.post("/greet", json={"name": "Alice", "greeting": "Hi"})
    assert response.status_code == 200
    assert response.json() == "Hi, Alice!"

    # Test with defaults
    response = client.post("/greet", json={})
    assert response.status_code == 200
    assert response.json() == "Hello, world!"


def test_dict_configuration():
    """Test dict-based function configuration"""

    def multiply(x: float, y: float) -> float:
        return x * y

    def divide(x: float, y: float) -> float:
        if y == 0:
            raise ValueError("Division by zero")
        return x / y

    funcs = {
        multiply: {
            "path": "/math/multiply",
            "methods": ["GET", "POST"],
            "summary": "Multiply two numbers",
        },
        divide: {
            "path": "/math/divide",
            "tags": ["mathematics"],
        },
    }

    app = mk_fastapi_app(funcs)
    client = TestClient(app)

    # Test custom path
    response = client.post("/math/multiply", json={"x": 4, "y": 5})
    assert response.status_code == 200
    assert response.json() == 20

    # Test GET method also works
    response = client.get("/math/multiply", json={"x": 4, "y": 5})
    assert response.status_code == 200

    # Test divide
    response = client.post("/math/divide", json={"x": 10, "y": 2})
    assert response.status_code == 200
    assert response.json() == 5


def test_input_transformation():
    """Test input transformation functionality"""

    def process(data: list[int], factor: int = 2) -> int:
        return sum(data) * factor

    # Create ingress that converts string to list of ints
    input_trans = mk_json_ingress({'data': lambda x: [int(i) for i in x.split(',')]})

    app = mk_fastapi_app(
        {process: {"input_trans": input_trans}},
    )
    client = TestClient(app)

    # Send data as string, should be converted to list
    response = client.post("/process", json={"data": "1,2,3,4", "factor": 3})
    assert response.status_code == 200
    assert response.json() == 30  # (1+2+3+4) * 3


def test_output_transformation():
    """Test output transformation functionality"""

    class CustomObject:
        def __init__(self, name: str, value: int):
            self.name = name
            self.value = value

    def create_object(name: str, value: int) -> CustomObject:
        return CustomObject(name, value)

    # Create egress that converts CustomObject to dict
    output_trans = mk_json_egress(
        {CustomObject: lambda obj: {"name": obj.name, "value": obj.value}}
    )

    app = mk_fastapi_app(
        {create_object: {"output_trans": output_trans}},
    )
    client = TestClient(app)

    response = client.post("/create_object", json={"name": "test", "value": 42})
    assert response.status_code == 200
    assert response.json() == {"name": "test", "value": 42}


def test_app_wide_configuration():
    """Test app-wide configuration options"""

    def func1(a: int) -> int:
        return a * 2

    def func2(b: int) -> int:
        return b * 3

    app = mk_fastapi_app(
        [func1, func2],
        path_prefix="/api/v1",
        default_methods=["GET", "POST"],
        path_template="/compute/{func_name}",
    )
    client = TestClient(app)

    # Test custom path template and prefix
    response = client.post("/api/v1/compute/func1", json={"a": 5})
    assert response.status_code == 200
    assert response.json() == 10

    response = client.get("/api/v1/compute/func2", json={"b": 4})
    assert response.status_code == 200
    assert response.json() == 12


def test_name_based_ingress():
    """Test name-based ingress transformation"""

    def calculate(numbers: list[int], operation: str) -> Any:
        if operation == "sum":
            return sum(numbers)
        elif operation == "product":
            result = 1
            for n in numbers:
                result *= n
            return result
        else:
            return None

    # Transform specific argument by name
    ingress = name_based_ingress(
        numbers=lambda x: [int(i) for i in x.split()], operation=lambda x: x.lower()
    )

    app = mk_fastapi_app(
        {calculate: {"input_trans": ingress}},
    )
    client = TestClient(app)

    response = client.post(
        "/calculate", json={"numbers": "1 2 3 4", "operation": "SUM"}
    )
    assert response.status_code == 200
    assert response.json() == 10


def test_store_dispatcher(test_store):
    """Test store dispatcher functionality"""
    store_getter, store_data = test_store

    app = mk_store_dispatcher(store_getter, path_prefix="/storage")
    client = TestClient(app)

    # Test list keys
    response = client.get("/storage/store1/keys")
    assert response.status_code == 200
    assert set(response.json()) == {"key1", "key2"}

    # Test get value
    response = client.get("/storage/store1/values/key1")
    assert response.status_code == 200
    assert response.json() == "value1"

    # Test set value
    response = client.put("/storage/store1/values/key3", json={"value": "new_value"})
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

    # Verify value was set
    assert store_data["store1"]["key3"] == "new_value"

    # Test delete
    response = client.delete("/storage/store1/values/key3")
    assert response.status_code == 200
    assert "key3" not in store_data["store1"]


def test_complex_types(typed_function):
    """Test handling of complex types"""
    app = mk_fastapi_app([typed_function])
    client = TestClient(app)

    response = client.post(
        "/process_data",
        json={
            "numbers": [1, 2, 3],
            "multiplier": 2.5,
            "metadata": {"source": "test", "version": 1},
        },
    )

    assert response.status_code == 200
    result = response.json()
    assert result["result"] == [2.5, 5.0, 7.5]
    assert result["sum"] == 15.0
    assert result["metadata"]["source"] == "test"


def test_missing_required_params():
    """Test error handling for missing required parameters"""

    def requires_param(required: str, optional: str = "default") -> str:
        return f"{required} - {optional}"

    app = mk_fastapi_app([requires_param])
    client = TestClient(app)

    # Missing required param should fail
    response = client.post("/requires_param", json={"optional": "test"})
    assert response.status_code == 422  # Unprocessable Entity

    # With required param should work
    response = client.post("/requires_param", json={"required": "value"})
    assert response.status_code == 200
    assert response.json() == "value - default"


def test_function_with_no_params():
    """Test function with no parameters"""

    def no_params() -> str:
        return "Hello from no params!"

    app = mk_fastapi_app([no_params])
    client = TestClient(app)

    response = client.post("/no_params", json={})
    assert response.status_code == 200
    assert response.json() == "Hello from no params!"


def test_function_list_with_dict_spec():
    """Test mixed specification format"""

    def func1(x: int) -> int:
        return x * 2

    def func2(y: int) -> int:
        return y + 10

    funcs = [
        {"func": func1, "path": "/double"},
        {"func": func2, "path": "/add_ten"},
    ]

    app = mk_fastapi_app(funcs)
    client = TestClient(app)

    response = client.post("/double", json={"x": 5})
    assert response.status_code == 200
    assert response.json() == 10

    response = client.post("/add_ten", json={"y": 5})
    assert response.status_code == 200
    assert response.json() == 15


def test_custom_defaults():
    """Test custom defaults in route config"""

    def greet(name: str, greeting: str = "Hello") -> str:
        return f"{greeting}, {name}!"

    # Override the default for greeting
    app = mk_fastapi_app({greet: {"defaults": {"greeting": "Bonjour"}}})
    client = TestClient(app)

    # Should use custom default
    response = client.post("/greet", json={"name": "Marie"})
    assert response.status_code == 200
    assert response.json() == "Bonjour, Marie!"

    # Can still override
    response = client.post("/greet", json={"name": "Marie", "greeting": "Salut"})
    assert response.status_code == 200
    assert response.json() == "Salut, Marie!"


def test_existing_app_integration():
    """Test adding routes to existing FastAPI app"""
    from fastapi import FastAPI

    # Create app with existing route
    app = FastAPI()

    @app.get("/existing")
    def existing_route():
        return {"message": "existing"}

    # Add new routes via mk_fastapi_app
    def new_func(value: int) -> int:
        return value * 2

    mk_fastapi_app([new_func], app=app)

    client = TestClient(app)

    # Test existing route still works
    response = client.get("/existing")
    assert response.status_code == 200
    assert response.json() == {"message": "existing"}

    # Test new route
    response = client.post("/new_func", json={"value": 21})
    assert response.status_code == 200
    assert response.json() == 42


def test_error_handling():
    """Test error handling in functions"""

    def may_fail(x: int, fail: bool = False) -> int:
        if fail:
            raise ValueError("Intentional failure")
        return x * 2

    app = mk_fastapi_app([may_fail])
    client = TestClient(app)

    # Success case
    response = client.post("/may_fail", json={"x": 5, "fail": False})
    assert response.status_code == 200
    assert response.json() == 10

    # Failure case - should propagate as 500
    response = client.post("/may_fail", json={"x": 5, "fail": True})
    assert response.status_code == 500


def test_docstring_as_description():
    """Test that docstrings are used as endpoint descriptions"""

    def documented_func(x: int) -> int:
        """This function doubles the input.

        It's very useful for doubling things.
        """
        return x * 2

    app = mk_fastapi_app([documented_func])

    # Check OpenAPI schema
    assert (
        "This function doubles the input"
        in app.openapi()["paths"]["/documented_func"]["post"]["description"]
    )


# Parametrized tests for edge cases


@pytest.mark.parametrize(
    "func_spec,expected_error",
    [
        ({"not_callable": {}}, ValueError),
        ([{"no_func_key": "data"}], ValueError),
        ("not_iterable_or_dict", TypeError),
    ],
)
def test_invalid_func_specs(func_spec, expected_error):
    """Test invalid function specifications"""
    with pytest.raises(expected_error):
        mk_fastapi_app(func_spec)


@pytest.mark.parametrize(
    "path_template,expected_path",
    [
        ("/{func_name}", "/test_func"),
        ("/api/{func_name}/execute", "/api/test_func/execute"),
        ("/v1/{func_name}", "/v1/test_func"),
    ],
)
def test_path_templates(path_template, expected_path):
    """Test different path template formats"""

    def test_func(x: int) -> int:
        return x

    app = mk_fastapi_app([test_func], path_template=path_template)
    client = TestClient(app)

    response = client.post(expected_path, json={"x": 1})
    assert response.status_code == 200
    assert response.json() == 1


if __name__ == "__main__":
    pytest.main([__file__])
