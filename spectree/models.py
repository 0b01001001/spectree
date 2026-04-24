import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Mapping, Optional, Set

from spectree.dataclass_model import AdapterBackedDataclass
from spectree.errors import SpecTreeValidationError

# OpenAPI names validation regexp
OpenAPI_NAME_RE = re.compile(r"^[A-Za-z0-9-._]+")

_EMPTY_FIELDS: set[str] = set()


@dataclass
class ExternalDocs(AdapterBackedDataclass):
    url: str = field(metadata={"format": "url"})
    description: str = ""


@dataclass
class Tag(AdapterBackedDataclass):
    """OpenAPI tag object."""

    name: str
    description: str = ""
    externalDocs: Optional[ExternalDocs] = None

    def __str__(self) -> str:
        return self.name


@dataclass
class ValidationErrorElement(AdapterBackedDataclass):
    """Model of a validation error response element."""

    loc: list[str] = field(metadata={"title": "Missing field name"})
    msg: str = field(metadata={"title": "Error message"})
    type: str = field(metadata={"title": "Error type"})
    ctx: Optional[Dict[str, Any]] = field(
        default=None,
        metadata={"title": "Error context"},
    )


class SecureType(str, Enum):
    HTTP = "http"
    API_KEY = "apiKey"
    OAUTH_TWO = "oauth2"
    OPEN_ID_CONNECT = "openIdConnect"


class InType(str, Enum):
    HEADER = "header"
    QUERY = "query"
    COOKIE = "cookie"


SECURE_TYPE_REQUIRED_FIELDS: Dict[SecureType, Set[str]] = {
    SecureType.HTTP: {"scheme"},
    SecureType.API_KEY: {"name", "field_in"},
    SecureType.OAUTH_TWO: {"flows"},
    SecureType.OPEN_ID_CONNECT: {"openIdConnectUrl"},
}


@dataclass
class SecuritySchemeData(AdapterBackedDataclass):
    """
    Security scheme data
    https://github.com/OAI/OpenAPI-Specification/blob/main/versions/3.0.3.md#securitySchemeObject
    """

    type: SecureType = field(
        metadata={"description": "Secure scheme type"},
    )
    description: Optional[str] = field(
        default=None,
        metadata={"description": "A short description for security scheme."},
    )
    name: Optional[str] = field(
        default=None,
        metadata={
            "description": "The name of the header, query or cookie parameter to be used."
        },
    )
    field_in: Optional[InType] = field(
        default=None,
        metadata={"description": "The location of the API key.", "rename": "in"},
    )
    scheme: Optional[str] = field(
        default=None,
        metadata={"description": "The name of the HTTP Authorization scheme."},
    )
    bearerFormat: Optional[str] = field(
        default=None,
        metadata={
            "description": (
                "A hint to the client to identify how the bearer token is formatted."
            )
        },
    )
    flows: Optional[Dict[str, Any]] = field(
        default=None,
        metadata={
            "description": "Containing configuration information for the flow types supported."
        },
    )
    openIdConnectUrl: Optional[str] = field(
        default=None,
        metadata={
            "description": "OpenId Connect URL to discover OAuth2 configuration values."
        },
    )

    def __post_init__(self) -> None:
        super().__post_init__()
        if self.type is None:
            raise SpecTreeValidationError("Type field is required")

        exist_fields = {
            field_name
            for field_name in (
                "name",
                "field_in",
                "scheme",
                "flows",
                "openIdConnectUrl",
            )
            if getattr(self, field_name)
        }
        required_fields = SECURE_TYPE_REQUIRED_FIELDS.get(self.type, _EMPTY_FIELDS)
        if not required_fields.issubset(exist_fields):
            raise SpecTreeValidationError(
                f"`{self.type.value}` type requires "
                f"`{', '.join(required_fields)}` field(s)"
                f"But only found `{', '.join(sorted(exist_fields))}`."
            )


@dataclass
class SecurityScheme(AdapterBackedDataclass):
    """
    Named security scheme
    """

    name: str = field(
        metadata={
            "description": "Custom security scheme name. Can only contain - [A-Za-z0-9-._]"
        }
    )
    data: SecuritySchemeData = field(metadata={"description": "Security scheme data"})

    @classmethod
    def __pre_init__(cls, kwargs: dict[str, Any]) -> dict[str, Any]:
        kwargs = super().__pre_init__(kwargs)
        if isinstance(kwargs.get("data"), Mapping):
            kwargs["data"] = SecuritySchemeData.__pre_init__(kwargs["data"])
        return kwargs

    def __post_init__(self) -> None:
        super().__post_init__()
        if not OpenAPI_NAME_RE.fullmatch(self.name):
            raise SpecTreeValidationError("Name does not match OpenAPI naming rules")


@dataclass
class Server(AdapterBackedDataclass):
    """
    Servers section of OAS
    """

    url: str = field(
        metadata={
            "description": (
                "URL or path of API server\n\n"
                '(may be parametrized with using "variables" section - for more '
                "information, see: "
                "https://swagger.io/docs/specification/api-host-and-base-path/ )"
            )
        }
    )
    description: Optional[str] = field(
        default=None,
        metadata={"description": "Custom server description for server URL"},
    )
    variables: Optional[Dict[str, Any]] = field(
        default=None,
        metadata={"description": "Variables for customizing server URL"},
    )
