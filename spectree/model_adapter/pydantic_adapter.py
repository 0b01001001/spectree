from collections.abc import Mapping, Sequence
from dataclasses import is_dataclass
from typing import Any, get_origin

from pydantic import BaseModel, RootModel, TypeAdapter, ValidationError
from pydantic_core import core_schema

from spectree.model_adapter.protocol import ModelAdapter, SchemaMode
from spectree.models import ValidationErrorElement
from spectree.utils import get_type_name


class ValidationErrorType(RootModel[Sequence[ValidationErrorElement]]):
    """Model of a validation error response."""


def _is_base_model(model: Any) -> bool:
    return isinstance(model, type) and issubclass(model, BaseModel)


def _payload_model(model: Any) -> Any:
    """Return the model that describes the payload of ``model``.

    ``ValidationError`` is used as the model of validation error responses; its
    payload is described by :class:`ValidationErrorType`.
    """
    return ValidationErrorType if model is ValidationError else model


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


class PydanticModelAdapter(ModelAdapter[Any, ValidationError, type[BaseFile]]):
    """`pydantic` model adapter."""

    validation_error = ValidationError
    basefile = BaseFile

    def __init__(self) -> None:
        self._type_adapters: dict[Any, TypeAdapter[Any]] = {}

    def _type_adapter(self, value: Any) -> TypeAdapter[Any]:
        try:
            adapter = self._type_adapters.get(value)
        except TypeError:
            # unhashable type expression, e.g. `Annotated` metadata without
            # `__hash__`: it cannot be cached
            return TypeAdapter(value)
        if adapter is None:
            adapter = TypeAdapter(value)
            self._type_adapters[value] = adapter
        return adapter

    def is_model_type(self, value: Any) -> bool:
        if isinstance(value, type):
            return (
                value is ValidationError
                or issubclass(value, BaseModel)
                or is_dataclass(value)
            )
        # Type expressions such as `list[Item]`, `Annotated[Item, ...]` or
        # `Item | None` are handled by a `TypeAdapter`.
        return get_origin(value) is not None

    def is_model_instance(self, value: Any, model) -> bool:
        return (
            isinstance(model, type)
            and (issubclass(model, BaseModel) or is_dataclass(model))
            and isinstance(value, model)
        )

    def is_partial_model_instance(self, value: Any) -> bool:
        if not value:
            return False
        if isinstance(value, BaseModel):
            return True
        if is_dataclass(value):
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

    def validate_obj(self, model: Any, value: Any) -> Any:
        model = _payload_model(model)
        if _is_base_model(model):
            return model.model_validate(value)
        return self._type_adapter(model).validate_python(value)

    def validate_json(self, model: Any, value: bytes) -> Any:
        model = _payload_model(model)
        if _is_base_model(model):
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
        name: str | None = None,
        module: str | None = None,
    ) -> type[BaseModel]:
        model_name = name or "GeneratedRootModel"
        module_name = module or __name__
        return type(model_name, (RootModel[root_type],), {"__module__": module_name})

    def make_list_model(self, model: type[Any]) -> type[BaseModel]:
        return self.make_root_model(
            list[model],  # type: ignore[valid-type]
            name=f"{get_type_name(model)}List",
            module=model.__module__,
        )

    def json_schema(
        self,
        model: Any,
        *,
        ref_template: str,
        mode: SchemaMode = "validation",
    ) -> dict[str, Any]:
        model = _payload_model(model)
        if _is_base_model(model):
            return model.model_json_schema(ref_template=ref_template, mode=mode)
        return self._type_adapter(model).json_schema(
            ref_template=ref_template, mode=mode
        )

    def validation_errors(self, err: ValidationError) -> Any:
        return err.errors(include_context=False)
