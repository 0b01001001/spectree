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
