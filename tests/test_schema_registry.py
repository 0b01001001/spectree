import copy

import pytest

from spectree.schema_registry import SchemaRegistry
from spectree.utils import get_nested_key

REF = "#/components/schemas/"


def _flat(_parent, child):
    return child


def _components(registry, nested_naming_strategy=get_nested_key):
    models, definitions = registry.render(nested_naming_strategy)
    return {**models, **definitions}


def _item_schema(*properties: str) -> dict:
    return {
        "title": "Item",
        "type": "object",
        "properties": {name: {"type": "string"} for name in properties},
    }


def _nested_schema(child_type: str) -> dict:
    return {
        "type": "object",
        "properties": {"child": {"$ref": f"{REF}Child"}},
        "$defs": {
            "Child": {"type": "object", "properties": {"x": {"type": child_type}}}
        },
    }


def _register(registry, key, *schemas, first="validation"):
    modes = ("validation", "serialization")
    if first != "validation":
        modes = modes[::-1]
        schemas = schemas[::-1]
    for mode, schema in zip(modes, schemas, strict=True):
        registry.register(key, mode, schema)


def test_single_mode_is_published_under_the_key():
    registry = SchemaRegistry()
    registry.register("Item.1", "serialization", _item_schema("name"))

    assert registry.component_name("Item.1", "serialization") == "Item.1"
    assert _components(registry) == {"Item.1": _item_schema("name")}


def test_identical_modes_share_one_component():
    registry = SchemaRegistry()
    _register(registry, "Item.1", _item_schema("name"), _item_schema("name"))

    assert registry.component_name("Item.1", "validation") == "Item.1"
    assert registry.component_name("Item.1", "serialization") == "Item.1"
    assert _components(registry) == {"Item.1": _item_schema("name")}


@pytest.mark.parametrize("first", ["validation", "serialization"])
def test_differing_modes_are_published_separately_in_any_order(first):
    validation, serialization = _item_schema("name"), _item_schema("name", "computed")
    registry = SchemaRegistry()
    _register(registry, "Item.1", validation, serialization, first=first)

    assert registry.component_name("Item.1", "validation") == "Item.1"
    assert registry.component_name("Item.1", "serialization") == (
        "Item.1.serialization"
    )
    assert _components(registry) == {
        "Item.1": validation,
        "Item.1.serialization": serialization,
    }


def test_nested_definitions_are_lifted_and_named_after_the_final_parent():
    registry = SchemaRegistry()
    _register(registry, "Outer.1", _nested_schema("integer"), _nested_schema("string"))

    assert _components(registry) == {
        "Outer.1": {
            "type": "object",
            "properties": {"child": {"$ref": f"{REF}Outer.1.Child"}},
        },
        "Outer.1.serialization": {
            "type": "object",
            "properties": {"child": {"$ref": f"{REF}Outer.1.serialization.Child"}},
        },
        "Outer.1.Child": {"type": "object", "properties": {"x": {"type": "integer"}}},
        "Outer.1.serialization.Child": {
            "type": "object",
            "properties": {"x": {"type": "string"}},
        },
    }


@pytest.mark.parametrize("first", ["validation", "serialization"])
def test_shared_nested_names_keep_differing_modes_apart(first):
    """With a nested naming strategy that drops the parent name, a nested model
    whose schemas differ between modes is published under two names."""
    registry = SchemaRegistry()
    _register(
        registry,
        "Outer.1",
        _nested_schema("integer"),
        _nested_schema("string"),
        first=first,
    )

    assert _components(registry, _flat) == {
        "Outer.1": {"type": "object", "properties": {"child": {"$ref": f"{REF}Child"}}},
        "Outer.1.serialization": {
            "type": "object",
            "properties": {"child": {"$ref": f"{REF}Child.serialization"}},
        },
        "Child": {"type": "object", "properties": {"x": {"type": "integer"}}},
        "Child.serialization": {
            "type": "object",
            "properties": {"x": {"type": "string"}},
        },
    }


def test_shared_nested_names_compare_referenced_definitions():
    """`Line` has the same text in both modes, but refers to a `Product` that
    differs, so both are published per mode."""

    def schema(price_type):
        return {
            "type": "object",
            "properties": {"line": {"$ref": f"{REF}Line"}},
            "$defs": {
                "Line": {
                    "type": "object",
                    "properties": {"product": {"$ref": f"{REF}Product"}},
                },
                "Product": {
                    "type": "object",
                    "properties": {"price": {"type": price_type}},
                },
            },
        }

    registry = SchemaRegistry()
    _register(registry, "Order.1", schema("number"), schema("string"))

    components = _components(registry, _flat)

    assert components["Order.1.serialization"]["properties"]["line"] == {
        "$ref": f"{REF}Line.serialization"
    }
    assert components["Line.serialization"]["properties"]["product"] == {
        "$ref": f"{REF}Product.serialization"
    }
    assert components["Line"]["properties"]["product"] == {"$ref": f"{REF}Product"}
    assert components["Product"]["properties"]["price"] == {"type": "number"}
    assert components["Product.serialization"]["properties"]["price"] == {
        "type": "string"
    }


def test_identical_nested_definitions_share_one_name_across_modes():
    registry = SchemaRegistry()
    validation = _nested_schema("integer")
    serialization = copy.deepcopy(validation)
    serialization["properties"]["extra"] = {"type": "string"}
    _register(registry, "Outer.1", validation, serialization)

    components = _components(registry, _flat)

    assert set(components) == {"Outer.1", "Outer.1.serialization", "Child"}
    assert components["Outer.1.serialization"]["properties"]["child"] == {
        "$ref": f"{REF}Child"
    }


def test_recursive_definitions_point_to_the_lifted_component():
    registry = SchemaRegistry()
    registry.register(
        "Node.1",
        "validation",
        {
            "$ref": f"{REF}Node",
            "$defs": {
                "Node": {
                    "type": "object",
                    "properties": {
                        "children": {"type": "array", "items": {"$ref": f"{REF}Node"}}
                    },
                }
            },
        },
    )

    components = _components(registry)

    assert components["Node.1"] == {"$ref": f"{REF}Node.1.Node"}
    assert components["Node.1.Node"]["properties"]["children"]["items"] == {
        "$ref": f"{REF}Node.1.Node"
    }


def test_rendering_does_not_change_the_registry():
    original = _nested_schema("integer")
    registry = SchemaRegistry()
    registry.register("Outer.1", "validation", original)
    original["properties"]["changed"] = {"type": "null"}

    first = _components(registry)
    first["Outer.1"]["properties"].clear()
    first.clear()

    assert _components(registry) == _components(registry)
    assert set(_components(registry)) == {"Outer.1", "Outer.1.Child"}
    assert "changed" not in _components(registry)["Outer.1"]["properties"]


def test_render_separates_models_from_nested_definitions():
    registry = SchemaRegistry()
    registry.register("Outer.1", "validation", _nested_schema("integer"))

    models, definitions = registry.render(get_nested_key)

    assert set(models) == {"Outer.1"}
    assert set(definitions) == {"Outer.1.Child"}


def test_registering_a_key_and_mode_again_replaces_the_schema():
    registry = SchemaRegistry()
    registry.register("Item.1", "validation", _item_schema("old"))
    registry.register("Item.1", "validation", _item_schema("new"))

    assert _components(registry) == {"Item.1": _item_schema("new")}


def test_first_definition_wins_when_nested_names_of_one_mode_collide():
    registry = SchemaRegistry()
    registry.register("A.1", "validation", _nested_schema("integer"))
    registry.register("B.1", "validation", _nested_schema("string"))

    components = _components(registry, _flat)

    assert components["Child"] == _nested_schema("integer")["$defs"]["Child"]
    assert components["A.1"]["properties"]["child"] == {"$ref": f"{REF}Child"}
    assert components["B.1"]["properties"]["child"] == {"$ref": f"{REF}Child"}


def test_special_float_values_are_json_compatible():
    registry = SchemaRegistry()
    schema = {"type": "number", "maximum": float("inf")}
    registry.register("Number.1", "validation", copy.deepcopy(schema))

    assert _components(registry) == {
        "Number.1": {"type": "number", "maximum": "Infinity"}
    }
