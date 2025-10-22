import re
from enum import Enum
from typing import Any, Dict, Optional, Sequence, Set

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    RootModel,
    field_validator,
    model_validator,
)
from pydantic_core import core_schema

# OpenAPI names validation regexp
OpenAPI_NAME_RE = re.compile(r"^[A-Za-z0-9-._]+")

_EMPTY_SET: set[None] = set()


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
    type: str = Field(
        ...,
        title="Error type",
    )
    ctx: Optional[Dict[str, Any]] = Field(
        None,
        title="Error context",
    )


class ValidationError(RootModel[Sequence[ValidationErrorElement]]):
    """Model of a validation error response."""


class SecureType(str, Enum):
    HTTP = "http"
    API_KEY = "apiKey"
    OAUTH_TWO = "oauth2"
    OPEN_ID_CONNECT = "openIdConnect"


class InType(str, Enum):
    HEADER = "header"
    QUERY = "query"
    COOKIE = "cookie"


type_req_fields: Dict[SecureType, Set[str]] = {
    SecureType.HTTP: {"scheme"},
    SecureType.API_KEY: {"name", "in"},
    SecureType.OAUTH_TWO: {"flows"},
    SecureType.OPEN_ID_CONNECT: {"openIdConnectUrl"},
}


class SecuritySchemeData(BaseModel):
    """
    Security scheme data
    https://github.com/OAI/OpenAPI-Specification/blob/main/versions/3.0.3.md#securitySchemeObject
    """

    type: SecureType = Field(..., description="Secure scheme type")
    description: Optional[str] = Field(
        None,
        description="A short description for security scheme.",
    )
    name: Optional[str] = Field(
        None,
        description="The name of the header, query or cookie parameter to be used.",
    )
    field_in: Optional[InType] = Field(
        None, alias="in", description="The location of the API key."
    )
    scheme: Optional[str] = Field(
        None, description="The name of the HTTP Authorization scheme."
    )
    bearerFormat: Optional[str] = Field(
        None,
        description=(
            "A hint to the client to identify how the bearer token is formatted."
        ),
    )
    flows: Optional[dict] = Field(
        None,
        description=(
            "Containing configuration information for the flow types supported."
        ),
    )
    openIdConnectUrl: Optional[str] = Field(
        None, description="OpenId Connect URL to discover OAuth2 configuration values."
    )

    @model_validator(mode="before")
    @classmethod
    def check_type_required_fields(cls, values: dict):
        exist_fields = {key for key in values if values[key]}
        if not values.get("type"):
            raise ValueError("Type field is required")

        if not type_req_fields.get(values["type"], _EMPTY_SET).issubset(exist_fields):
            raise ValueError(
                f"For `{values['type']}` type "
                f"`{', '.join(type_req_fields[values['type']])}` field(s) is required. "
                f"But only found `{', '.join(exist_fields)}`."
            )
        return values

    model_config = ConfigDict(
        validate_assignment=True,
        validate_by_alias=True,
        validate_by_name=True,
    )


class SecurityScheme(BaseModel):
    """
    Named security scheme
    """

    name: str = Field(
        ...,
        description="Custom security scheme name. Can only contain - [A-Za-z0-9-._]",
    )
    data: SecuritySchemeData = Field(..., description="Security scheme data")

    @field_validator("name")
    def check_name(cls, value: str):
        if not OpenAPI_NAME_RE.fullmatch(value):
            raise ValueError("Name does not match OpenAPI rules")
        return value

    model_config = ConfigDict(validate_assignment=True)


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
    description: Optional[str] = Field(
        None,
        description="Custom server description for server URL",
    )
    variables: Optional[dict] = Field(
        None,
        description="Variables for customizing server URL",
    )

    model_config = ConfigDict(validate_assignment=True)


class BaseFile:
    """
    An uploaded file, will be assigned as the corresponding web framework's
    file object.
    """

    @classmethod
    def __get_pydantic_json_schema__(cls, _core_schema: Dict[str, Any], _handler):
        return {"format": "binary", "type": "string"}

    @classmethod
    def __get_pydantic_core_schema__(cls, _source_type, _handler):
        return core_schema.with_info_plain_validator_function(cls.validate)

    @classmethod
    def validate(cls, value: Any, *_args, **_kwargs):
        return value
