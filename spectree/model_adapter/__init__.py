from functools import cache
from importlib import import_module

from spectree._types import ModelAdapterType
from spectree.model_adapter.protocol import ModelAdapter, ModelClass

__all__ = [
    "ModelAdapter",
    "ModelClass",
    "get_msgspec_model_adapter",
    "get_pydantic_model_adapter",
]


@cache
def get_pydantic_model_adapter() -> ModelAdapterType:
    module = import_module("spectree.model_adapter.pydantic_adapter")
    return module.PydanticModelAdapter()


@cache
def get_msgspec_model_adapter() -> ModelAdapterType:
    module = import_module("spectree.model_adapter.msgspec_adapter")
    return module.MsgspecModelAdapter()
