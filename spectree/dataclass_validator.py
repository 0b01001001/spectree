import re
from dataclasses import MISSING, Field, fields
from enum import Enum
from typing import (
    Any,
    ClassVar,
    Dict,
    Mapping,
    Optional,
    TypeVar,
    Union,
    get_args,
    get_origin,
)
from urllib.parse import urlsplit


class DataClassValidationError(ValueError):
    """Dataclass validation error."""


DataClassModelType = TypeVar("DataClassModelType", bound="DataClassValidator")
_NONE_TYPE = type(None)


class DataClassValidator:
    error_type: ClassVar[type[DataClassValidationError]] = DataClassValidationError

    def __post_init__(self) -> None:
        type(self).validate_instance(self)

    @staticmethod
    def normalize_key(key: str) -> str:
        key = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", key)
        key = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", key)
        return key.lower()

    @staticmethod
    def dataclass_fields(model: Any) -> tuple[Field, ...]:
        return fields(model)

    @classmethod
    def duplicate_key_error(cls, normalized_key: str) -> str:
        return f"duplicate field key for {normalized_key}"

    @classmethod
    def unknown_fields_error(
        cls, model_type: type[DataClassModelType], unknown_fields: list[str]
    ) -> str:
        unknown = ", ".join(unknown_fields)
        return f"unknown fields for {model_type.__name__}: {unknown}"

    @classmethod
    def missing_field_error(
        cls, model_type: type[DataClassModelType], field_name: str
    ) -> str:
        return f"{model_type.__name__}.{field_name} is required"

    @classmethod
    def invalid_model_error(cls, field_name: str) -> str:
        return f"{field_name} is invalid"

    @classmethod
    def ensure_mapping(cls, value: Any, field_name: str) -> Mapping[str, Any]:
        if not isinstance(value, Mapping):
            raise cls.error_type(f"{field_name} must be a mapping")
        return value

    @classmethod
    def ensure_str(cls, value: Any, field_name: str) -> str:
        if not isinstance(value, str):
            raise cls.error_type(f"{field_name} must be a string")
        return value

    @classmethod
    def ensure_bool(cls, value: Any, field_name: str) -> bool:
        if not isinstance(value, bool):
            raise cls.error_type(f"{field_name} must be a boolean")
        return value

    @classmethod
    def normalize_kwargs(cls, values: Mapping[str, Any]) -> Dict[str, Any]:
        normalized: Dict[str, Any] = {}
        seen: set[str] = set()
        for key, value in values.items():
            normalized_key = cls.normalize_key(key)
            if normalized_key in seen:
                raise cls.error_type(cls.duplicate_key_error(normalized_key))
            seen.add(normalized_key)
            normalized[normalized_key] = value
        return normalized

    @classmethod
    def validate_url(cls, value: Any, field_name: str) -> Optional[str]:
        if value is None:
            return None
        url = cls.ensure_str(value, field_name)
        parts = urlsplit(url)
        if not parts.scheme or not parts.netloc:
            raise cls.error_type(f"{field_name} must be a valid absolute URL")
        return url

    @classmethod
    def validate_enum(cls, enum_type: type[Enum], value: Any, field_name: str) -> Enum:
        if isinstance(value, enum_type):
            return value
        if not isinstance(value, str):
            raise cls.error_type(f"{field_name} must be a string")
        try:
            return enum_type(value)
        except ValueError as exc:
            allowed = ", ".join(item.value for item in enum_type)
            raise cls.error_type(f"{field_name} must be one of: {allowed}") from exc

    @classmethod
    def default_value(
        cls, dataclass_field: Any, model_type: type[DataClassModelType]
    ) -> Any:
        if dataclass_field.default_factory is not MISSING:
            return dataclass_field.default_factory()
        if dataclass_field.default is not MISSING:
            return dataclass_field.default
        raise cls.error_type(cls.missing_field_error(model_type, dataclass_field.name))

    @staticmethod
    def unwrap_optional(annotation: Any) -> tuple[Any, bool]:
        origin = get_origin(annotation)
        if origin is Union:
            args = tuple(arg for arg in get_args(annotation) if arg is not _NONE_TYPE)
            if len(args) == 1 and len(args) != len(get_args(annotation)):
                return args[0], True
        return annotation, False

    @classmethod
    def validate_model_type(cls, model_type: type, value: Any, field_name: str) -> Any:
        if callable(getattr(model_type, "from_value", None)):
            return model_type.from_value(value, field_name)
        if callable(getattr(model_type, "model_validate", None)):
            if isinstance(value, model_type):
                return value
            try:
                return model_type.model_validate(value)
            except (TypeError, ValueError) as exc:
                raise cls.error_type(cls.invalid_model_error(field_name)) from exc
        raise TypeError("unsupported model type")

    @classmethod
    def validate_annotation(  # noqa: PLR0911
        cls, annotation: Any, value: Any, field_name: str, metadata: Mapping[str, Any]
    ) -> Any:
        origin = get_origin(annotation)
        args = get_args(annotation)

        if metadata.get("format") == "url":
            return cls.validate_url(value, field_name)
        if annotation is str:
            return cls.ensure_str(value, field_name)
        if annotation is bool:
            return cls.ensure_bool(value, field_name)
        if isinstance(annotation, type) and issubclass(annotation, Enum):
            return cls.validate_enum(annotation, value, field_name)
        if isinstance(annotation, type) and (
            callable(getattr(annotation, "from_value", None))
            or callable(getattr(annotation, "model_validate", None))
        ):
            return cls.validate_model_type(annotation, value, field_name)
        if origin is Union:
            for union_arg in args:
                if union_arg is _NONE_TYPE:
                    if value is None:
                        return None
                    continue
                try:
                    return cls.validate_annotation(union_arg, value, field_name, {})
                except cls.error_type:
                    continue
            raise cls.error_type(cls.invalid_model_error(field_name))
        if origin is list and len(args) == 1:
            if not isinstance(value, list):
                raise cls.error_type(f"{field_name} must be a list")
            return [
                cls.validate_annotation(args[0], item, field_name, {}) for item in value
            ]
        if origin is dict and len(args) == 2 and args[0] is str:
            mapping = cls.ensure_mapping(value, field_name)
            return {
                cls.ensure_str(key, field_name): cls.validate_annotation(
                    args[1], item, field_name, {}
                )
                for key, item in mapping.items()
            }
        raise cls.error_type(
            f"unsupported configuration field type for {field_name}: {annotation!r}"
        )

    @classmethod
    def validate_field(cls, dataclass_field: Any, value: Any, field_name: str) -> Any:
        metadata = dataclass_field.metadata
        if validator_name := metadata.get("validator"):
            return getattr(cls, validator_name)(value, field_name)

        annotation, optional = cls.unwrap_optional(dataclass_field.type)
        if value is None:
            if optional:
                return None
            raise cls.error_type(f"{field_name} is required")

        return cls.validate_annotation(annotation, value, field_name, metadata)

    @classmethod
    def build_kwargs(
        cls,
        model_type: type[DataClassModelType],
        values: Mapping[str, Any],
        *,
        normalize_keys: bool = False,
    ) -> Dict[str, Any]:
        normalized = cls.normalize_kwargs(values) if normalize_keys else dict(values)
        model_fields = cls.dataclass_fields(model_type)
        allowed_fields = {dataclass_field.name for dataclass_field in model_fields}
        unknown_fields = sorted(set(normalized) - allowed_fields)
        if unknown_fields:
            raise cls.error_type(cls.unknown_fields_error(model_type, unknown_fields))

        kwargs: Dict[str, Any] = {}
        for dataclass_field in model_fields:
            if dataclass_field.name in normalized:
                raw_value = normalized[dataclass_field.name]
            else:
                raw_value = cls.default_value(dataclass_field, model_type)
            kwargs[dataclass_field.name] = cls.validate_field(
                dataclass_field,
                raw_value,
                dataclass_field.name,
            )
        return kwargs

    @classmethod
    def validate_instance(cls, instance: Any) -> None:
        for dataclass_field in cls.dataclass_fields(instance):
            value = getattr(instance, dataclass_field.name)
            validated = cls.validate_field(dataclass_field, value, dataclass_field.name)
            setattr(instance, dataclass_field.name, validated)

    @classmethod
    def from_value(
        cls: type[DataClassModelType], value: Any, field_name: str = "config"
    ) -> DataClassModelType:
        if isinstance(value, cls):
            init_kwargs = {
                dataclass_field.name: getattr(value, dataclass_field.name)
                for dataclass_field in cls.dataclass_fields(cls)
            }
            return cls(**init_kwargs)
        mapping = cls.ensure_mapping(value, field_name)
        return cls(**cls.build_kwargs(cls, mapping))

    def _serialize_value(self, value: Any, *, exclude_none: bool) -> Any:
        if isinstance(value, DataClassValidator):
            return value.to_dict(exclude_none=exclude_none)
        if isinstance(value, list):
            return [
                self._serialize_value(item, exclude_none=exclude_none) for item in value
            ]
        if isinstance(value, dict):
            return {
                self._serialize_value(
                    key, exclude_none=exclude_none
                ): self._serialize_value(item, exclude_none=exclude_none)
                for key, item in value.items()
            }
        return value

    def to_dict(
        self,
        *,
        include: Optional[set[str]] = None,
        exclude_none: bool = False,
    ) -> Dict[str, Any]:
        data: Dict[str, Any] = {}
        for dataclass_field in self.dataclass_fields(self):
            if include is not None and dataclass_field.name not in include:
                continue
            value = getattr(self, dataclass_field.name)
            if exclude_none and value is None:
                continue
            alias = dataclass_field.metadata.get("alias", dataclass_field.name)
            data[alias] = self._serialize_value(value, exclude_none=exclude_none)
        return data
