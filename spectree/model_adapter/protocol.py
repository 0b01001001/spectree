from typing import Any, Literal, Protocol, TypeAlias, TypeVar

# ModelSpec is not "any value accepted by Spectree".
# It is a type expression whose support is determined by the selected adapter.
ModelSpec: TypeAlias = Any
ModelT = TypeVar("ModelT")
ValidationErrorT = TypeVar("ValidationErrorT", bound=Exception)
BaseFileT = TypeVar("BaseFileT")

SchemaMode: TypeAlias = Literal["validation", "serialization"]


class ModelAdapter(Protocol[ModelT, ValidationErrorT, BaseFileT]):
    """The protocol of model adapter.

    A model spec is an adapter-defined runtime type expression. It may be a
    model class, a generic alias such as ``list[User]``, ``Annotated[...]``,
    or another type expression supported by the adapter.
    """

    validation_error: type[ValidationErrorT]
    basefile: BaseFileT

    def is_model_type(self, value: ModelSpec) -> bool:
        """Check if the value can be used to generate a schema."""
        ...

    def is_model_instance(self, value: Any, model: ModelSpec) -> bool:
        """Check if ``value`` is an instance of ``model`` under this adapter.

        If it is already a valid model instance, runtime validation may be
        skipped.
        """
        ...

    def is_partial_model_instance(self, value: Any) -> bool:
        ...

    def validate_obj(self, model: ModelSpec, value: Any) -> ModelT:
        ...

    def validate_json(self, model: ModelSpec, value: bytes) -> ModelT:
        ...

    def dump_json(self, value: Any) -> bytes:
        ...

    def make_root_model(
        self,
        root_type: ModelSpec,
        *,
        name: str | None = None,
        module: str | None = None,
    ) -> ModelSpec:
        ...

    def make_list_model(self, model: ModelSpec) -> ModelSpec:
        ...

    def json_schema(
        self,
        model: ModelSpec,
        *,
        ref_template: str,
        mode: SchemaMode = "validation",
    ) -> dict[str, Any]:
        ...

    def validation_errors(self, err: ValidationErrorT) -> Any:
        ...