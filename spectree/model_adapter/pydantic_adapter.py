from collections.abc import Mapping
from dataclasses import is_dataclass
from typing import Any, Sequence

from pydantic import BaseModel, RootModel, TypeAdapter, ValidationError
from pydantic_core import core_schema

from spectree._types import ModelAdapterType
from spectree.model_adapter.protocol import SchemaMode
from spectree.models import ValidationErrorElement


class ValidationErrorType(RootModel[Sequence[ValidationErrorElement]]):
    """Model of a validation error response."""


class BaseFile:
    """
    An uploaded file, will be assigned as the corresponding web framework's
    file object.
    """

    @classmethod
    def __get_pydantic_json_schema__(cls, _core_schema: Mapping[str, Any], _handler):
        return {"format": "binary", "type": "string"}

    @classmethod
    def __get_pydantic_core_schema__(cls, _source_type, _handler):
        return core_schema.with_info_plain_validator_function(cls.validate)

    @classmethod
    def validate(cls, value: Any, *_args, **_kwargs):
        return value


class PydanticModelAdapter(ModelAdapterType):
    """`pydantic` model adapter."""

    validation_error = ValidationError
    basefile = BaseFile

    def __init__(self) -> None:
        self._type_adapters: dict[type[Any], TypeAdapter[Any]] = {}

    def _type_adapter(self, value: type[Any]) -> TypeAdapter[Any]:
        adapter = self._type_adapters.get(value)
        if adapter is None:
            adapter = TypeAdapter(value)
            self._type_adapters[value] = adapter
        return adapter

    def is_model_type(self, value: type) -> bool:
        return (
            value is ValidationError
            or issubclass(value, BaseModel)
            or is_dataclass(value)
        )

    def is_model_instance(self, value: Any, model) -> bool:
        return isinstance(value, model)

    def is_partial_model_instance(self, value: Any) -> bool:
        if not value:
            return False
        if isinstance(value, BaseModel):
            return True
        if isinstance(value, dict):
            return any(
                self.is_partial_model_instance(key)
                or self.is_partial_model_instance(item)
                for key, item in value.items()
            )
        if isinstance(value, (list, tuple)):
            return any(self.is_partial_model_instance(item) for item in value)
        return False

    def validate_obj(self, model: type[Any], value: Any) -> Any:
        if issubclass(model, BaseModel):
            return model.model_validate(value)
        return self._type_adapter(model).validate_python(value)

    def validate_json(self, model: type[Any], value: bytes) -> Any:
        if issubclass(model, BaseModel):
            return model.model_validate_json(value)
        return self._type_adapter(model).validate_json(value)

    def dump_json(self, value: Any) -> bytes:
        instance = value
        if not isinstance(value, BaseModel):
            instance = self.validate_obj(type(instance), instance)
        if isinstance(instance, BaseModel):
            return instance.model_dump_json().encode("utf-8")
        return self._type_adapter(type(instance)).dump_json(instance)

    def make_root_model(
        self,
        root_type: Any,
        *,
        name: str = "GeneratedRootModel",
        module: str | None = None,
    ) -> type[BaseModel]:
        module_name = module or __name__
        return type(name, (RootModel[root_type],), {"__module__": module_name})

    def make_list_model(self, model: type[Any]) -> type[BaseModel]:
        return self.make_root_model(
            list[model],  # type: ignore[valid-type]
            name=f"{model.__name__}List",
            module=model.__module__,
        )

    def json_schema(
        self,
        model: type[Any],
        *,
        ref_template: str,
        mode: SchemaMode = "validation",
    ) -> dict[str, Any]:
        if issubclass(model, BaseModel):
            return model.model_json_schema(ref_template=ref_template, mode=mode)
        elif model is ValidationError:
            return ValidationErrorType.model_json_schema(
                ref_template=ref_template, mode=mode
            )
        return self._type_adapter(model).json_schema(
            ref_template=ref_template, mode=mode
        )

    def validation_errors(self, err: ValidationError) -> Any:
        return err.errors(include_context=False)
