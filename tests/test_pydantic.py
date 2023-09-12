from dataclasses import dataclass
from typing import Any, List

import pytest

from spectree._pydantic import BaseModel, is_root_model


class DummyRootModel(BaseModel):
    __root__: List[int]


class SimpleModel(BaseModel):
    user_id: int


@dataclass
class RootModelLookalike:
    __root__: List[str]


@pytest.mark.parametrize(
    "value, expected",
    [
        (DummyRootModel, True),
        (SimpleModel, False),
        (RootModelLookalike, False),
        (list, False),
        (str, False),
        (int, False),
    ],
)
def test_is_root_model(value: Any, expected: bool):
    assert is_root_model(value) is expected
