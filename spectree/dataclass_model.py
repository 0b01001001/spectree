import dataclasses
import re
from collections.abc import Mapping, Sequence
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


@dataclasses.dataclass
class AdapterBackedDataclass:
    @classmethod
    def __pre_init__(cls, kwargs: Any) -> Any:
        if not isinstance(kwargs, Mapping):
            return kwargs
        normalized = {}
        fields = {field.name: field for field in dataclasses.fields(cls)}

        renames = []
        for field in fields.values():
            if target := getattr(field.metadata, "rename", None):
                renames.append((field.name, target))
        for source, target in renames:
            fields[target] = fields.pop(source)

        for key, value in kwargs.items():
            norm = normalize_key(key)
            if norm in normalized:
                raise SpecTreeDuplicateField(cls.__name__, norm)
            field = fields[norm]
            if getattr(field.metadata, "format", "") == "url":
                validate_url(value, norm)
            normalized[normalize_key(key)] = value
        return normalized

    def __post_init__(self):
        pass

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

        The `include` and `exclude_none` only affects the outermost instance.
        """
        data = dataclasses.asdict(self)
        final = {}
        for key, value in data.items():
            if key not in include:
                continue
            if exclude_none and value is None:
                continue
            final[key] = value
        return final
