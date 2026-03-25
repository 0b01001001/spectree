import warnings
from dataclasses import MISSING, dataclass, field, fields
from enum import Enum
from typing import (
    Any,
    Dict,
    List,
    Mapping,
    Optional,
    TypeVar,
    Union,
    get_args,
    get_origin,
)
from urllib.parse import urlsplit

from spectree.models import SecurityScheme, Server
from spectree.page import PAGE_TEMPLATES


class ConfigurationError(ValueError):
    """Configuration validation error."""


class ModeEnum(str, Enum):
    """the mode of the SpecTree validator"""

    #: includes undecorated routes and routes decorated by this instance
    normal = "normal"
    #: only includes routes decorated by this instance
    strict = "strict"
    #: includes all the routes
    greedy = "greedy"


SecurityValue = Union[Dict[str, List[str]], List[Dict[str, List[str]]]]
ConfigModelType = TypeVar("ConfigModelType", bound="ConfigModelBase")
_NONE_TYPE = type(None)


class ConfigValidator:
    @staticmethod
    def ensure_mapping(value: Any, field_name: str) -> Mapping[str, Any]:
        if not isinstance(value, Mapping):
            raise ConfigurationError(f"{field_name} must be a mapping")
        return value

    @staticmethod
    def ensure_str(value: Any, field_name: str) -> str:
        if not isinstance(value, str):
            raise ConfigurationError(f"{field_name} must be a string")
        return value

    @staticmethod
    def ensure_bool(value: Any, field_name: str) -> bool:
        if not isinstance(value, bool):
            raise ConfigurationError(f"{field_name} must be a boolean")
        return value

    @classmethod
    def ensure_str_list(cls, value: Any, field_name: str) -> List[str]:
        if not isinstance(value, list):
            raise ConfigurationError(f"{field_name} must be a list")
        return [cls.ensure_str(item, field_name) for item in value]

    @classmethod
    def ensure_str_mapping(cls, value: Any, field_name: str) -> Dict[str, str]:
        mapping = cls.ensure_mapping(value, field_name)
        return {
            cls.ensure_str(key, field_name): cls.ensure_str(item, field_name)
            for key, item in mapping.items()
        }

    @staticmethod
    def ensure_list_of_instances(
        value: Any, field_name: str, expected_type: type
    ) -> List[Any]:
        if not isinstance(value, list):
            raise ConfigurationError(f"{field_name} must be a list")
        if not all(isinstance(item, expected_type) for item in value):
            raise ConfigurationError(
                f"{field_name} items must be {expected_type.__name__} instances"
            )
        return list(value)

    @staticmethod
    def normalize_config_kwargs(values: Mapping[str, Any]) -> Dict[str, Any]:
        return {key.lower(): value for key, value in values.items()}

    @classmethod
    def validate_url(cls, value: Any, field_name: str) -> Optional[str]:
        if value is None:
            return None
        url = cls.ensure_str(value, field_name)
        parts = urlsplit(url)
        if not parts.scheme or not parts.netloc:
            raise ConfigurationError(f"{field_name} must be a valid absolute URL")
        return url

    @staticmethod
    def validate_enum(enum_type: type[Enum], value: Any, field_name: str) -> Enum:
        if isinstance(value, enum_type):
            return value
        if not isinstance(value, str):
            raise ConfigurationError(f"{field_name} must be a string")
        try:
            return enum_type(value)
        except ValueError as exc:
            allowed = ", ".join(item.value for item in enum_type)
            raise ConfigurationError(f"{field_name} must be one of: {allowed}") from exc

    @classmethod
    def validate_security_entry(
        cls, value: Any, field_name: str
    ) -> Dict[str, List[str]]:
        mapping = cls.ensure_mapping(value, field_name)
        normalized: Dict[str, List[str]] = {}
        for key, item in mapping.items():
            normalized[cls.ensure_str(key, field_name)] = cls.ensure_str_list(
                item, field_name
            )
        return normalized

    @classmethod
    def validate_security(cls, value: Any, field_name: str) -> SecurityValue:
        if isinstance(value, list):
            return [cls.validate_security_entry(item, field_name) for item in value]
        return cls.validate_security_entry(value, field_name)

    @staticmethod
    def default_value(dataclass_field: Any, model_type: type[ConfigModelType]) -> Any:
        if dataclass_field.default_factory is not MISSING:
            return dataclass_field.default_factory()
        if dataclass_field.default is not MISSING:
            return dataclass_field.default
        raise ConfigurationError(
            f"{model_type.__name__}.{dataclass_field.name} is required"
        )

    @staticmethod
    def unwrap_optional(annotation: Any) -> tuple[Any, bool]:
        origin = get_origin(annotation)
        if origin is Union:
            args = tuple(arg for arg in get_args(annotation) if arg is not _NONE_TYPE)
            if len(args) == 1 and len(args) != len(get_args(annotation)):
                return args[0], True
        return annotation, False

    @classmethod
    def validate_annotation(
        cls, annotation: Any, value: Any, field_name: str, metadata: Mapping[str, Any]
    ) -> Any:
        result: Any
        origin = get_origin(annotation)
        args = get_args(annotation)

        if metadata.get("format") == "url":
            result = cls.validate_url(value, field_name)
        elif annotation is str:
            result = cls.ensure_str(value, field_name)
        elif annotation is bool:
            result = cls.ensure_bool(value, field_name)
        elif isinstance(annotation, type) and issubclass(annotation, Enum):
            result = cls.validate_enum(annotation, value, field_name)
        elif isinstance(annotation, type) and issubclass(annotation, ConfigModelBase):
            result = annotation.from_value(value, field_name)
        elif origin is list and len(args) == 1 and args[0] is str:
            result = cls.ensure_str_list(value, field_name)
        elif origin is list and len(args) == 1 and isinstance(args[0], type):
            result = cls.ensure_list_of_instances(value, field_name, args[0])
        elif origin is dict and args == (str, str):
            result = cls.ensure_str_mapping(value, field_name)
        else:
            raise ConfigurationError(
                f"unsupported configuration field type for {field_name}: {annotation!r}"
            )

        return result

    @classmethod
    def validate_field(cls, dataclass_field: Any, value: Any, field_name: str) -> Any:
        metadata = dataclass_field.metadata
        validator = metadata.get("validator")
        if validator is not None:
            return getattr(cls, validator)(value, field_name)

        annotation, optional = cls.unwrap_optional(dataclass_field.type)
        if value is None:
            if optional:
                return None
            raise ConfigurationError(f"{field_name} is required")

        return cls.validate_annotation(annotation, value, field_name, metadata)

    @classmethod
    def build_kwargs(
        cls,
        model_type: type[ConfigModelType],
        values: Mapping[str, Any],
        *,
        normalize_keys: bool = False,
    ) -> Dict[str, Any]:
        normalized = (
            cls.normalize_config_kwargs(values) if normalize_keys else dict(values)
        )
        kwargs: Dict[str, Any] = {}
        for dataclass_field in fields(model_type):
            if dataclass_field.name in normalized:
                raw_value = normalized[dataclass_field.name]
            else:
                raw_value = cls.default_value(dataclass_field, model_type)
            kwargs[dataclass_field.name] = cls.validate_field(
                dataclass_field,
                raw_value,
                dataclass_field.name,
            )
        return kwargs

    @classmethod
    def validate_instance(cls, instance: "ConfigModelBase") -> None:
        for dataclass_field in fields(instance):
            value = getattr(instance, dataclass_field.name)
            validated = cls.validate_field(dataclass_field, value, dataclass_field.name)
            setattr(instance, dataclass_field.name, validated)


@dataclass
class ConfigModelBase:
    def __post_init__(self) -> None:
        ConfigValidator.validate_instance(self)

    @classmethod
    def from_value(
        cls: type[ConfigModelType], value: Any, field_name: str = "config"
    ) -> ConfigModelType:
        if isinstance(value, cls):
            init_kwargs = {
                dataclass_field.name: getattr(value, dataclass_field.name)
                for dataclass_field in fields(cls)
            }
            return cls(**init_kwargs)
        mapping = ConfigValidator.ensure_mapping(value, field_name)
        return cls(**ConfigValidator.build_kwargs(cls, mapping))

    def _serialize_value(self, value: Any, *, exclude_none: bool) -> Any:
        if isinstance(value, ConfigModelBase):
            return value.to_dict(exclude_none=exclude_none)
        if isinstance(value, list):
            return [
                self._serialize_value(item, exclude_none=exclude_none) for item in value
            ]
        if isinstance(value, dict):
            return {
                self._serialize_value(
                    key, exclude_none=exclude_none
                ): self._serialize_value(item, exclude_none=exclude_none)
                for key, item in value.items()
            }
        return value

    def to_dict(
        self,
        *,
        include: Optional[set[str]] = None,
        exclude_none: bool = False,
    ) -> Dict[str, Any]:
        data: Dict[str, Any] = {}
        for dataclass_field in fields(self):
            if include is not None and dataclass_field.name not in include:
                continue
            value = getattr(self, dataclass_field.name)
            if exclude_none and value is None:
                continue
            alias = dataclass_field.metadata.get("alias", dataclass_field.name)
            data[alias] = self._serialize_value(value, exclude_none=exclude_none)
        return data


@dataclass
class Contact(ConfigModelBase):
    """contact information"""

    #: name of the contact
    name: str
    #: contact url
    url: Optional[str] = field(default=None, metadata={"format": "url"})
    #: contact email address
    email: Optional[str] = None


@dataclass
class License(ConfigModelBase):
    """license information"""

    #: name of the license
    name: str
    #: license url
    url: Optional[str] = field(default=None, metadata={"format": "url"})


@dataclass(init=False)
class Configuration(ConfigModelBase):
    """Global configuration."""

    # OpenAPI configurations
    #: title of the service
    title: str = "Service API Document"
    #: service OpenAPI document description
    description: Optional[str] = None
    #: service version
    version: str = "0.1.0"
    #: terms of service url
    terms_of_service: Optional[str] = field(
        default=None,
        metadata={"alias": "termsOfService", "format": "url"},
    )
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
    page_templates: Dict[str, str] = field(default_factory=lambda: dict(PAGE_TEMPLATES))
    #: opt-in type annotation feature, see the README examples
    annotations: bool = True
    #: servers section of OAS :py:class:`spectree.models.Server`
    servers: List[Server] = field(default_factory=list)
    #: OpenAPI `securitySchemes` :py:class:`spectree.models.SecurityScheme`
    security_schemes: Optional[List[SecurityScheme]] = None
    #: OpenAPI `security` JSON at the global level
    security: SecurityValue = field(
        default_factory=dict,
        metadata={"validator": "validate_security"},
    )
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
    scopes: List[str] = field(default_factory=list)
    #: OAuth2 additional query string params
    additional_query_string_params: Dict[str, str] = field(default_factory=dict)
    #: OAuth2 use basic authentication with access code grant
    use_basic_authentication_with_access_code_grant: bool = False
    #: OAuth2 use PKCE with authorization code grant
    use_pkce_with_authorization_code_grant: bool = False

    def __setattr__(self, name: str, value: Any) -> None:
        dataclass_field = type(self).__dataclass_fields__.get(name)
        if dataclass_field is None:
            super().__setattr__(name, value)
            return

        validated = ConfigValidator.validate_field(dataclass_field, value, name)
        super().__setattr__(name, validated)

    def __init__(self, **kwargs: Any) -> None:
        validated = ConfigValidator.build_kwargs(
            type(self),
            kwargs,
            normalize_keys=True,
        )
        for name, value in validated.items():
            super().__setattr__(name, value)

    @classmethod
    def model_validate(cls, values: Mapping[str, Any]) -> "Configuration":
        return cls(**dict(ConfigValidator.ensure_mapping(values, "configuration")))

    @property
    def spec_url(self) -> str:
        return f"/{self.path}/{self.filename}"

    def swagger_oauth2_config(self) -> Dict[str, Any]:
        """
        return the swagger UI OAuth2 configs

        ref: https://swagger.io/docs/open-source-tools/swagger-ui/usage/oauth2/
        """
        if self.client_secret:
            warnings.warn(
                "Do not use client_secret in production", UserWarning, stacklevel=1
            )

        return self.to_dict(
            include={
                "client_id",
                "client_secret",
                "realm",
                "app_name",
                "scope_separator",
                "scopes",
                "additional_query_string_params",
                "use_basic_authentication_with_access_code_grant",
                "use_pkce_with_authorization_code_grant",
            }
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

    def openapi_info(self) -> Dict[str, Any]:
        return self.to_dict(
            include={
                "title",
                "description",
                "version",
                "terms_of_service",
                "contact",
                "license",
            },
            exclude_none=True,
        )
