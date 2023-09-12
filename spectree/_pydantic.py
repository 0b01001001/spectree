from typing import Any, Optional, Type

from pydantic.version import VERSION as PYDANTIC_VERSION

PYDANTIC2 = PYDANTIC_VERSION.startswith("2")

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


def is_root_model(value: Optional[Type[Any]]):
    return value and issubclass(value, BaseModel) and "__root__" in value.__fields__
