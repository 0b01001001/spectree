import re
from typing import Annotated, Any, TypeAlias

import msgspec

from spectree.model_adapter.protocol import ModelAdapter, SchemaMode
from spectree.models import ValidationErrorElement

_ERROR_PATH_RE = re.compile(r" - at `(?P<path>.+)`$")

MsgspecValidationError: TypeAlias = Annotated[
    list[ValidationErrorElement], msgspec.Meta(title="ValidationError")
]


class BaseFile:
    pass


def _dec_hook(typ: type, obj: Any):
    """DO NOT edit the basefile obj, leave it to the downstream."""
    if typ is BaseFile:
        return obj
    raise NotImplementedError(f"unsupported type {typ}")


def _schema_hook(typ: type[Any]) -> dict[str, Any]:
    if typ is BaseFile:
        return {"format": "binary", "type": "string"}
    raise NotImplementedError


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


class MsgspecModelAdapter(ModelAdapter[Any, msgspec.ValidationError, type[BaseFile]]):
    """`msgspec` model adapter."""

    validation_error = msgspec.ValidationError
    basefile: type[BaseFile]

    def __init__(self) -> None:
        self.encoder = msgspec.json.Encoder()

    def is_model_type(self, value: type) -> bool:
        """All kinds of types are treated the same."""
        return True

    def is_model_instance(self, value: Any, model) -> bool:
        """All kinds of types are treated the same."""
        return True

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
        return msgspec.convert(value, type=model, strict=False, dec_hook=_dec_hook)

    def validate_json(self, model: type[Any], value: bytes) -> Any:
        return msgspec.json.decode(value, type=model, strict=False)

    def dump_json(self, value: Any) -> bytes:
        return self.encoder.encode(value)

    def make_root_model(
        self,
        root_type: type[Any],
        *,
        name: str = "GeneratedRootModel",
        module: str | None = None,
    ) -> type[msgspec.Struct]:
        """
        All the types are treated the same in `msgspec`.

        See: https://github.com/jcrist/msgspec/issues/484
        """
        T = Annotated[root_type, msgspec.Meta(title=name)]  # type: ignore
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
        return msgspec.json.schema(
            model,
            schema_hook=_schema_hook,
            ref_template=ref_template.replace("{model}", "{name}"),
        )

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
