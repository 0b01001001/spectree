from spectree import SpecTree
from spectree.model_adapter import get_msgspec_model_adapter

SpecTree("falcon", model_adapter=get_msgspec_model_adapter())
print("=> passed msgspec plugin import test")
