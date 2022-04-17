import re
from enum import Enum
from typing import Any, Dict, Optional, Sequence

from pydantic import BaseModel, Field, root_validator, validator

# OpenAPI names validation regexp
OpenAPI_NAME_RE = re.compile(r"^[A-Za-z0-9-._]+")


class ExternalDocs(BaseModel):
    description: str = ""
    url: str


class Tag(BaseModel):
    """OpenAPI tag object"""

    name: str
    description: str = ""
    externalDocs: Optional[ExternalDocs] = None

    def __str__(self):
        return self.name


class ValidationErrorElement(BaseModel):
    """Model of a validation error response element."""

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


class ValidationError(BaseModel):
    """Model of a validation error response."""

    __root__: Sequence[ValidationErrorElement]


class SecureType(str, Enum):
    HTTP = "http"
    API_KEY = "apiKey"
    OAUTH_TWO = "oauth2"
    OPEN_ID_CONNECT = "openIdConnect"


class InType(str, Enum):
    HEADER = "header"
    QUERY = "query"
    COOKIE = "cookie"


type_req_fields: Dict[SecureType, Sequence[str]] = {
    SecureType.HTTP: ["scheme"],
    SecureType.API_KEY: ["name", "field_in"],
    SecureType.OAUTH_TWO: ["flows"],
    SecureType.OPEN_ID_CONNECT: ["openIdConnectUrl"],
}


class SecuritySchemeData(BaseModel):
    """
    Security scheme data
    https://github.com/OAI/OpenAPI-Specification/blob/main/versions/3.0.3.md#securitySchemeObject
    """

    type: SecureType = Field(..., description="Secure scheme type")
    description: str = Field(
        None,
        description="A short description for security scheme.",
    )
    name: str = Field(
        None,
        description="The name of the header, query or cookie parameter to be used.",
    )
    field_in: InType = Field(
        None, alias="in", description="The location of the API key."
    )
    scheme: str = Field(None, description="The name of the HTTP Authorization scheme.")
    bearerFormat: str = Field(
        None,
        description=(
            "A hint to the client to identify how the bearer token is formatted."
        ),
    )
    flows: dict = Field(
        None,
        description=(
            "Containing configuration information for the flow types supported."
        ),
    )
    openIdConnectUrl: str = Field(
        None, description="OpenId Connect URL to discover OAuth2 configuration values."
    )

    @root_validator()
    def check_type_required_fields(cls, values: dict):
        exist_fields = {key for key in values.keys() if values[key]}
        if not values.get("type"):
            raise ValueError("Type field is required")

        if not set(type_req_fields[values["type"]]).issubset(exist_fields):
            raise ValueError(
                f"For `{values['type']}` type "
                f"`{', '.join(type_req_fields[values['type']])}` field(s) is required."
            )
        return values

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
    def check_name(cls, value: str):
        if not OpenAPI_NAME_RE.fullmatch(value):
            raise ValueError("Name not match OpenAPI rules")
        return value

    class Config:
        validate_assignment = True


class Server(BaseModel):
    """
    Servers section of OAS
    """

    url: str = Field(
        ...,
        description="""URL or path of API server

        (may be parametrized with using \"variables\" section - for more information,
        see: https://swagger.io/docs/specification/api-host-and-base-path/ )""",
    )
    description: str = Field(
        None,
        description="Custom server description for server URL",
    )
    variables: dict = Field(
        None,
        description="Variables for customizing server URL",
    )

    class Config:
        validate_assignment = True
