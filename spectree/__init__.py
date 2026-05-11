import logging

from spectree.model_adapter import get_msgspec_model_adapter, get_pydantic_model_adapter
from spectree.models import ExternalDocs, SecurityScheme, SecuritySchemeData, Tag
from spectree.response import Response
from spectree.spec import SpecTree

__all__ = [
    "ExternalDocs",
    "Response",
    "SecurityScheme",
    "SecuritySchemeData",
    "SpecTree",
    "Tag",
    "get_msgspec_model_adapter",
    "get_pydantic_model_adapter",
]

# setup library logging
logging.getLogger(__name__).addHandler(logging.NullHandler())
