import re
from enum import Enum
from typing import Any, Dict, Sequence

from pydantic import BaseModel, Field, validator

# OpenAPI names validation regexp
OpenAPI_NAME_RE = re.compile(r"^[A-Za-z0-9-._]+")


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


class SecureType(str, Enum):
    HTTP = "http"
    API_KEY = "apiKey"
    OAUTH_TWO = "oauth2"
    OPEN_ID_CONNECT = "openIdConnect"


class SecuritySchemeData(BaseModel):
    """
    Security scheme data
    """

    type: SecureType = Field(..., description="Secure scheme type")
    name: str = None
    field_in: str = Field(None, alias="in")
    scheme: str = None
    openIdConnectUrl: str = None
    flows: dict = None

    class Config:
        validate_assignment = True


class SecurityScheme(BaseModel):
    """
    Named security scheme
    """

    name: str = Field(
        ...,
        description="Custom security scheme name. Can only contain - [A-Za-z0-9-._]",
    )
    data: SecuritySchemeData = Field(..., description="Security scheme data")

    @validator("name")
    def check_db_name(cls, value: str):
        if not OpenAPI_NAME_RE.fullmatch(value):
            raise ValueError("Name not match OpenAPI rules")
        return value

    class Config:
        validate_assignment = True
