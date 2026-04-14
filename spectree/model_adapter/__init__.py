from functools import cache
from importlib import import_module
from typing import Any

from .protocol import ModelAdapter, ModelClass

__all__ = [
    "ModelAdapter",
    "ModelClass",
    "get_default_model_adapter",
    "get_pydantic_model_adapter",
]


@cache
def get_pydantic_model_adapter() -> ModelAdapter[Any, Exception]:
    module = import_module("spectree.model_adapter.pydantic_adapter")
    return module.PydanticModelAdapter()


@cache
def get_default_model_adapter() -> ModelAdapter[Any, Exception]:
    return get_pydantic_model_adapter()
