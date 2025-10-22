from dataclasses import dataclass
from typing import Any, Union, cast

from pydantic import BaseModel, RootModel

__all__ = [
    "BaseModel",
    "generate_root_model",
    "is_base_model",
    "is_base_model_instance",
    "is_pydantic_model",
    "is_root_model",
    "is_root_model_instance",
    "serialize_model_instance",
]


def generate_root_model(root_type, name="GeneratedRootModel") -> type[BaseModel]:
    return type(name, (RootModel[root_type],), {})


def is_pydantic_model(t: Any) -> bool:
    return issubclass(t, BaseModel)


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
    pydantic_v2_root = is_base_model(t) and any(
        f"{m.__module__}.{m.__name__}" == "pydantic.root_model.RootModel"
        for m in t.mro()
    )
    return pydantic_v2_root


def is_root_model_instance(value: Any):
    """Check whether a value is a Pydantic RootModel instance."""
    return is_root_model(type(value))


@dataclass(frozen=True)
class SerializedPydanticResponse:
    data: bytes


_PydanticResponseModel = generate_root_model(Any, name="_PydanticResponseModel")


def serialize_model_instance(
    value: Union[BaseModel, list[BaseModel], dict[Any, BaseModel]],
) -> SerializedPydanticResponse:
    """Serialize a (partial) Pydantic BaseModel to json string."""
    if not is_base_model_instance(value):
        value = _PydanticResponseModel.model_validate(value)
    else:
        value = cast(BaseModel, value)
    serialized = value.model_dump_json()
    return SerializedPydanticResponse(serialized.encode("utf-8"))
