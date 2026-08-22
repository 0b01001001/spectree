from functools import cache
from importlib import import_module

from spectree._types import ModelAdapterType
from spectree.model_adapter.protocol import ModelAdapter, ModelSpec


@cache
def get_pydantic_model_adapter() -> ModelAdapterType:
    module = import_module("spectree.model_adapter.pydantic_adapter")
    return module.PydanticModelAdapter()


@cache
def get_msgspec_model_adapter() -> ModelAdapterType:
    module = import_module("spectree.model_adapter.msgspec_adapter")
    return module.MsgspecModelAdapter()


__all__ = [
    "ModelAdapter",
    "ModelSpec",
    "get_msgspec_model_adapter",
    "get_pydantic_model_adapter",
]
