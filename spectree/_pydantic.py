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
