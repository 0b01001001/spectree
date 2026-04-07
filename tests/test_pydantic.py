import json
from dataclasses import dataclass
from typing import Any, List

import pytest
from pydantic import BaseModel

from spectree.model_adapter import ModelAdapter, get_default_model_adapter
from spectree.model_adapter.pydantic import PydanticModelAdapter

ADAPTER = get_default_model_adapter()

DummyRootModel = ADAPTER.make_root_model(List[int], name="DummyRootModel")

NestedRootModel = ADAPTER.make_root_model(DummyRootModel, name="NestedRootModel")


class SimpleModel(BaseModel):
    user_id: int


Users = ADAPTER.make_root_model(List[SimpleModel], name="Users")


@dataclass
class RootModelLookalike:
    __root__: List[str]


@pytest.mark.parametrize(
    "value, expected",
    [
        (DummyRootModel, True),
        (DummyRootModel.model_validate([1, 2, 3]), False),
        (NestedRootModel, True),
        (
            NestedRootModel.model_validate(DummyRootModel.model_validate([1, 2, 3])),
            False,
        ),
        (SimpleModel, False),
        (SimpleModel(user_id=1), False),
        (RootModelLookalike, False),
        (RootModelLookalike(__root__=["False"]), False),
        (list, False),
        ([1, 2, 3], False),
        (str, False),
        ("str", False),
        (int, False),
        (1, False),
    ],
)
def test_is_root_model(value: Any, expected: bool):
    assert ADAPTER.is_root_model(value) is expected


@pytest.mark.parametrize(
    "value, expected",
    [
        (DummyRootModel, False),
        (DummyRootModel.model_validate([1, 2, 3]), True),
        (NestedRootModel, False),
        (
            NestedRootModel.model_validate(DummyRootModel.model_validate([1, 2, 3])),
            True,
        ),
        (SimpleModel, False),
        (SimpleModel(user_id=1), False),
        (RootModelLookalike, False),
        (RootModelLookalike(__root__=["False"]), False),
        (list, False),
        ([1, 2, 3], False),
        (str, False),
        ("str", False),
        (int, False),
        (1, False),
    ],
)
def test_is_root_model_instance(value, expected):
    assert ADAPTER.is_root_model_instance(value) is expected


@pytest.mark.parametrize(
    "value, expected",
    [
        (DummyRootModel, True),
        (DummyRootModel.model_validate([1, 2, 3]), False),
        (NestedRootModel, True),
        (
            NestedRootModel.model_validate(DummyRootModel.model_validate([1, 2, 3])),
            False,
        ),
        (SimpleModel, True),
        (SimpleModel(user_id=1), False),
        (RootModelLookalike, False),
        (RootModelLookalike(__root__=["False"]), False),
        (list, False),
        ([1, 2, 3], False),
        (str, False),
        ("str", False),
        (int, False),
        (1, False),
    ],
)
def test_is_base_model(value, expected):
    assert ADAPTER.is_model_type(value) is expected


@pytest.mark.parametrize(
    "value, expected",
    [
        (DummyRootModel, False),
        (DummyRootModel.model_validate([1, 2, 3]), True),
        (NestedRootModel, False),
        (
            NestedRootModel.model_validate(DummyRootModel.model_validate([1, 2, 3])),
            True,
        ),
        (SimpleModel, False),
        (SimpleModel(user_id=1), True),
        (RootModelLookalike, False),
        (RootModelLookalike(__root__=["False"]), False),
        (list, False),
        ([1, 2, 3], False),
        (str, False),
        ("str", False),
        (int, False),
        (1, False),
    ],
)
def test_is_base_model_instance(value, expected):
    assert ADAPTER.is_model_instance(value) is expected


@pytest.mark.parametrize(
    "value, expected",
    [
        (SimpleModel(user_id=1), True),
        ([0, SimpleModel(user_id=1)], True),
        ([1, 2, 3], False),
        ((0, SimpleModel(user_id=1)), True),
        ((0, 1), False),
        ({"test": SimpleModel(user_id=1)}, True),
        ({"test": [SimpleModel(user_id=1)]}, True),
        ([0, [1, SimpleModel(user_id=1)]], True),
    ],
)
def test_is_partial_base_model_instance(value, expected):
    assert ADAPTER.is_partial_model_instance(value) is expected, value


@pytest.mark.parametrize(
    "value, expected",
    [
        (SimpleModel(user_id=1), {"user_id": 1}),
        (DummyRootModel.model_validate([1, 2, 3]), [1, 2, 3]),
        (
            NestedRootModel.model_validate(DummyRootModel.model_validate([1, 2, 3])),
            [1, 2, 3],
        ),
        (
            Users.model_validate(
                [
                    SimpleModel(user_id=1),
                    SimpleModel(user_id=2),
                ]
            ),
            [{"user_id": 1}, {"user_id": 2}],
        ),
    ],
)
def test_serialize_model_instance(value, expected):
    assert json.loads(ADAPTER.dump_json(value)) == expected


def test_default_model_adapter_matches_protocol():
    adapter = ADAPTER

    assert isinstance(adapter, PydanticModelAdapter)
    assert hasattr(adapter, "validate_obj")
    assert hasattr(adapter, "validate_json")
    assert hasattr(adapter, "dump_json")

    typed_adapter: ModelAdapter = adapter
    assert typed_adapter.is_model_type(SimpleModel) is True
