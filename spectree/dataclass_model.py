import dataclasses
import re
from collections.abc import Iterable, Mapping, Sequence
from typing import Any, TypeVar
from urllib.parse import urlsplit

from spectree.errors import SpecTreeDuplicateField, SpecTreeValidationError
from spectree.model_adapter import ModelAdapter

DataClassModelType = TypeVar("DataClassModelType", bound="AdapterBackedDataclass")


def normalize_key(key: str) -> str:
    key = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", key)
    key = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", key)
    return key.lower()


def validate_url(value: Any, field_name: str):
    if value is None:
        return
    if not isinstance(value, str):
        raise SpecTreeValidationError(f"{field_name} must be a string")
    parts = urlsplit(value)
    if not parts.scheme or not parts.netloc:
        raise SpecTreeValidationError(f"{field_name} must be a valid absolute URL")


def dict_exclude_none_value(items: Iterable[tuple[str, object]]):
    return {k: v for k, v in items if v is not None}


@dataclasses.dataclass
class AdapterBackedDataclass:
    """
    Limitation: cannot parse nested `AdapterBackedDataclass` when `__pre_init__`
    is required for the inner class.
    """

    @classmethod
    def __pre_init__(cls, kwargs: Any) -> Any:
        if not isinstance(kwargs, Mapping):
            return kwargs
        normalized = {}
        rename_rev = {
            val: key for key, val in getattr(cls, "__cls_renames__", {}).items()
        }

        for key, value in kwargs.items():
            norm = rename_rev[key] if key in rename_rev else normalize_key(key)
            if norm in normalized:
                raise SpecTreeDuplicateField(cls.__name__, norm)
            normalized[norm] = value
        return normalized

    def __post_init__(self):
        fields = {field.name: field for field in dataclasses.fields(self)}
        for name, field in fields.items():
            if "format" in field.metadata and field.metadata["format"] == "url":
                validate_url(getattr(self, name), name)

    @classmethod
    def model_validate(
        cls: type[DataClassModelType],
        value: Any,
        *,
        model_adapter: ModelAdapter[Any, Exception, Any],
    ) -> DataClassModelType:
        value = cls.__pre_init__(value)
        try:
            instance = model_adapter.validate_obj(cls, value)
        except model_adapter.validation_error as exc:
            raise SpecTreeValidationError from exc
        return instance

    def to_dict(
        self,
        *,
        include: Sequence[str] = (),
        exclude_none: bool = False,
    ) -> dict[str, Any]:
        """Dump the instance to a python dict.

        The `include` only affects the outermost instance.

        `exclude_none` only affects
        """
        data = dataclasses.asdict(
            self, dict_factory=dict_exclude_none_value if exclude_none else dict
        )
        final = {}
        renames = getattr(self, "__cls_renames__", {})
        for key, value in data.items():
            if key not in include:
                continue
            if key in renames:
                final[renames[key]] = value
            else:
                final[key] = value
        return final
