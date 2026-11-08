import json
from dataclasses import dataclass
from typing import Annotated

import pytest

from tests.common_dataclass import SimpleModel


def _partial_model_instance_value(model_case, kind):
    simple_model = model_case.get_model(SimpleModel)
    values = {
        "model": simple_model(user_id=1),
        "list-with-model": [0, simple_model(user_id=1)],
        "list-without-model": [1, 2, 3],
        "tuple-with-model": (0, simple_model(user_id=1)),
        "tuple-without-model": (0, 1),
        "dict-with-model": {"test": simple_model(user_id=1)},
        "nested-dict-with-model": {"test": [simple_model(user_id=1)]},
        "nested-list-with-model": [0, [1, simple_model(user_id=1)]],
    }

    return values[kind]


def test_validate_obj_and_is_model_instance(model_case):
    adapter = model_case.adapter
    simple_model = model_case.get_model(SimpleModel)

    instance = model_case.validate_obj(simple_model, {"user_id": "1"})

    assert model_case.dump_python(instance) == {"user_id": 1}
    assert adapter.is_model_instance(instance, simple_model) is True
    assert adapter.is_model_instance({"user_id": 1}, simple_model) is False
    assert adapter.is_model_instance(simple_model, simple_model) is False


def test_plain_dataclass_is_supported_as_a_model(model_case):
    adapter = model_case.adapter

    instance = adapter.validate_obj(SimpleModel, {"user_id": "1"})

    assert instance == SimpleModel(user_id=1)
    assert adapter.is_model_type(SimpleModel) is True
    assert adapter.is_model_instance(instance, SimpleModel) is True
    assert adapter.dump_json(instance) == b'{"user_id":1}'
    assert (
        adapter.json_schema(
            SimpleModel,
            ref_template="#/components/schemas/{model}",
        )["properties"]["user_id"]["type"]
        == "integer"
    )


def test_root_model_instances(model_case):
    adapter = model_case.adapter
    dummy_root_model = model_case.get_model(list[int], name="DummyRootModel")
    nested_root_model = model_case.get_model(
        dummy_root_model,
        name="NestedRootModel",
    )

    root_instance = model_case.validate_obj(
        dummy_root_model,
        [1, 2, 3],
    )
    nested_root_instance = model_case.validate_obj(
        nested_root_model,
        root_instance,
    )

    assert adapter.is_model_instance(root_instance, dummy_root_model) is True
    assert (
        adapter.is_model_instance(
            nested_root_instance,
            nested_root_model,
        )
        is True
    )
    assert model_case.dump_python(nested_root_instance) == [1, 2, 3]


def test_plain_dataclass_with_root_like_field_is_model_instance(model_case):
    lookalike = model_case.root_model_lookalike(__root__=["False"])

    assert (
        model_case.adapter.is_model_instance(
            lookalike,
            model_case.root_model_lookalike,
        )
        is True
    )


@pytest.mark.parametrize(
    "kind, expected",
    [
        ("model", True),
        ("list-with-model", True),
        ("list-without-model", False),
        ("tuple-with-model", True),
        ("tuple-without-model", False),
        ("dict-with-model", True),
        ("nested-dict-with-model", True),
        ("nested-list-with-model", True),
    ],
)
def test_is_partial_model_instance(model_case, kind, expected):
    value = _partial_model_instance_value(model_case, kind)

    assert model_case.adapter.is_partial_model_instance(value) is expected


def test_dump_json(model_case):
    simple_model = model_case.get_model(SimpleModel)

    assert model_case.dump_python(simple_model(user_id=1)) == {"user_id": 1}
    assert model_case.dump_python(
        model_case.validate_obj(
            model_case.get_model(list[int], name="DummyRootModel"),
            [1, 2, 3],
        )
    ) == [1, 2, 3]
    assert model_case.dump_python(
        model_case.validate_obj(
            model_case.get_model(list[SimpleModel], name="Users"),
            [
                {"user_id": 1},
                {"user_id": 2},
            ],
        )
    ) == [{"user_id": 1}, {"user_id": 2}]


def test_validate_json_list_model(model_case):
    list_model = model_case.adapter.make_list_model(model_case.get_model(SimpleModel))
    instance = model_case.validate_json(list_model, b'[{"user_id": 1}, {"user_id": 2}]')

    assert model_case.dump_python(instance) == [
        {"user_id": 1},
        {"user_id": 2},
    ]


def test_json_schema(model_case):
    schema = model_case.adapter.json_schema(
        model_case.get_model(SimpleModel),
        ref_template="#/components/schemas/{model}",
    )

    assert schema["type"] == "object"
    assert schema["properties"]["user_id"]["type"] == "integer"


def test_validation_errors(model_case):
    with pytest.raises(model_case.adapter.validation_error) as exc_info:
        model_case.validate_obj(model_case.get_model(SimpleModel), {"user_id": "bad"})

    errors = model_case.adapter.validation_errors(exc_info.value)

    assert isinstance(errors, list)
    assert list(errors[0]["loc"]) == ["user_id"]
    assert errors[0]["msg"]
    assert errors[0]["type"]


@pytest.mark.parametrize(
    "build, value, expected",
    [
        pytest.param(
            lambda model: list[model],
            [{"user_id": "1"}],
            [{"user_id": 1}],
            id="list",
        ),
        pytest.param(
            lambda model: dict[str, model],
            {"a": {"user_id": "1"}},
            {"a": {"user_id": 1}},
            id="dict",
        ),
        pytest.param(
            lambda model: model | None,
            {"user_id": "1"},
            {"user_id": 1},
            id="optional",
        ),
        pytest.param(
            lambda model: Annotated[model, "metadata"],
            {"user_id": "1"},
            {"user_id": 1},
            id="annotated",
        ),
    ],
)
def test_type_expressions_are_models(model_case, build, value, expected):
    adapter = model_case.adapter
    simple_model = model_case.get_model(SimpleModel)
    model = build(simple_model)

    instance = adapter.validate_obj(model, value)

    assert adapter.is_model_type(model) is True
    assert model_case.dump_python(instance) == expected
    assert (
        model_case.dump_python(adapter.validate_json(model, json.dumps(value).encode()))
        == expected
    )
    assert adapter.is_model_instance(value, model) is False
    assert isinstance(adapter.is_model_instance(instance, model), bool)
    assert isinstance(
        adapter.json_schema(model, ref_template="#/components/schemas/{model}"), dict
    )
    with pytest.raises(adapter.validation_error):
        adapter.validate_obj(model, {"unexpected": "shape"})


@dataclass(frozen=True, slots=True)
class FrozenSlotsModel:
    user_id: int
    label: str = "default"


@dataclass
class NestedModel:
    child: SimpleModel
    tags: list[int]


def test_frozen_and_slots_dataclass_is_supported_as_a_model(model_case):
    adapter = model_case.adapter
    instance = FrozenSlotsModel(user_id=1)

    assert adapter.is_model_type(FrozenSlotsModel) is True
    assert adapter.is_model_instance(instance, FrozenSlotsModel) is True
    assert adapter.is_model_instance({"user_id": 1}, FrozenSlotsModel) is False
    assert adapter.validate_obj(FrozenSlotsModel, {"user_id": "1"}) == instance
    assert adapter.validate_json(FrozenSlotsModel, b'{"user_id":1}') == instance
    assert adapter.dump_json(instance) == b'{"user_id":1,"label":"default"}'
    schema = adapter.json_schema(
        FrozenSlotsModel, ref_template="#/components/schemas/{model}"
    )
    assert schema["properties"]["user_id"]["type"] == "integer"
    assert schema["properties"]["label"]["type"] == "string"


@pytest.mark.parametrize(
    "build, payload, item_of",
    [
        pytest.param(lambda m: m, b'{"child":{"user_id":42},"tags":[1,2,3]}', None),
        pytest.param(lambda m: list[m], b'[{"child":{"user_id":1},"tags":[]}]', 0),
        pytest.param(
            lambda m: dict[str, m], b'{"a":{"child":{"user_id":1},"tags":[]}}', "a"
        ),
        pytest.param(
            lambda m: Annotated[m, "metadata"],
            b'{"child":{"user_id":7},"tags":[1]}',
            None,
        ),
        pytest.param(lambda m: m | None, b'{"child":{"user_id":7},"tags":[1]}', None),
    ],
    ids=["model", "list", "dict", "annotated", "optional"],
)
def test_json_round_trip_preserves_dataclass_types(model_case, build, payload, item_of):
    adapter = model_case.adapter

    decoded = adapter.validate_json(build(NestedModel), payload)
    item = decoded if item_of is None else decoded[item_of]

    assert type(item) is NestedModel
    assert type(item.child) is SimpleModel
    assert adapter.dump_json(decoded) == payload
