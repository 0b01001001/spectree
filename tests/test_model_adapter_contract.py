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


def test_root_model_lookalike_is_not_model_instance(model_case):
    lookalike = model_case.root_model_lookalike(__root__=["False"])

    assert (
        model_case.adapter.is_model_instance(
            lookalike,
            model_case.root_model_lookalike,
        )
        is False
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
