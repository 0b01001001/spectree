from dataclasses import dataclass
from typing import Any, List

import pytest

from spectree._pydantic import BaseModel, is_root_model, serialize_model_instance


class DummyRootModel(BaseModel):
    __root__: List[int]


class NestedRootModel(BaseModel):
    __root__: DummyRootModel


class SimpleModel(BaseModel):
    user_id: int


class Users(BaseModel):
    __root__: list[SimpleModel]


@dataclass
class RootModelLookalike:
    __root__: List[str]


@pytest.mark.parametrize(
    "value, expected",
    [
        (DummyRootModel, True),
        (NestedRootModel, True),
        (SimpleModel, False),
        (RootModelLookalike, False),
        (list, False),
        (str, False),
        (int, False),
        (1, False),
    ],
)
def test_is_root_model(value: Any, expected: bool):
    assert is_root_model(value) is expected


@pytest.mark.parametrize(
    "value, expected",
    [
        (SimpleModel(user_id=1), {"user_id": 1}),
        (DummyRootModel(__root__=[1, 2, 3]), [1, 2, 3]),
        (NestedRootModel(__root__=DummyRootModel(__root__=[1, 2, 3])), [1, 2, 3]),
        (
            Users(
                __root__=[
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
