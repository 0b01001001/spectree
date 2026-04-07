from typing import Any, Protocol, TypeAlias, TypeVar

ModelClass: TypeAlias = type[Any]
ModelT = TypeVar("ModelT")


class ModelAdapter(Protocol):
    validation_error: type[Exception]

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
    ) -> ModelClass: ...

    def make_list_model(self, model: ModelClass) -> ModelClass: ...

    def json_schema(
        self,
        model: ModelClass,
        *,
        ref_template: str,
        mode: str = "validation",
    ) -> dict[str, Any]: ...

    def validation_error_errors(self, err: Exception) -> Any: ...

    def validation_error_model_name(self, err: Exception) -> str: ...

    def is_root_model(self, value: Any) -> bool: ...

    def is_root_model_instance(self, value: Any) -> bool: ...
