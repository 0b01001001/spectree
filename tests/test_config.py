import pytest

from spectree import SecurityScheme, models
from spectree.config import Configuration, ConfigurationError
from spectree.models import ModelValidationError

from .common import ADAPTER, SECURITY_SCHEMAS, WRONG_SECURITY_SCHEMAS_DATA


def validate_config(**kwargs):
    return Configuration.model_validate(kwargs, model_adapter=ADAPTER)


def validate_security_scheme(**kwargs):
    return SecurityScheme.model_validate(kwargs, model_adapter=ADAPTER)


def dump_security_scheme(item: SecurityScheme):
    return {"name": item.name, "data": item.data.model_dump()}


def test_config_license():
    config = validate_config(license={"name": "MIT"})
    assert config.license is not None
    assert config.license.name == "MIT"

    config = validate_config(
        license={"name": "MIT", "url": "https://opensource.org/licenses/MIT"}
    )
    assert config.license is not None
    assert config.license.name == "MIT"
    assert str(config.license.url) == "https://opensource.org/licenses/MIT"

    with pytest.raises(ConfigurationError):
        validate_config(license={"name": "MIT", "url": "url"})


def test_config_contact():
    config = validate_config(contact={"name": "John"})
    assert config.contact is not None
    assert config.contact.name == "John"

    config = validate_config(contact={"name": "John", "url": "https://example.com"})
    assert config.contact is not None
    assert config.contact.name == "John"
    assert str(config.contact.url).rstrip("/") == "https://example.com"

    config = validate_config(contact={"name": "John", "email": "hello@github.com"})
    assert config.contact is not None
    assert config.contact.name == "John"
    assert config.contact.email == "hello@github.com"

    with pytest.raises(ConfigurationError):
        validate_config(contact={"name": "John", "url": "url"})


def test_config_kwargs_are_normalized_to_snake_case():
    config = validate_config(
        TITLE="Demo API",
        PATH="docs",
        termsOfService="https://example.com/camel-terms",
    )

    assert config.title == "Demo API"
    assert config.path == "docs"
    assert str(config.terms_of_service) == "https://example.com/camel-terms"


def test_config_rejects_duplicate_normalized_keys():
    with pytest.raises(
        ConfigurationError,
        match=r"duplicate field key for terms_of_service",
    ):
        validate_config(
            TERMS_OF_SERVICE="https://example.com/terms",
            termsOfService="https://example.com/camel-terms",
        )


def test_config_rejects_unknown_top_level_fields():
    with pytest.raises(
        ConfigurationError,
        match=r"unknown fields for Configuration: unexpected",
    ):
        validate_config(unexpected=True)


def test_config_rejects_unknown_nested_fields():
    with pytest.raises(
        ConfigurationError,
        match=r"unknown fields for License: extra",
    ):
        validate_config(license={"name": "MIT", "extra": "value"})


def test_config_rejects_unknown_fields_after_normalization():
    with pytest.raises(
        ConfigurationError,
        match=r"unknown fields for Configuration: unknown_field_name",
    ):
        validate_config(unknownFieldName=True)


def test_openapi_info_serialization():
    config = validate_config(
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
        "contact": {"name": "John", "email": "hello@example.com"},
        "license": {
            "name": "MIT",
            "url": "https://opensource.org/licenses/MIT",
        },
    }


def test_swagger_oauth2_config_serialization():
    config = validate_config(
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


def test_config_mutable_defaults_are_isolated():
    config = validate_config()
    other = validate_config()

    config.scopes.append("read")
    config.additional_query_string_params["audience"] = "spectree"
    assert config.servers is not None
    config.servers.append(models.Server(url="https://github.com"))

    assert other.scopes == []
    assert other.additional_query_string_params == {}
    assert other.servers == []


def test_config_allows_assignment_without_revalidation():
    config = validate_config()

    config.mode = "strict"
    assert config.mode == "strict"

    config.contact = {"name": "John", "email": "hello@example.com"}
    assert config.contact == {"name": "John", "email": "hello@example.com"}

    config.terms_of_service = "invalid-url"
    assert config.terms_of_service == "invalid-url"

    config.security = {"auth_apiKey": [1]}
    assert config.security == {"auth_apiKey": [1]}

    with pytest.raises(
        ConfigurationError,
        match=r"unknown fields for Configuration: unknown_field",
    ):
        config.unknown_field = True


@pytest.mark.parametrize(("secure_item"), SECURITY_SCHEMAS)
def test_update_security_scheme(secure_item: SecurityScheme):
    config = validate_config(security_schemes=[dump_security_scheme(secure_item)])
    assert config.security_schemes is not None
    assert config.security_schemes[0].name == secure_item.name
    assert config.security_schemes[0].data == secure_item.data


def test_update_security_schemes():
    config = validate_config(
        security_schemes=[dump_security_scheme(item) for item in SECURITY_SCHEMAS]
    )
    assert config.security_schemes == SECURITY_SCHEMAS


def test_config_parses_servers_from_mappings():
    config = validate_config(
        servers=[
            {"url": "https://example.com", "description": "primary"},
            {"url": "https://backup.example.com"},
        ]
    )

    assert config.servers == [
        models.Server(url="https://example.com", description="primary"),
        models.Server(url="https://backup.example.com"),
    ]


def test_config_parses_security_schemes_from_mappings():
    config = validate_config(
        security_schemes=[
            {
                "name": "auth_apiKey",
                "data": {"type": "apiKey", "in": "query", "name": "auth-api-key"},
            }
        ]
    )

    assert config.security_schemes is not None
    assert len(config.security_schemes) == 1
    assert config.security_schemes[0].name == "auth_apiKey"
    assert config.security_schemes[0].data.type.value == "apiKey"
    assert config.security_schemes[0].data.field_in.value == "query"
    assert config.security_schemes[0].data.name == "auth-api-key"


def test_config_parses_security_from_union_shapes():
    config = validate_config(security={"auth_apiKey": ["read"]})
    assert config.security == {"auth_apiKey": ["read"]}

    config = validate_config(security=[{"auth_apiKey": ["read"]}])
    assert config.security == [{"auth_apiKey": ["read"]}]


@pytest.mark.parametrize(("secure_item"), SECURITY_SCHEMAS)
def test_update_security_scheme_wrong_type(secure_item: SecurityScheme):
    with pytest.raises(ModelValidationError):
        validate_security_scheme(
            name=secure_item.name,
            data={
                **secure_item.data.model_dump(),
                "type": f"{secure_item.data.type.value}_wrong",
            },
        )


@pytest.mark.parametrize(("secure_item"), WRONG_SECURITY_SCHEMAS_DATA)
def test_update_security_scheme_wrong_data(secure_item: dict):
    with pytest.raises(ModelValidationError):
        validate_security_scheme(**secure_item)
