import string
from typing import Type

import pytest
from pydantic import ValidationError

from spectree import SecurityScheme
from spectree.config import Configuration, EmailFieldType

from .common import SECURITY_SCHEMAS, WRONG_SECURITY_SCHEMAS_DATA


def test_config_license():
    config = Configuration(license={"name": "MIT"})
    assert config.license.name == "MIT"

    config = Configuration(
        license={"name": "MIT", "url": "https://opensource.org/licenses/MIT"}
    )
    assert config.license.name == "MIT"
    assert config.license.url == "https://opensource.org/licenses/MIT"

    with pytest.raises(ValidationError):
        config = Configuration(license={"name": "MIT", "url": "url"})


def test_config_contact():
    config = Configuration(contact={"name": "John"})
    assert config.contact.name == "John"

    config = Configuration(contact={"name": "John", "url": "https://example.com"})
    assert config.contact.name == "John"
    assert config.contact.url == "https://example.com"

    config = Configuration(contact={"name": "John", "email": "hello@github.com"})
    assert config.contact.name == "John"
    assert config.contact.email == "hello@github.com"

    with pytest.raises(ValidationError):
        config = Configuration(contact={"name": "John", "url": "url"})


@pytest.mark.skipif(EmailFieldType == str, reason="email-validator is not installled")
def test_config_contact_invalid_email():
    with pytest.raises(ValidationError):
        Configuration(contact={"name": "John", "email": "hello"})


def test_config_case():
    # lower case
    config = Configuration(title="Demo")
    assert config.title == "Demo"

    # upper case
    config = Configuration(TITLE="Demo")
    assert config.title == "Demo"

    # capitalized
    config = Configuration(Title="Demo")
    assert config.title == "Demo"


@pytest.mark.parametrize("filename", ["openapi.json", "/openapi.json"])
@pytest.mark.parametrize("path", ["", "/"])
def test_config_spec_url_when_given_empty_path(path, filename):
    """
    Test spec_url given empty path values and filename values with and
    without leading slash.
    """
    config = Configuration(path=path, filename=filename)
    assert config.spec_url == "/openapi.json"


@pytest.mark.parametrize("filename", ["openapi.json", "/openapi.json"])
@pytest.mark.parametrize("path", ["prefix", "/prefix", "prefix/", "/prefix/"])
def test_config_spec_url_when_given_path_and_filename(path, filename):
    """
    Test spec_url given path and filename values with and without
    leading/trailing slashes.
    """
    config = Configuration(path=path, filename=filename)
    assert config.spec_url == "/prefix/openapi.json"


@pytest.mark.parametrize(
    "config_path, test_path, expected_path",
    [
        pytest.param("prefix", "", "/prefix", id="root"),
        pytest.param(
            "prefix", "swagger", "/prefix/swagger", id="test-path-no-trailing-slash"
        ),
        pytest.param(
            "prefix", "swagger/", "/prefix/swagger", id="test-path-trailing-slash"
        ),
    ],
)
def test_config_join_doc_path(config_path, test_path, expected_path):
    config = Configuration(path=config_path)
    assert config.join_doc_path(test_path) == expected_path


@pytest.mark.parametrize(
    "config_path, expected_doc_root_path",
    [
        pytest.param("", "/", id="root"),
        pytest.param("prefix", "/prefix", id="path-no-trailing-slash"),
        pytest.param("prefix/", "/prefix", id="path-trailing-slash"),
    ],
)
def test_config_doc_root(config_path, expected_doc_root_path):
    config = Configuration(path=config_path)
    assert config.doc_root == expected_doc_root_path


@pytest.mark.parametrize(("secure_item"), SECURITY_SCHEMAS)
def test_update_security_scheme(secure_item: Type[SecurityScheme]):
    # update and validate each schema type
    config = Configuration(
        security_schemes=[SecurityScheme(name=secure_item.name, data=secure_item.data)]
    )
    assert config.security_schemes == [
        {"name": secure_item.name, "data": secure_item.data}
    ]


def test_update_security_schemes():
    # update and validate ALL schemas types
    config = Configuration(security_schemes=SECURITY_SCHEMAS)
    assert config.security_schemes == SECURITY_SCHEMAS


@pytest.mark.parametrize(("secure_item"), SECURITY_SCHEMAS)
def test_update_security_scheme_wrong_type(secure_item: SecurityScheme):
    # update and validate each schema type
    with pytest.raises(ValidationError):
        secure_item.data.type += "_wrong"  # type: ignore


@pytest.mark.parametrize(
    "symbol", [symb for symb in string.punctuation if symb not in "-._"]
)
@pytest.mark.parametrize(("secure_item"), SECURITY_SCHEMAS)
def test_update_security_scheme_wrong_name(secure_item: SecurityScheme, symbol: str):
    # update and validate each schema name
    with pytest.raises(ValidationError):
        secure_item.name += symbol

    with pytest.raises(ValidationError):
        secure_item.name = symbol + secure_item.name


@pytest.mark.parametrize(("secure_item"), WRONG_SECURITY_SCHEMAS_DATA)
def test_update_security_scheme_wrong_data(secure_item: dict):
    # update and validate each schema type
    with pytest.raises(ValidationError):
        SecurityScheme(**secure_item)
