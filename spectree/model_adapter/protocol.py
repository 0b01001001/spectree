from typing import Any, Literal, Protocol, TypeAlias, TypeVar

ModelClass: TypeAlias = type[Any]
ModelT = TypeVar("ModelT")
ValidationErrorT = TypeVar("ValidationErrorT", bound=Exception)
SchemaMode: TypeAlias = Literal["validation", "serialization"]


class ModelAdapter(Protocol[ModelT, ValidationErrorT]):
    validation_error: type[ValidationErrorT]

    def is_model_type(self, value: Any) -> bool: ...

    def is_model_instance(self, value: Any) -> bool: ...

    def is_partial_model_instance(self, value: Any) -> bool: ...

    def validate_obj(self, model: type[ModelT], value: Any) -> ModelT: ...

    def validate_json(self, model: type[ModelT], value: bytes) -> ModelT: ...

    def dump_json(self, value: Any) -> bytes: ...

    def make_root_model(
        self,
        root_type: Any,
        *,
        name: str = "GeneratedRootModel",
        module: str | None = None,
    ) -> ModelClass: ...

    def make_list_model(self, model: ModelClass) -> ModelClass: ...

    def json_schema(
        self,
        model: ModelClass,
        *,
        ref_template: str,
        mode: SchemaMode = "validation",
    ) -> dict[str, Any]: ...

    def validation_errors(self, err: ValidationErrorT) -> Any: ...

    def validation_error_model_name(self, err: ValidationErrorT) -> str: ...

    def is_root_model(self, value: Any) -> bool: ...

    def is_root_model_instance(self, value: Any) -> bool: ...
