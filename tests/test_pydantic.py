import json
from dataclasses import dataclass
from typing import List

import pytest
from pydantic import BaseModel

from spectree.model_adapter import get_pydantic_model_adapter

ADAPTER = get_pydantic_model_adapter()

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
    assert ADAPTER.is_model_instance(value, BaseModel) is expected


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
