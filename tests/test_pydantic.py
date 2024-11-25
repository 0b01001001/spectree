from dataclasses import dataclass
from typing import Any, List

import pytest
from pydantic import BaseModel

from spectree._pydantic import (
    generate_root_model,
    is_base_model,
    is_base_model_instance,
    is_partial_base_model_instance,
    is_root_model,
    is_root_model_instance,
    serialize_model_instance,
)

DummyRootModel = generate_root_model(List[int], name="DummyRootModel")

NestedRootModel = generate_root_model(DummyRootModel, name="NestedRootModel")


class SimpleModel(BaseModel):
    user_id: int


Users = generate_root_model(List[SimpleModel], name="Users")


@dataclass
class RootModelLookalike:
    __root__: List[str]


@pytest.mark.parametrize(
    "value, expected",
    [
        (DummyRootModel, True),
        (DummyRootModel.parse_obj([1, 2, 3]), False),
        (NestedRootModel, True),
        (NestedRootModel.parse_obj(DummyRootModel.parse_obj([1, 2, 3])), False),
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
    assert is_root_model(value) is expected


@pytest.mark.parametrize(
    "value, expected",
    [
        (DummyRootModel, False),
        (DummyRootModel.parse_obj([1, 2, 3]), True),
        (NestedRootModel, False),
        (NestedRootModel.parse_obj(DummyRootModel.parse_obj([1, 2, 3])), True),
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
    assert is_root_model_instance(value) is expected


@pytest.mark.parametrize(
    "value, expected",
    [
        (DummyRootModel, True),
        (DummyRootModel.parse_obj([1, 2, 3]), False),
        (NestedRootModel, True),
        (NestedRootModel.parse_obj(DummyRootModel.parse_obj([1, 2, 3])), False),
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
    assert is_base_model(value) is expected


@pytest.mark.parametrize(
    "value, expected",
    [
        (DummyRootModel, False),
        (DummyRootModel.parse_obj([1, 2, 3]), True),
        (NestedRootModel, False),
        (NestedRootModel.parse_obj(DummyRootModel.parse_obj([1, 2, 3])), True),
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
    assert is_base_model_instance(value) is expected


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
    assert is_partial_base_model_instance(value) is expected, value


@pytest.mark.parametrize(
    "value, expected",
    [
        (SimpleModel(user_id=1), {"user_id": 1}),
        (DummyRootModel.parse_obj([1, 2, 3]), [1, 2, 3]),
        (NestedRootModel.parse_obj(DummyRootModel.parse_obj([1, 2, 3])), [1, 2, 3]),
        (
            Users.parse_obj(
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
    assert serialize_model_instance(value) == expected
