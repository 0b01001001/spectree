"""Default api models definitions."""

from typing import Sequence, Dict, Any, Optional

from pydantic import Field
from pydantic.main import BaseModel


class UnprocessableEntityElement(BaseModel):
    """Model of missing field description."""
    loc: Sequence[str] = Field(
        ...,
        title='Missing field name',
    )
    msg: str = Field(
        ...,
        title='Error message',
    )
    type: str = Field(  # noqa: WPS125
        ...,
        title='Message type',
    )
    ctx: Optional[Dict[str, Any]] = Field(
        ...,
        title='Error context',
    )


class UnprocessableEntity(BaseModel):
    """Model of 422 Unprocessable Entity error."""

    __root__: Sequence[UnprocessableEntityElement]
