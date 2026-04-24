import warnings
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional, Union

from spectree.dataclass_model import AdapterBackedDataclass
from spectree.models import SecurityScheme, Server
from spectree.page import PAGE_TEMPLATES


class ModeEnum(str, Enum):
    """the mode of the SpecTree validator"""

    #: includes undecorated routes and routes decorated by this instance
    normal = "normal"
    #: only includes routes decorated by this instance
    strict = "strict"
    #: includes all the routes
    greedy = "greedy"


SecurityValue = Union[dict[str, list[str]], list[dict[str, list[str]]]]


@dataclass
class Contact(AdapterBackedDataclass):
    """contact information"""

    #: name of the contact
    name: str
    #: contact url
    url: Optional[str] = field(default=None, metadata={"format": "url"})
    #: contact email address
    email: Optional[str] = None


@dataclass
class License(AdapterBackedDataclass):
    """license information"""

    #: name of the license
    name: str
    #: license url
    url: Optional[str] = field(default=None, metadata={"format": "url"})


@dataclass
class Configuration(AdapterBackedDataclass):
    """Global configuration."""

    # OpenAPI configurations
    #: title of the service
    title: str = "Service API Document"
    #: service OpenAPI document description
    description: Optional[str] = None
    #: service version
    version: str = "0.1.0"
    #: terms of service url
    terms_of_service: Optional[str] = field(default=None, metadata={"format": "url"})
    #: author contact information
    contact: Optional[Contact] = None
    #: license information
    license: Optional[License] = None

    # SpecTree configurations
    #: OpenAPI doc route path prefix (i.e. /apidoc/)
    path: str = "apidoc"
    #: OpenAPI file route path suffix (i.e. /apidoc/openapi.json)
    filename: str = "openapi.json"
    #: OpenAPI version (doesn't affect anything)
    openapi_version: str = "3.1.0"
    #: the mode of the SpecTree validator :class:`ModeEnum`
    mode: ModeEnum = ModeEnum.normal
    #: A dictionary of documentation page templates. The key is the
    #: name of the template, that is also used in the URL path, while the value is used
    #: to render the documentation page content. (Each page template should contain a
    #: `{spec_url}` placeholder, that'll be replaced by the actual OpenAPI spec URL in
    #: the rendered documentation page
    page_templates: dict[str, str] = field(default_factory=lambda: dict(PAGE_TEMPLATES))
    #: opt-in type annotation feature, see the README examples
    annotations: bool = True
    #: servers section of OAS :py:class:`spectree.models.Server`
    servers: list[Server] = field(default_factory=list)
    #: OpenAPI `securitySchemes` :py:class:`spectree.models.SecurityScheme`
    security_schemes: Optional[list[SecurityScheme]] = None
    #: OpenAPI `security` JSON at the global level
    security: SecurityValue = field(default_factory=dict)
    # Swagger OAuth2 configs
    #: OAuth2 client id
    client_id: str = ""
    #: OAuth2 client secret
    client_secret: str = ""
    #: OAuth2 realm
    realm: str = ""
    #: OAuth2 app name
    app_name: str = "spectree_app"
    #: OAuth2 scope separator
    scope_separator: str = " "
    #: OAuth2 scopes
    scopes: list[str] = field(default_factory=list)
    #: OAuth2 additional query string params
    additional_query_string_params: dict[str, str] = field(default_factory=dict)
    #: OAuth2 use basic authentication with access code grant
    use_basic_authentication_with_access_code_grant: bool = False
    #: OAuth2 use PKCE with authorization code grant
    use_pkce_with_authorization_code_grant: bool = False

    @property
    def spec_url(self) -> str:
        return f"/{self.path}/{self.filename}"

    def swagger_oauth2_config(self) -> dict[str, Any]:
        """
        return the swagger UI OAuth2 configs

        ref: https://swagger.io/docs/open-source-tools/swagger-ui/usage/oauth2/
        """
        if self.client_secret:
            warnings.warn(
                "Do not use client_secret in production", UserWarning, stacklevel=1
            )

        return self.to_dict(
            include=(
                "client_id",
                "client_secret",
                "realm",
                "app_name",
                "scope_separator",
                "scopes",
                "additional_query_string_params",
                "use_basic_authentication_with_access_code_grant",
                "use_pkce_with_authorization_code_grant",
            )
        ) | {
            "use_basic_authentication_with_access_code_grant": (
                "true"
                if self.use_basic_authentication_with_access_code_grant
                else "false"
            ),
            "use_pkce_with_authorization_code_grant": (
                "true" if self.use_pkce_with_authorization_code_grant else "false"
            ),
        }

    def openapi_info(self) -> dict[str, Any]:
        info = self.to_dict(
            include=(
                "title",
                "description",
                "version",
                "terms_of_service",
                "contact",
                "license",
            ),
            exclude_none=True,
        )
        info["termsOfService"] = info.pop("terms_of_service")
        return info
