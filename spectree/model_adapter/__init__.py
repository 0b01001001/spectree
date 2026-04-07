from functools import cache
from importlib import import_module

from .protocol import ModelAdapter, ModelClass

__all__ = [
    "ModelAdapter",
    "ModelClass",
    "get_default_model_adapter",
]


@cache
def get_default_model_adapter() -> ModelAdapter:
    module = import_module("spectree.model_adapter.pydantic")
    return module.PydanticModelAdapter()
