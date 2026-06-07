from __future__ import annotations

import importlib
import importlib.util
import json
from dataclasses import MISSING, dataclass, fields, is_dataclass
from functools import lru_cache
from types import GenericAlias
from typing import (
    Annotated,
    Any,
    Callable,
    Union,
    cast,
    get_args,
    get_origin,
    get_type_hints,
)

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

DATACLASS_CONVERTER_CACHE_SIZE = 128
MODEL_DEFINITION_CACHE_SIZE = 128
DataclassConverter = Callable[[type[Any]], Any]
ModelResolver = Callable[[Any | None, str | None], Any | None]


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
    _get_model: ModelResolver
    root_model_lookalike: type[RootModelLookalike] = RootModelLookalike

    def get_model(
        self,
        model_def: Any | None,
        *,
        name: str | None = None,
    ) -> Any | None:
        return self._get_model(model_def, name)

    def validate_obj(self, model: Any, value: Any) -> Any:
        return self.adapter.validate_obj(model, value)

    def validate_json(self, model: Any, value: bytes) -> Any:
        return self.adapter.validate_json(model, value)

    def dump_python(self, value: Any) -> Any:
        return json.loads(self.adapter.dump_json(value))

    def list_of(self, model: Any) -> Any:
        return GenericAlias(list, (model,))


def _dataclass_field_types(model_def: type[Any]) -> list[tuple[Any, Any]]:
    if not is_dataclass(model_def):
        raise TypeError(f"{model_def!r} is not a dataclass")

    type_hints = get_type_hints(model_def, include_extras=True)
    return [
        (model_field, type_hints.get(model_field.name, model_field.type))
        for model_field in fields(model_def)
    ]


def _build_model_resolver(
    adapter: ModelAdapterType,
    convert_dataclass: DataclassConverter,
) -> ModelResolver:
    def convert_type_def(type_def: Any) -> Any:
        if is_dataclass(type_def):
            return convert_dataclass(cast(type[Any], type_def))

        origin = get_origin(type_def)
        if origin is None:
            return type_def

        args = tuple(convert_type_def(arg) for arg in get_args(type_def))
        if origin is Union:
            return Union[args]
        if origin is Annotated:
            return Annotated[args]
        return GenericAlias(origin, args)

    @lru_cache(maxsize=MODEL_DEFINITION_CACHE_SIZE)
    def get_model(
        model_def: Any | None,
        name: str | None,
    ) -> Any | None:
        if model_def is None:
            return None

        converted_def = convert_type_def(model_def)
        if is_dataclass(model_def):
            return converted_def

        origin = get_origin(model_def)
        if origin is list and name is None:
            item_model = get_args(converted_def)[0]
            return adapter.make_list_model(item_model)

        return adapter.make_root_model(converted_def, name=name, module=__name__)

    return cast(ModelResolver, get_model)


def _build_pydantic_dataclass_converter() -> DataclassConverter:
    pydantic = importlib.import_module("pydantic")
    base_model = pydantic.BaseModel
    create_model = pydantic.create_model
    field = pydantic.Field

    @lru_cache(maxsize=DATACLASS_CONVERTER_CACHE_SIZE)
    def convert(model_def: type[Any]) -> Any:
        field_definitions = {}
        for model_field, type_hint in _dataclass_field_types(model_def):
            if model_field.default_factory is not MISSING:
                default = field(default_factory=model_field.default_factory)
            elif model_field.default is not MISSING:
                default = model_field.default
            else:
                default = ...
            field_definitions[model_field.name] = (type_hint, default)

        model = create_model(
            model_def.__name__,
            __base__=base_model,
            __module__=model_def.__module__,
            **field_definitions,
        )
        return model

    return cast(DataclassConverter, convert)


def _build_msgspec_dataclass_converter() -> DataclassConverter:
    msgspec = importlib.import_module("msgspec")
    defstruct = msgspec.defstruct
    field = msgspec.field

    @lru_cache(maxsize=DATACLASS_CONVERTER_CACHE_SIZE)
    def convert(model_def: type[Any]) -> Any:
        field_definitions: list[Any] = []
        for model_field, type_hint in _dataclass_field_types(model_def):
            if model_field.default_factory is not MISSING:
                default = field(default_factory=model_field.default_factory)
                field_definitions.append((model_field.name, type_hint, default))
            elif model_field.default is not MISSING:
                field_definitions.append(
                    (model_field.name, type_hint, model_field.default)
                )
            else:
                field_definitions.append((model_field.name, type_hint))

        model = defstruct(
            model_def.__name__,
            field_definitions,
            module=model_def.__module__,
        )
        return model

    return cast(DataclassConverter, convert)


def build_model_case(name: str) -> ModelCase:
    if name == "pydantic":
        return _build_pydantic_case()
    if name == "msgspec":
        return _build_msgspec_case()
    raise ValueError(f"unknown model adapter case: {name}")


def _build_pydantic_case() -> ModelCase:
    if importlib.util.find_spec("pydantic") is None:
        pytest.skip("pydantic is not installed")

    adapter = get_pydantic_model_adapter()
    convert_dataclass = _build_pydantic_dataclass_converter()

    return ModelCase(
        name="pydantic",
        adapter=adapter,
        _get_model=_build_model_resolver(adapter, convert_dataclass),
    )


def _build_msgspec_case() -> ModelCase:
    if importlib.util.find_spec("msgspec") is None:
        pytest.skip("msgspec is not installed")

    adapter = get_msgspec_model_adapter()
    convert_dataclass = _build_msgspec_dataclass_converter()

    return ModelCase(
        name="msgspec",
        adapter=adapter,
        _get_model=_build_model_resolver(adapter, convert_dataclass),
    )
