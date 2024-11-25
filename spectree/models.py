import re
from enum import Enum
from typing import Any, Dict, Optional, Sequence, Set

from ._pydantic import (
    PYDANTIC2,
    InternalBaseModel,
    InternalField,
    root_validator,
    validator,
)

# OpenAPI names validation regexp
OpenAPI_NAME_RE = re.compile(r"^[A-Za-z0-9-._]+")


class ExternalDocs(InternalBaseModel):
    description: str = ""
    url: str


class Tag(InternalBaseModel):
    """OpenAPI tag object"""

    name: str
    description: str = ""
    externalDocs: Optional[ExternalDocs] = None

    def __str__(self):
        return self.name


class ValidationErrorElement(InternalBaseModel):
    """Model of a validation error response element."""

    loc: Sequence[str] = InternalField(
        ...,
        title="Missing field name",
    )
    msg: str = InternalField(
        ...,
        title="Error message",
    )
    type: str = InternalField(
        ...,
        title="Error type",
    )
    ctx: Optional[Dict[str, Any]] = InternalField(
        None,
        title="Error context",
    )


class ValidationError(InternalBaseModel):
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


type_req_fields: Dict[SecureType, Set[str]] = {
    SecureType.HTTP: {"scheme"},
    SecureType.API_KEY: {"name", "field_in"},
    SecureType.OAUTH_TWO: {"flows"},
    SecureType.OPEN_ID_CONNECT: {"openIdConnectUrl"},
}


class SecuritySchemeData(InternalBaseModel):
    """
    Security scheme data
    https://github.com/OAI/OpenAPI-Specification/blob/main/versions/3.0.3.md#securitySchemeObject
    """

    type: SecureType = InternalField(..., description="Secure scheme type")
    description: Optional[str] = InternalField(
        None,
        description="A short description for security scheme.",
    )
    name: Optional[str] = InternalField(
        None,
        description="The name of the header, query or cookie parameter to be used.",
    )
    field_in: Optional[InType] = InternalField(
        None, alias="in", description="The location of the API key."
    )
    scheme: Optional[str] = InternalField(
        None, description="The name of the HTTP Authorization scheme."
    )
    bearerFormat: Optional[str] = InternalField(
        None,
        description=(
            "A hint to the client to identify how the bearer token is formatted."
        ),
    )
    flows: Optional[dict] = InternalField(
        None,
        description=(
            "Containing configuration information for the flow types supported."
        ),
    )
    openIdConnectUrl: Optional[str] = InternalField(
        None, description="OpenId Connect URL to discover OAuth2 configuration values."
    )

    @root_validator
    def check_type_required_fields(cls, values: dict):
        exist_fields = {key for key in values if values[key]}
        if not values.get("type"):
            raise ValueError("Type field is required")

        if not type_req_fields[values["type"]].issubset(exist_fields):
            raise ValueError(
                f"For `{values['type']}` type "
                f"`{', '.join(type_req_fields[values['type']])}` field(s) is required. "
                f"But only found `{', '.join(exist_fields)}`."
            )
        return values

    class Config:
        validate_assignment = True
        allow_population_by_field_name = True


class SecurityScheme(InternalBaseModel):
    """
    Named security scheme
    """

    name: str = InternalField(
        ...,
        description="Custom security scheme name. Can only contain - [A-Za-z0-9-._]",
    )
    data: SecuritySchemeData = InternalField(..., description="Security scheme data")

    @validator("name")
    def check_name(cls, value: str):
        if not OpenAPI_NAME_RE.fullmatch(value):
            raise ValueError("Name not match OpenAPI rules")
        return value

    class Config:
        validate_assignment = True


class Server(InternalBaseModel):
    """
    Servers section of OAS
    """

    url: str = InternalField(
        ...,
        description="""URL or path of API server

        (may be parametrized with using \"variables\" section - for more information,
        see: https://swagger.io/docs/specification/api-host-and-base-path/ )""",
    )
    description: Optional[str] = InternalField(
        None,
        description="Custom server description for server URL",
    )
    variables: Optional[dict] = InternalField(
        None,
        description="Variables for customizing server URL",
    )

    class Config:
        validate_assignment = True


if PYDANTIC2:

    class BaseFile:
        """
        An uploaded file included as part of the request data.
        """

        @classmethod
        def __get_pydantic_json_schema__(cls, _core_schema: Dict[str, Any], _handler):
            return {"format": "binary", "type": "string"}

        @classmethod
        def __get_pydantic_core_schema__(cls, _source_type, _handler):
            from ._pydantic import core_schema

            return core_schema.with_info_plain_validator_function(cls.validate)

        @classmethod
        def validate(cls, value: Any, *_args, **_kwargs):
            return value
else:

    class BaseFile:  # type: ignore
        """
        An uploaded file included as part of the request data.
        """

        @classmethod
        def __get_validators__(cls):
            # one or more validators may be yielded which will be called in the
            # order to validate the input, each validator will receive as an input
            # the value returned from the previous validator
            yield cls.validate

        @classmethod
        def __modify_schema__(cls, field_schema: Dict[str, Any]) -> None:
            field_schema.update(format="binary", type="string")

        @classmethod
        def validate(cls, value: Any, values, config, field):
            # https://github.com/luolingchun/flask-openapi3/blob/master/flask_openapi3/models/file.py
            return value
