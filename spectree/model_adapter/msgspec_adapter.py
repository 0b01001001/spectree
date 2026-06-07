import re
from typing import Annotated, Any, TypeAlias, get_args, get_origin

import msgspec

from spectree.model_adapter.protocol import ModelAdapter, SchemaMode
from spectree.models import ValidationErrorElement

_ERROR_PATH_RE = re.compile(r" - at `(?P<path>.+)`$")

MsgspecValidationError: TypeAlias = Annotated[
    list[ValidationErrorElement], msgspec.Meta(title="ValidationError")
]


BaseFile = Annotated[
    Any, msgspec.Meta(extra_json_schema={"format": "binary", "type": "string"})
]


def _parse_error_location(message: str) -> list[str]:
    match = _ERROR_PATH_RE.search(message)
    if match is None:
        return []
    path = match.group("path")
    if path == "$":
        return []
    path = path.removeprefix("$")
    path = path.replace("[", ".").replace("]", "")
    return [part for part in path.split(".") if part]


class MsgspecModelAdapter(ModelAdapter[Any, msgspec.ValidationError, BaseFile]):
    """`msgspec` model adapter."""

    validation_error = msgspec.ValidationError
    basefile = BaseFile

    def __init__(self) -> None:
        self.encoder = msgspec.json.Encoder()

    def is_model_type(self, value: type) -> bool:
        """All kinds of types are treated the same."""
        return True

    def is_model_instance(self, value: Any, model) -> bool:
        # msgspec accepts generic aliases like list[Item] and Annotated[...] as
        # validation models, but they cannot be passed to isinstance() directly.
        while (origin := get_origin(model)) is Annotated:
            model = get_args(model)[0]
        if origin is list:
            item_model = get_args(model)[0]
            return (
                isinstance(value, list)
                and isinstance(item_model, type)
                and all(isinstance(item, item_model) for item in value)
            )
        return (
            isinstance(model, type)
            and issubclass(model, msgspec.Struct)
            and isinstance(value, model)
        )

    def is_partial_model_instance(self, value: Any) -> bool:
        if not value:
            return False
        if isinstance(value, msgspec.Struct):
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
        return msgspec.convert(value, type=model, strict=False)

    def validate_json(self, model: type[Any], value: bytes) -> Any:
        return msgspec.json.decode(value, type=model, strict=False)

    def dump_json(self, value: Any) -> bytes:
        return self.encoder.encode(value)

    def make_root_model(
        self,
        root_type: type[Any],
        *,
        name: str | None = None,
        module: str | None = None,
    ) -> type[msgspec.Struct]:
        """
        All the types are treated the same in `msgspec`.

        See: https://github.com/jcrist/msgspec/issues/484
        """
        model_name = name or "GeneratedRootModel"
        T = Annotated[root_type, msgspec.Meta(title=model_name)]  # type: ignore
        return T  # type: ignore

    def make_list_model(self, model: type) -> type:
        list_model = self.make_root_model(list[model], name=f"{model.__name__}List")  # type: ignore
        return list_model

    def json_schema(
        self,
        model: type[Any],
        *,
        ref_template: str,
        mode: SchemaMode = "validation",
    ) -> dict[str, Any]:
        """
        `mode` is not supported by `msgspec`.

        See https://github.com/jcrist/msgspec/issues/686
        """
        if model is msgspec.ValidationError:
            model = MsgspecValidationError  # type: ignore
        ref_template = ref_template.replace("{model}", "{name}")
        schemas, components = msgspec.json.schema_components(
            (model,),
            ref_template=ref_template,
        )
        schema = schemas[0]

        # msgspec returns structs as a root $ref plus a component. SpecTree stores
        # the root model under its own naming_strategy key, so keep only true nested
        # components in $defs and return the root schema directly.
        ref = schema.get("$ref")
        if isinstance(ref, str):
            for key in tuple(components):
                if ref == ref_template.format(name=key):
                    schema = components.pop(key)
                    break

        if components:
            schema["$defs"] = components

        return schema

    def validation_errors(self, err: msgspec.ValidationError):
        """Expect a `list[ValidationErrorElement]`"""
        message = str(err)
        return [
            {
                "loc": _parse_error_location(message),
                "msg": _ERROR_PATH_RE.sub("", message),
                "type": "validation_error",
            }
        ]
