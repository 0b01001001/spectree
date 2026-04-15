from typing import Any, List

from pydantic import BaseModel, RootModel, ValidationError

from .protocol import ModelAdapter, SchemaMode


class PydanticModelAdapter(ModelAdapter[BaseModel, ValidationError]):
    """`pydantic` model adapter."""

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

    def validate_obj(self, model: type[BaseModel], value: Any) -> BaseModel:
        return model.model_validate(value)

    def validate_json(self, model: type[BaseModel], value: bytes) -> BaseModel:
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
        module: str | None = None,
    ) -> type[BaseModel]:
        module_name = module or __name__
        return type(name, (RootModel[root_type],), {"__module__": module_name})

    def make_list_model(self, model: type[BaseModel]) -> type[BaseModel]:
        return self.make_root_model(
            List[model],  # type: ignore
            name=f"{model.__name__}List",
            module=model.__module__,
        )

    def json_schema(
        self,
        model: type[BaseModel],
        *,
        ref_template: str,
        mode: SchemaMode = "validation",
    ) -> dict[str, Any]:
        return model.model_json_schema(ref_template=ref_template, mode=mode)

    def validation_errors(self, err: ValidationError) -> Any:
        return err.errors(include_context=False)

    def validation_error_model_name(self, err: ValidationError) -> str:
        return getattr(err, "title", None) or err.model.__name__

    def is_root_model(self, value: Any) -> bool:
        return self.is_model_type(value) and any(
            f"{base.__module__}.{base.__name__}" == "pydantic.root_model.RootModel"
            for base in value.mro()
        )

    def is_root_model_instance(self, value: Any) -> bool:
        return self.is_root_model(type(value))
