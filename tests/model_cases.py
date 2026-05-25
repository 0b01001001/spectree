from __future__ import annotations

import importlib
import importlib.util
import json
from dataclasses import dataclass
from types import GenericAlias
from typing import Any

import pytest

from spectree._types import ModelAdapterType
from spectree.model_adapter import (
    get_msgspec_model_adapter,
    get_pydantic_model_adapter,
)

MODEL_CASE_PARAMS = [
    pytest.param("pydantic", id="pydantic"),
    pytest.param("msgspec", marks=pytest.mark.msgspec, id="msgspec"),
]


@dataclass
class RootModelLookalike:
    __root__: list[str]


@dataclass(frozen=True)
class ModelCase:
    name: str
    adapter: ModelAdapterType
    simple_model: Any
    dummy_root_model: Any
    nested_root_model: Any
    users_model: Any
    root_model_lookalike: type[RootModelLookalike] = RootModelLookalike

    def validate_obj(self, model: Any, value: Any) -> Any:
        return self.adapter.validate_obj(model, value)

    def validate_json(self, model: Any, value: bytes) -> Any:
        return self.adapter.validate_json(model, value)

    def dump_python(self, value: Any) -> Any:
        return json.loads(self.adapter.dump_json(value))


def _make_simple_model(base: Any) -> Any:
    return type(
        "SimpleModel",
        (base,),
        {
            "__annotations__": {"user_id": int},
            "__module__": __name__,
        },
    )


def build_model_case(name: str) -> ModelCase:
    if name == "pydantic":
        return _build_pydantic_case()
    if name == "msgspec":
        return _build_msgspec_case()
    raise ValueError(f"unknown model adapter case: {name}")


def _build_pydantic_case() -> ModelCase:
    if importlib.util.find_spec("pydantic") is None:
        pytest.skip("pydantic is not installed")

    pydantic = importlib.import_module("pydantic")
    adapter = get_pydantic_model_adapter()
    SimpleModel = _make_simple_model(pydantic.BaseModel)

    dummy_root_model = adapter.make_root_model(
        list[int],
        name="DummyRootModel",
        module=__name__,
    )
    nested_root_model = adapter.make_root_model(
        dummy_root_model,
        name="NestedRootModel",
        module=__name__,
    )
    users_model = adapter.make_root_model(
        GenericAlias(list, (SimpleModel,)),
        name="Users",
        module=__name__,
    )

    return ModelCase(
        name="pydantic",
        adapter=adapter,
        simple_model=SimpleModel,
        dummy_root_model=dummy_root_model,
        nested_root_model=nested_root_model,
        users_model=users_model,
    )


def _build_msgspec_case() -> ModelCase:
    if importlib.util.find_spec("msgspec") is None:
        pytest.skip("msgspec is not installed")

    msgspec = importlib.import_module("msgspec")
    adapter = get_msgspec_model_adapter()
    SimpleModel = _make_simple_model(msgspec.Struct)

    dummy_root_model = adapter.make_root_model(
        list[int],
        name="DummyRootModel",
        module=__name__,
    )
    nested_root_model = adapter.make_root_model(
        dummy_root_model,
        name="NestedRootModel",
        module=__name__,
    )
    users_model = adapter.make_root_model(
        GenericAlias(list, (SimpleModel,)),
        name="Users",
        module=__name__,
    )

    return ModelCase(
        name="msgspec",
        adapter=adapter,
        simple_model=SimpleModel,
        dummy_root_model=dummy_root_model,
        nested_root_model=nested_root_model,
        users_model=users_model,
    )
