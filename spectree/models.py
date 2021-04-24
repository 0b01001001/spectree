from typing import Any, Dict, Sequence

from pydantic import BaseModel, Field


class ExternalDocs(BaseModel):
    description: str = ""
    url: str


class Tag(BaseModel):
    """OpenAPI tag object"""

    name: str
    description: str = ""
    externalDocs: ExternalDocs = None

    def __str__(self):
        return self.name


class UnprocessableEntityElement(BaseModel):
    """Model of missing field description."""

    loc: Sequence[str] = Field(
        ...,
        title="Missing field name",
    )
    msg: str = Field(
        ...,
        title="Error message",
    )
    type: str = Field(  # noqa: WPS125
        ...,
        title="Error type",
    )
    ctx: Dict[str, Any] = Field(
        None,
        title="Error context",
    )


class UnprocessableEntity(BaseModel):
    """Model of 422 Unprocessable Entity error."""

    __root__: Sequence[UnprocessableEntityElement]
