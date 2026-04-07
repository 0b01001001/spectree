from typing import Any, List, TypeVar

from pydantic import BaseModel, RootModel, ValidationError

from .protocol import ModelClass

ModelT = TypeVar("ModelT", bound=BaseModel)


class PydanticModelAdapter:
    validation_error = ValidationError

    def __init__(self) -> None:
        self._response_model = self.make_root_model(Any, name="_PydanticResponseModel")

    def is_model_type(self, value: Any) -> bool:
        try:
            return issubclass(value, BaseModel)
        except TypeError:
            return False

    def is_model_instance(self, value: Any) -> bool:
        return self.is_model_type(type(value))

    def is_partial_model_instance(self, value: Any) -> bool:
        if not value:
            return False
        if self.is_model_instance(value):
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

    def validate_obj(self, model: type[ModelT], value: Any) -> ModelT:
        return model.model_validate(value)

    def validate_json(self, model: type[ModelT], value: bytes) -> ModelT:
        return model.model_validate_json(value)

    def dump_json(self, value: Any) -> bytes:
        instance = value
        if not self.is_model_instance(instance):
            instance = self.validate_obj(self._response_model, instance)
        return instance.model_dump_json().encode("utf-8")

    def make_root_model(
        self,
        root_type: Any,
        *,
        name: str = "GeneratedRootModel",
    ) -> ModelClass:
        return type(name, (RootModel[root_type],), {})

    def make_list_model(self, model: ModelClass) -> ModelClass:
        return self.make_root_model(List[model], name=f"{model.__name__}List")  # type: ignore

    def json_schema(
        self,
        model: ModelClass,
        *,
        ref_template: str,
        mode: str = "validation",
    ) -> dict[str, Any]:
        return model.model_json_schema(ref_template=ref_template, mode=mode)

    def validation_error_errors(self, err: Exception) -> Any:
        assert isinstance(err, ValidationError)
        return err.errors(include_context=False)

    def validation_error_model_name(self, err: Exception) -> str:
        assert isinstance(err, ValidationError)
        return getattr(err, "title", None) or err.model.__name__

    def is_root_model(self, value: Any) -> bool:
        return self.is_model_type(value) and any(
            f"{base.__module__}.{base.__name__}" == "pydantic.root_model.RootModel"
            for base in value.mro()
        )

    def is_root_model_instance(self, value: Any) -> bool:
        return self.is_root_model(type(value))
