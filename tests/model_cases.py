from __future__ import annotations

import importlib
import importlib.util
import json
from dataclasses import MISSING, dataclass, fields, is_dataclass
from types import GenericAlias
from typing import Any, Callable, get_type_hints

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
class SimpleModel:
    user_id: int


@dataclass
class RootModelLookalike:
    __root__: list[str]


@dataclass(frozen=True)
class ModelCase:
    name: str
    adapter: ModelAdapterType
    _convert_dataclass: Callable[[type[Any]], Any]
    simple_model: Any
    dummy_root_model: Any
    nested_root_model: Any
    users_model: Any
    root_model_lookalike: type[RootModelLookalike] = RootModelLookalike

    def convert_dataclass(self, model_decl: type[Any]) -> Any:
        return self._convert_dataclass(model_decl)

    def validate_obj(self, model: Any, value: Any) -> Any:
        return self.adapter.validate_obj(model, value)

    def validate_json(self, model: Any, value: bytes) -> Any:
        return self.adapter.validate_json(model, value)

    def dump_python(self, value: Any) -> Any:
        return json.loads(self.adapter.dump_json(value))

    def list_of(self, model: Any) -> Any:
        return GenericAlias(list, (model,))


def _dataclass_field_types(model_decl: type[Any]) -> list[tuple[Any, Any]]:
    if not is_dataclass(model_decl):
        raise TypeError(f"{model_decl!r} is not a dataclass")

    type_hints = get_type_hints(model_decl, include_extras=True)
    return [
        (model_field, type_hints.get(model_field.name, model_field.type))
        for model_field in fields(model_decl)
    ]


def _build_pydantic_dataclass_converter(pydantic) -> Callable[[type[Any]], Any]:
    cache: dict[type[Any], Any] = {}

    def convert(model_decl: type[Any]) -> Any:
        if model_decl in cache:
            return cache[model_decl]

        field_definitions = {}
        for model_field, type_hint in _dataclass_field_types(model_decl):
            if model_field.default_factory is not MISSING:
                default = pydantic.Field(default_factory=model_field.default_factory)
            elif model_field.default is not MISSING:
                default = model_field.default
            else:
                default = ...
            field_definitions[model_field.name] = (type_hint, default)

        model = pydantic.create_model(
            model_decl.__name__,
            __base__=pydantic.BaseModel,
            __module__=model_decl.__module__,
            **field_definitions,
        )
        cache[model_decl] = model
        return model

    return convert


def _build_msgspec_dataclass_converter(msgspec) -> Callable[[type[Any]], Any]:
    cache: dict[type[Any], Any] = {}

    def convert(model_decl: type[Any]) -> Any:
        if model_decl in cache:
            return cache[model_decl]

        field_definitions: list[Any] = []
        for model_field, type_hint in _dataclass_field_types(model_decl):
            if model_field.default_factory is not MISSING:
                default = msgspec.field(default_factory=model_field.default_factory)
                field_definitions.append((model_field.name, type_hint, default))
            elif model_field.default is not MISSING:
                field_definitions.append(
                    (model_field.name, type_hint, model_field.default)
                )
            else:
                field_definitions.append((model_field.name, type_hint))

        model = msgspec.defstruct(
            model_decl.__name__,
            field_definitions,
            module=model_decl.__module__,
        )
        cache[model_decl] = model
        return model

    return convert


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
    convert_dataclass = _build_pydantic_dataclass_converter(pydantic)
    simple_model = convert_dataclass(SimpleModel)

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
        GenericAlias(list, (simple_model,)),
        name="Users",
        module=__name__,
    )

    return ModelCase(
        name="pydantic",
        adapter=adapter,
        _convert_dataclass=convert_dataclass,
        simple_model=simple_model,
        dummy_root_model=dummy_root_model,
        nested_root_model=nested_root_model,
        users_model=users_model,
    )


def _build_msgspec_case() -> ModelCase:
    if importlib.util.find_spec("msgspec") is None:
        pytest.skip("msgspec is not installed")

    msgspec = importlib.import_module("msgspec")
    adapter = get_msgspec_model_adapter()
    convert_dataclass = _build_msgspec_dataclass_converter(msgspec)
    simple_model = convert_dataclass(SimpleModel)

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
        GenericAlias(list, (simple_model,)),
        name="Users",
        module=__name__,
    )

    return ModelCase(
        name="msgspec",
        adapter=adapter,
        _convert_dataclass=convert_dataclass,
        simple_model=simple_model,
        dummy_root_model=dummy_root_model,
        nested_root_model=nested_root_model,
        users_model=users_model,
    )
