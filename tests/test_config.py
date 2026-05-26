import pytest

from spectree import SecurityScheme, models
from spectree.config import Configuration
from spectree.errors import SpecTreeValidationError

SECURITY_SCHEMAS_DATA = [
    {
        "name": "auth_apiKey",
        "data": {"type": "apiKey", "name": "Authorization", "in": "header"},
    },
    {
        "name": "auth_apiKey_backup",
        "data": {"type": "apiKey", "name": "Authorization", "in": "header"},
    },
    {
        "name": "auth_BasicAuth",
        "data": {"type": "http", "scheme": "basic"},
    },
    {
        "name": "auth_BearerAuth",
        "data": {"type": "http", "scheme": "bearer"},
    },
    {
        "name": "auth_openID",
        "data": {
            "type": "openIdConnect",
            "openIdConnectUrl": "https://example.com/.well-known/openid-cfg",
        },
    },
    {
        "name": "auth_oauth2",
        "data": {
            "type": "oauth2",
            "flows": {
                "authorizationCode": {
                    "authorizationUrl": "https://example.com/oauth/authorize",
                    "tokenUrl": "https://example.com/oauth/token",
                    "scopes": {
                        "read": "Grants read access",
                        "write": "Grants write access",
                        "admin": "Grants access to admin operations",
                    },
                },
            },
        },
    },
]
WRONG_SECURITY_SCHEMAS_DATA = [
    {
        "name": "auth_apiKey_name",
        "data": {"type": "apiKey", "name": "Authorization"},
    },
    {
        "name": "auth_apiKey_in",
        "data": {"type": "apiKey", "in": "header"},
    },
    {
        "name": "auth_BasicAuth_scheme",
        "data": {"type": "http"},
    },
    {
        "name": "auth_openID_openIdConnectUrl",
        "data": {"type": "openIdConnect"},
    },
    {"name": "auth_oauth2_flows", "data": {"type": "oauth2"}},
    {"name": "empty_Data", "data": {}},
    {"name": "wrong_Data", "data": {"x": "y"}},
]


def validate_config(model_case, **kwargs):
    return Configuration.model_validate(kwargs, model_adapter=model_case.adapter)


def validate_security_scheme(model_case, **kwargs):
    return SecurityScheme.model_validate(kwargs, model_adapter=model_case.adapter)


def build_security_schemes(model_case):
    return [
        validate_security_scheme(model_case, **secure_item)
        for secure_item in SECURITY_SCHEMAS_DATA
    ]


def test_config_license(model_case):
    config = validate_config(model_case, license={"name": "MIT"})
    assert config.license is not None
    assert config.license.name == "MIT"

    config = validate_config(
        model_case,
        license={"name": "MIT", "url": "https://opensource.org/licenses/MIT"},
    )
    assert config.license is not None
    assert config.license.name == "MIT"
    assert str(config.license.url) == "https://opensource.org/licenses/MIT"

    with pytest.raises(SpecTreeValidationError):
        validate_config(model_case, license={"name": "MIT", "url": "url"})


def test_config_contact(model_case):
    config = validate_config(model_case, contact={"name": "John"})
    assert config.contact is not None
    assert config.contact.name == "John"

    config = validate_config(
        model_case,
        contact={"name": "John", "url": "https://example.com"},
    )
    assert config.contact is not None
    assert config.contact.name == "John"
    assert str(config.contact.url).rstrip("/") == "https://example.com"

    config = validate_config(
        model_case,
        contact={"name": "John", "email": "hello@github.com"},
    )
    assert config.contact is not None
    assert config.contact.name == "John"
    assert config.contact.email == "hello@github.com"

    with pytest.raises(SpecTreeValidationError):
        validate_config(model_case, contact={"name": "John", "url": "url"})


def test_config_kwargs_are_normalized_to_snake_case(model_case):
    config = validate_config(
        model_case,
        TITLE="Demo API",
        PATH="docs",
        termsOfService="https://example.com/camel-terms",
    )

    assert config.title == "Demo API"
    assert config.path == "docs"
    assert str(config.terms_of_service) == "https://example.com/camel-terms"


def test_openapi_info_serialization(model_case):
    config = validate_config(
        model_case,
        title="Demo API",
        description="Demo description",
        version="1.2.3",
        terms_of_service="https://example.com/terms",
        contact={"name": "John", "email": "hello@example.com"},
        license={"name": "MIT", "url": "https://opensource.org/licenses/MIT"},
    )

    assert config.openapi_info() == {
        "title": "Demo API",
        "description": "Demo description",
        "version": "1.2.3",
        "termsOfService": "https://example.com/terms",
        "contact": {
            "name": "John",
            "email": "hello@example.com",
        },
        "license": {
            "name": "MIT",
            "url": "https://opensource.org/licenses/MIT",
        },
    }


def test_swagger_oauth2_config_serialization(model_case):
    config = validate_config(
        model_case,
        client_id="client-id",
        client_secret="client-secret",
        scopes=["read", "write"],
        additional_query_string_params={"audience": "spectree"},
        use_basic_authentication_with_access_code_grant=True,
        use_pkce_with_authorization_code_grant=False,
    )

    oauth_config = config.swagger_oauth2_config()

    assert oauth_config["client_id"] == "client-id"
    assert oauth_config["client_secret"] == "client-secret"
    assert oauth_config["scopes"] == ["read", "write"]
    assert oauth_config["additional_query_string_params"] == {"audience": "spectree"}
    assert oauth_config["use_basic_authentication_with_access_code_grant"] == "true"
    assert oauth_config["use_pkce_with_authorization_code_grant"] == "false"


def test_config_mutable_defaults_are_isolated(model_case):
    config = validate_config(model_case)
    other = validate_config(model_case)

    config.scopes.append("read")
    config.additional_query_string_params["audience"] = "spectree"
    assert config.servers is not None
    config.servers.append(models.Server(url="https://github.com"))

    assert other.scopes == []
    assert other.additional_query_string_params == {}
    assert other.servers == []


@pytest.mark.parametrize("secure_item_data", SECURITY_SCHEMAS_DATA)
def test_update_security_scheme(model_case, secure_item_data):
    secure_item = validate_security_scheme(model_case, **secure_item_data)

    config = validate_config(model_case, security_schemes=[secure_item])

    assert config.security_schemes is not None
    assert config.security_schemes[0].name == secure_item.name
    assert config.security_schemes[0].data == secure_item.data


def test_update_security_schemes(model_case):
    security_schemes = build_security_schemes(model_case)

    config = validate_config(model_case, security_schemes=[*security_schemes])

    assert config.security_schemes == security_schemes


def test_config_parses_servers_from_mappings(model_case):
    config = validate_config(
        model_case,
        servers=[
            {"url": "https://example.com", "description": "primary"},
            {"url": "https://backup.example.com"},
        ],
    )

    assert config.servers == [
        models.Server(url="https://example.com", description="primary"),
        models.Server(url="https://backup.example.com"),
    ]


def test_config_parses_security_from_union_shapes(model_case):
    config = validate_config(model_case, security={"auth_apiKey": ["read"]})
    assert config.security == {"auth_apiKey": ["read"]}

    config = validate_config(model_case, security=[{"auth_apiKey": ["read"]}])
    assert config.security == [{"auth_apiKey": ["read"]}]


@pytest.mark.parametrize("secure_item_data", SECURITY_SCHEMAS_DATA)
def test_update_security_scheme_wrong_type(model_case, secure_item_data):
    secure_item = validate_security_scheme(model_case, **secure_item_data)

    with pytest.raises(SpecTreeValidationError):
        validate_security_scheme(
            model_case,
            name=secure_item.name,
            data={
                **secure_item.data.to_dict(exclude_none=True),
                "type": f"{secure_item.data.type.value}_wrong",
            },
        )


@pytest.mark.parametrize("secure_item", WRONG_SECURITY_SCHEMAS_DATA)
def test_update_security_scheme_wrong_data(model_case, secure_item):
    with pytest.raises(SpecTreeValidationError):
        validate_security_scheme(model_case, **secure_item)
