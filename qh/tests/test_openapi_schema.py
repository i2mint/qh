"""Tests for JSON Schema derived from Python type hints in OpenAPI output.

Covers :func:`qh.openapi.python_type_to_json_schema` and the request/response
schema it feeds into the OpenAPI document — the capability that lets tools like
``openapi-typescript`` generate a typed client from ``qh``'s ``/openapi.json``.

The composite types under test are defined at **module level** on purpose:
``get_type_hints`` resolves string annotations against an object's module
globals, so a dataclass / ``TypedDict`` defined inside a test method would not
resolve.
"""

import enum
from dataclasses import dataclass, field
from typing import Literal, NamedTuple, Optional, TypedDict, Union

import pytest

from qh import mk_app, export_openapi, python_type_to_json_schema
from qh.openapi import enhance_openapi_schema


# --------------------------------------------------------------------------
# Composite types used across the tests
# --------------------------------------------------------------------------


@dataclass
class Point:
    """A 2-D point."""

    x: float
    y: float


@dataclass
class Annotated:
    """A point with an optional label and a defaulted weight."""

    point: Point
    label: Optional[str] = None
    weight: float = 1.0


class Color(enum.Enum):
    RED = "red"
    GREEN = "green"


class CorpusSummary(TypedDict):
    """A fully-required TypedDict (total=True)."""

    corpus_id: str
    n_segments: int


class PartialMeta(TypedDict, total=False):
    """A TypedDict whose every key is optional (total=False)."""

    note: str
    score: float


class Pair(NamedTuple):
    left: int
    right: int = 0


@dataclass
class TreeNode:
    """A self-referential dataclass — exercises the recursion guard."""

    value: int
    children: list["TreeNode"] = field(default_factory=list)


# --------------------------------------------------------------------------
# python_type_to_json_schema — primitives, containers, unions
# --------------------------------------------------------------------------


class TestPrimitivesAndContainers:
    def test_primitives(self):
        assert python_type_to_json_schema(int, {}) == {"type": "integer"}
        assert python_type_to_json_schema(str, {}) == {"type": "string"}
        assert python_type_to_json_schema(float, {}) == {"type": "number"}
        assert python_type_to_json_schema(bool, {}) == {"type": "boolean"}
        assert python_type_to_json_schema(type(None), {}) == {"type": "null"}

    def test_list(self):
        assert python_type_to_json_schema(list[str], {}) == {
            "type": "array",
            "items": {"type": "string"},
        }

    def test_nested_list(self):
        assert python_type_to_json_schema(list[list[float]], {}) == {
            "type": "array",
            "items": {"type": "array", "items": {"type": "number"}},
        }

    def test_dict(self):
        assert python_type_to_json_schema(dict[str, int], {}) == {
            "type": "object",
            "additionalProperties": {"type": "integer"},
        }

    def test_bare_containers(self):
        assert python_type_to_json_schema(list, {}) == {
            "type": "array",
            "items": {},
        }
        assert python_type_to_json_schema(dict, {}) == {
            "type": "object",
            "additionalProperties": {},
        }

    def test_optional(self):
        assert python_type_to_json_schema(Optional[int], {}) == {
            "anyOf": [{"type": "integer"}, {"type": "null"}]
        }

    def test_pep604_optional(self):
        assert python_type_to_json_schema(int | None, {}) == {
            "anyOf": [{"type": "integer"}, {"type": "null"}]
        }

    def test_union(self):
        schema = python_type_to_json_schema(Union[int, str], {})
        assert schema == {"anyOf": [{"type": "integer"}, {"type": "string"}]}

    def test_literal(self):
        assert python_type_to_json_schema(Literal["a", "b"], {}) == {
            "enum": ["a", "b"]
        }

    def test_enum(self):
        assert python_type_to_json_schema(Color, {}) == {"enum": ["red", "green"]}


# --------------------------------------------------------------------------
# python_type_to_json_schema — composite types into components
# --------------------------------------------------------------------------


class TestCompositeTypes:
    def test_dataclass_registered_as_ref(self):
        schemas = {}
        result = python_type_to_json_schema(Point, schemas)
        assert result == {"$ref": "#/components/schemas/Point"}
        assert schemas["Point"]["type"] == "object"
        assert schemas["Point"]["properties"]["x"] == {"type": "number"}
        assert set(schemas["Point"]["required"]) == {"x", "y"}
        assert schemas["Point"]["description"] == "A 2-D point."

    def test_dataclass_defaults_not_required(self):
        schemas = {}
        python_type_to_json_schema(Annotated, schemas)
        annotated = schemas["Annotated"]
        # Only ``point`` has no default → only ``point`` is required.
        assert annotated["required"] == ["point"]
        # The nested dataclass is registered too, and referenced.
        assert annotated["properties"]["point"] == {
            "$ref": "#/components/schemas/Point"
        }
        assert "Point" in schemas

    def test_typed_dict_total(self):
        schemas = {}
        python_type_to_json_schema(CorpusSummary, schemas)
        summary = schemas["CorpusSummary"]
        assert set(summary["required"]) == {"corpus_id", "n_segments"}

    def test_typed_dict_total_false(self):
        schemas = {}
        python_type_to_json_schema(PartialMeta, schemas)
        partial = schemas["PartialMeta"]
        # total=False → no key is required.
        assert "required" not in partial
        assert set(partial["properties"]) == {"note", "score"}

    def test_namedtuple(self):
        schemas = {}
        python_type_to_json_schema(Pair, schemas)
        pair = schemas["Pair"]
        # ``right`` has a default → not required.
        assert pair["required"] == ["left"]

    def test_list_of_dataclass(self):
        schemas = {}
        result = python_type_to_json_schema(list[Point], schemas)
        assert result == {
            "type": "array",
            "items": {"$ref": "#/components/schemas/Point"},
        }
        assert "Point" in schemas

    def test_self_referential_dataclass_terminates(self):
        schemas = {}
        result = python_type_to_json_schema(TreeNode, schemas)
        assert result == {"$ref": "#/components/schemas/TreeNode"}
        children = schemas["TreeNode"]["properties"]["children"]
        assert children == {
            "type": "array",
            "items": {"$ref": "#/components/schemas/TreeNode"},
        }

    def test_unknown_type_is_permissive(self):
        # An unannotated / unknown type maps to the empty (matches-anything) schema.
        assert python_type_to_json_schema(object, {}) == {}


# --------------------------------------------------------------------------
# Whole-document enhancement
# --------------------------------------------------------------------------


def make_point(x: float, y: float) -> Point:
    """Create a point from coordinates."""
    return Point(x, y)


def summarize(label: str, count: int = 0) -> CorpusSummary:
    """Summarize."""
    return CorpusSummary(corpus_id=label, n_segments=count)


def get_item(item_id: str) -> Point:
    """Fetch an item by id (convention-routed GET → query param)."""
    return Point(0.0, 0.0)


class TestEnhancedDocument:
    def test_request_body_schema(self):
        app = mk_app([make_point])
        spec = export_openapi(app)
        body = spec["paths"]["/make_point"]["post"]["requestBody"]
        schema = body["content"]["application/json"]["schema"]
        assert schema["properties"]["x"] == {"type": "number"}
        assert schema["properties"]["y"] == {"type": "number"}
        assert set(schema["required"]) == {"x", "y"}
        assert body["required"] is True

    def test_optional_param_not_required(self):
        app = mk_app([summarize])
        spec = export_openapi(app)
        schema = spec["paths"]["/summarize"]["post"]["requestBody"]["content"][
            "application/json"
        ]["schema"]
        # ``count`` has a default → not required.
        assert schema["required"] == ["label"]

    def test_response_schema_is_ref(self):
        app = mk_app([make_point])
        spec = export_openapi(app)
        response = spec["paths"]["/make_point"]["post"]["responses"]["200"]
        schema = response["content"]["application/json"]["schema"]
        assert schema == {"$ref": "#/components/schemas/Point"}

    def test_components_schemas_populated(self):
        app = mk_app([make_point, summarize])
        spec = export_openapi(app)
        schemas = spec["components"]["schemas"]
        assert "Point" in schemas
        assert "CorpusSummary" in schemas

    def test_get_route_uses_query_parameters(self):
        # A convention-routed GET turns non-path args into query parameters,
        # not a request body.
        app = mk_app([get_item], use_conventions=True)
        spec = export_openapi(app)
        # Find the get_item operation regardless of the conventional path.
        op = next(
            methods["get"]
            for methods in spec["paths"].values()
            if "get" in methods
        )
        assert "requestBody" not in op
        names = {p["name"]: p for p in op.get("parameters", [])}
        assert "item_id" in names
        assert names["item_id"]["schema"] == {"type": "string"}

    def test_none_return_is_null_schema(self):
        def drop(item_id: str) -> None:
            """Delete something."""

        app = mk_app([drop])
        spec = export_openapi(app)
        schema = spec["paths"]["/drop"]["post"]["responses"]["200"]["content"][
            "application/json"
        ]["schema"]
        assert schema == {"type": "null"}

    def test_include_schemas_false_skips_request_body(self):
        app = mk_app([make_point])
        spec = enhance_openapi_schema(app, include_schemas=False)
        assert "requestBody" not in spec["paths"]["/make_point"]["post"]


class TestInstalledOnApp:
    def test_mk_app_serves_enhanced_openapi_by_default(self):
        app = mk_app([make_point])
        spec = app.openapi()  # exercises the installed app.openapi override
        body = spec["paths"]["/make_point"]["post"].get("requestBody")
        assert body is not None
        assert "Point" in spec.get("components", {}).get("schemas", {})

    def test_enhanced_openapi_can_be_disabled(self):
        app = mk_app([make_point], enhanced_openapi=False)
        spec = app.openapi()
        # FastAPI's plain schema has no request body for a Request-based endpoint.
        assert "requestBody" not in spec["paths"]["/make_point"]["post"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
