from typing import Any

from pydantic.version import VERSION as PYDANTIC_VERSION

PYDANTIC2 = PYDANTIC_VERSION.startswith("2")
ROOT_FIELD = "__root__"


__all__ = [
    "BaseModel",
    "ValidationError",
    "Field",
    "root_validator",
    "AnyUrl",
    "BaseSettings",
    "EmailStr",
    "validator",
    "is_root_model",
    "is_root_model_instance",
    "serialize_model_instance",
    "is_base_model",
    "is_base_model_instance",
]

if PYDANTIC2:
    from pydantic.v1 import (
        AnyUrl,
        BaseModel,
        BaseSettings,
        EmailStr,
        Field,
        ValidationError,
        root_validator,
        validator,
    )
else:
    from pydantic import (  # type: ignore[no-redef,assignment]
        AnyUrl,
        BaseModel,
        BaseSettings,
        EmailStr,
        Field,
        ValidationError,
        root_validator,
        validator,
    )


def is_base_model(t: Any) -> bool:
    """Check whether a type is a Pydantic BaseModel"""
    try:
        return issubclass(t, BaseModel)
    except TypeError:
        return False


def is_base_model_instance(value: Any) -> bool:
    """Check whether a value is a Pydantic BaseModel instance."""
    return is_base_model(type(value))


def is_root_model(t: Any) -> bool:
    """Check whether a type is a Pydantic RootModel."""
    return is_base_model(t) and ROOT_FIELD in t.__fields__


def is_root_model_instance(value: Any):
    """Check whether a value is a Pydantic RootModel instance."""
    return is_root_model(type(value))


def serialize_model_instance(value: BaseModel):
    """Serialize a Pydantic BaseModel (equivalent of calling `.dict()` on a BaseModel,
    but additionally takes care of stripping __root__ for root models.
    """
    serialized = value.dict()
    if is_root_model_instance(value) and ROOT_FIELD in serialized:
        return serialized[ROOT_FIELD]
    return serialized
