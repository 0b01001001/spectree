import pytest

from spectree.schema_registry import SchemaCollisionError, SchemaRegistry


def create_registry():
    return SchemaRegistry(
        naming_strategy=lambda model: model["name"],
        nested_naming_strategy=lambda parent, child: f"{parent}.{child}",
    )


def test_same_model_and_mode_is_registered_once():
    registry = create_registry()

    model = {"name": "User"}
    schema = {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
        },
    }

    first = registry.register(model, "validation", schema)
    second = registry.register(model, "validation", schema)

    assert first == "User"
    assert second == "User"
    assert list(registry) == ["User"]


def test_same_schema_can_be_shared_by_validation_and_serialization():
    registry = create_registry()

    model = {"name": "User"}
    schema = {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
        },
    }

    validation = registry.register(model, "validation", schema)
    serialization = registry.register(model, "serialization", schema)

    assert validation == "User"
    assert serialization == "User"
    assert list(registry) == ["User"]


def test_different_validation_and_serialization_schemas_get_distinct_names():
    registry = create_registry()

    model = {"name": "User"}

    validation_schema = {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
        },
    }

    serialization_schema = {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "display_name": {"type": "string"},
        },
    }

    validation = registry.register(
        model,
        "validation",
        validation_schema,
    )
    serialization = registry.register(
        model,
        "serialization",
        serialization_schema,
    )

    assert validation == "User"
    assert serialization == "User.serialization"

    assert set(registry) == {
        "User",
        "User.serialization",
    }


def test_different_models_with_same_name_raise():
    registry = create_registry()

    first_model = {"name": "User"}
    second_model = {"name": "User"}

    schema = {
        "type": "object",
    }

    registry.register(
        first_model,
        "validation",
        schema,
    )

    with pytest.raises(SchemaCollisionError):
        registry.register(
            second_model,
            "validation",
            schema,
        )


def test_different_models_with_same_name_across_modes_raise():
    registry = create_registry()

    first_model = {"name": "User"}
    second_model = {"name": "User"}

    schema = {
        "type": "object",
    }

    registry.register(
        first_model,
        "validation",
        schema,
    )

    with pytest.raises(SchemaCollisionError):
        registry.register(
            second_model,
            "serialization",
            schema,
        )


def test_nested_refs_use_final_component_name():
    registry = create_registry()

    model = {"name": "User"}

    schema = {
        "type": "object",
        "properties": {
            "profile": {
                "$ref": "#/components/schemas/Profile",
            },
        },
        "$defs": {
            "Profile": {
                "type": "object",
            },
        },
    }

    component_name = registry.register(
        model,
        "validation",
        schema,
    )

    assert component_name == "User"
    assert registry["User"]["properties"]["profile"]["$ref"] == (
        "#/components/schemas/User.Profile"
    )


def test_schemas_are_not_aliased_to_input():
    registry = create_registry()

    model = {"name": "User"}
    schema = {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
        },
    }

    registry.register(model, "validation", schema)

    schema["properties"]["name"]["description"] = "changed"

    assert "description" not in registry["User"]["properties"]["name"]