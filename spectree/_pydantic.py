from enum import Enum
from typing import Any, Protocol, Type, runtime_checkable

from pydantic.version import VERSION as PYDANTIC_VERSION

PYDANTIC2 = PYDANTIC_VERSION.startswith("2")
ROOT_FIELD = "__root__"


__all__ = [
    "AnyUrl",
    "BaseModel",
    "Field",
    "InternalBaseModel",
    "InternalField",
    "InternalValidationError",
    "ValidationError",
    "generate_root_model",
    "is_base_model",
    "is_base_model_instance",
    "is_pydantic_model",
    "is_root_model",
    "is_root_model_instance",
    "root_validator",
    "serialize_model_instance",
    "validator",
]


class UNSET_TYPE(Enum):
    NODEFAULT = "NO_DEFAULT"


NODEFAULT = UNSET_TYPE.NODEFAULT

if PYDANTIC2:
    from pydantic import BaseModel, Field, RootModel, ValidationError
    from pydantic.v1 import AnyUrl, root_validator, validator
    from pydantic.v1 import BaseModel as InternalBaseModel
    from pydantic.v1 import Field as InternalField
    from pydantic.v1 import ValidationError as InternalValidationError
    from pydantic_core import core_schema  # noqa

else:
    from pydantic import (  # type: ignore[no-redef,assignment]
        AnyUrl,
        BaseModel,
        Field,
        ValidationError,
        root_validator,
        validator,
    )

    InternalBaseModel = BaseModel  # type: ignore
    InternalValidationError = ValidationError  # type: ignore
    InternalField = Field  # type: ignore


def generate_root_model(root_type, name="GeneratedRootModel") -> Type:
    if PYDANTIC2:
        return type(name, (RootModel[root_type],), {})
    return type(
        name,
        (BaseModel,),
        {
            "__annotations__": {ROOT_FIELD: root_type},
        },
    )


@runtime_checkable
class PydanticModelProtocol(Protocol):
    def dict(
        self,
        *,
        include=None,
        exclude=None,
        by_alias=False,
        skip_defaults=None,
        exclude_unset=False,
        exclude_defaults=False,
        exclude_none=False,
    ):
        pass

    def json(
        self,
        *,
        include=None,
        exclude=None,
        by_alias=False,
        skip_defaults=None,
        exclude_unset=False,
        exclude_defaults=False,
        exclude_none=False,
        encoder=None,
        models_as_dict=True,
        **dumps_kwargs,
    ):
        pass

    @classmethod
    def parse_obj(cls, obj):
        pass

    @classmethod
    def parse_raw(
        cls, b, *, content_type=None, encoding="utf8", proto=None, allow_pickle=False
    ):
        pass

    @classmethod
    def parse_file(
        cls, path, *, content_type=None, encoding="utf8", proto=None, allow_pickle=False
    ):
        pass

    @classmethod
    def construct(cls, _fields_set=None, **values):
        pass

    @classmethod
    def copy(cls, *, include=None, exclude=None, update=None, deep=False):
        pass

    @classmethod
    def schema(cls, by_alias=True, ref_template="#/definitions/{model}"):
        pass

    @classmethod
    def schema_json(
        cls, *, by_alias=True, ref_template="#/definitions/{model}", **dumps_kwargs
    ):
        pass

    @classmethod
    def validate(cls, value):
        pass


def is_pydantic_model(t: Any) -> bool:
    return issubclass(t, PydanticModelProtocol)


def is_base_model(t: Any) -> bool:
    """Check whether a type is a Pydantic BaseModel"""
    try:
        return is_pydantic_model(t)
    except TypeError:
        return False


def is_base_model_instance(value: Any) -> bool:
    """Check whether a value is a Pydantic BaseModel instance."""
    return is_base_model(type(value))


def is_partial_base_model_instance(instance: Any) -> bool:
    """Check if it's a Pydantic BaseModel instance or [BaseModel]
    or {key: BaseModel} instance.
    """
    if not instance:
        return False
    if is_base_model_instance(instance):
        return True
    if isinstance(instance, dict):
        return any(
            is_partial_base_model_instance(key) or is_partial_base_model_instance(value)
            for key, value in instance.items()
        )
    if isinstance(instance, (list, tuple)):
        return any(is_partial_base_model_instance(value) for value in instance)
    return False


def is_root_model(t: Any) -> bool:
    """Check whether a type is a Pydantic RootModel."""
    pydantic_v1_root = is_base_model(t) and ROOT_FIELD in t.__fields__
    pydantic_v2_root = is_base_model(t) and any(
        f"{m.__module__}.{m.__name__}" == "pydantic.root_model.RootModel"
        for m in t.mro()
    )
    return pydantic_v1_root or pydantic_v2_root


def is_root_model_instance(value: Any):
    """Check whether a value is a Pydantic RootModel instance."""
    return is_root_model(type(value))


def serialize_model_instance(value: BaseModel):
    """Serialize a Pydantic BaseModel (equivalent of calling `.dict()` on a BaseModel,
    but additionally takes care of stripping __root__ for root models.
    """
    serialized = value.model_dump() if PYDANTIC2 else value.dict()

    if is_root_model_instance(value) and ROOT_FIELD in serialized:
        return serialized[ROOT_FIELD]
    return serialized
