import importlib.util

from spectree import SpecTree
from spectree.model_adapter import get_msgspec_model_adapter

assert importlib.util.find_spec("msgspec") is not None
assert importlib.util.find_spec("pydantic") is None

SpecTree("falcon", model_adapter=get_msgspec_model_adapter())
print("=> passed msgspec plugin import test")
