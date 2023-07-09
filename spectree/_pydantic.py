from __future__ import annotations

from typing import Any, Dict

from pydantic import AnyUrl, EmailStr, Field, ValidationError
from pydantic.version import VERSION as PYDANTIC_VERSION

PYDANTIC2 = PYDANTIC_VERSION.startswith("2")

__all__ = [
    "AnyUrl",
    "BaseModel",
    "BaseSettings",
    "ConfigDict",
    "CoreSchema",
    "EmailStr",
    "field_validator",
    "Field",
    "general_plain_validator_function",
    "JsonSchemaValue",
    "model_validator",
    "root_validator",
    "RootModel",
    "Url",
    "validate_email",
    "ValidationError",
    "ValidationInfo",
    "validator",
]


if PYDANTIC2:
    from pydantic import field_validator  # type: ignore[no-redef]
    from pydantic import model_validator  # type: ignore[no-redef]
    from pydantic import BaseModel, ConfigDict, RootModel, validate_email
    from pydantic.json_schema import JsonSchemaValue
    from pydantic_core import CoreSchema, Url
    from pydantic_core.core_schema import (
        ValidationInfo,
        general_plain_validator_function,
    )
    from pydantic_settings import BaseSettings

    PYDANTIC_SCHEMA_DEFS_KEY = "$defs"
    PYDANTIC_ROOT_ATTR = "root"

    def root_validator(pre: bool = False, allow_reuse: bool = False):
        # type: ignore[no-redef]
        pass

    def validator(*args):  # type: ignore[no-redef]
        pass

else:
    from pydantic import AnyUrl as Url
    from pydantic import BaseModel  # type: ignore[no-redef]
    from pydantic import BaseSettings  # type: ignore[no-redef,assignment]
    from pydantic import root_validator, validator  # type: ignore[assignment]

    _PydanticBaseModel = BaseModel
    _PydanticBaseSettings = BaseSettings

    PYDANTIC_SCHEMA_DEFS_KEY = "definitions"
    PYDANTIC_ROOT_ATTR = "__root__"

    class BaseSettings(_PydanticBaseSettings):  # type: ignore[no-redef]
        @classmethod
        def model_validate(cls, *args, **kwargs):
            return cls.parse_obj(*args, **kwargs)

        def model_dump(self, mode="json", *args, **kwargs):
            return self.dict(*args, **kwargs)

    class BaseModel(_PydanticBaseModel):  # type: ignore[no-redef]
        @classmethod
        def model_validate(cls, *args, **kwargs):
            return cls.parse_obj(*args, **kwargs)

        @classmethod
        def model_json_schema(cls, *args, **kwargs) -> Dict[str, Any]:
            return cls.schema(*args, **kwargs)

        def model_dump(self, mode: str = "json", **kwargs) -> Dict[str, Any]:
            return self.dict(**kwargs)

        def model_dump_json(self, **kwargs) -> str:
            return self.json(**kwargs)

    def field_validator() -> None:  # type: ignore[no-redef]
        pass

    def model_validator() -> None:  # type: ignore[no-redef]
        pass

    def validate_email(value: str) -> str:  # type: ignore[misc]
        return EmailStr.validate(value)

    def general_plain_validator_function():  # type: ignore[misc]
        return {}

    RootModel = BaseModel  # type: ignore[misc,assignment]
    JsonSchemaValue = Dict[str, Any]  # type: ignore[misc,assignment]
    CoreSchema = Any  # type: ignore[misc,assignment]
    ValidationInfo = Any  # type: ignore[misc,assignment]
