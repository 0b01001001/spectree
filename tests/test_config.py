import string

import pytest
from pydantic import ValidationError

from spectree import SecurityScheme
from spectree.config import Config

from .common import SECURITY_SCHEMAS, WRONG_SECURITY_SCHEMAS_DATA


@pytest.fixture
def config():
    return Config()


def test_update_config(config):
    default = Config()

    config.update(title="demo", version="latest")
    assert config.DOMAIN is None
    assert config.FILENAME == default.FILENAME
    assert config.TITLE == "demo"
    assert config.VERSION == "latest"
    assert config.SECURITY_SCHEMES is None

    config.update(unknown="missing")
    with pytest.raises(AttributeError):
        assert config.unknown


def test_update_ui(config):
    config.update(ui="swagger")
    assert config.UI == "swagger"

    with pytest.raises(AssertionError) as e:
        config.update(ui="python")
    assert "UI" in str(e.value)


def test_update_mode(config):
    config.update(mode="greedy")
    assert config.MODE == "greedy"

    with pytest.raises(AssertionError) as e:
        config.update(mode="true")
    assert "MODE" in str(e.value)


@pytest.mark.parametrize(("secure_item"), SECURITY_SCHEMAS)
def test_update_security_scheme(config, secure_item: SecurityScheme):
    # update and validate each schema type
    config.update(security_schemes={secure_item.name: secure_item.data})
    assert config.SECURITY_SCHEMES == {secure_item.name: secure_item.data}


def test_update_security_schemes(config):
    # update and validate ALL schemas types
    config.update(security_schemes=SECURITY_SCHEMAS)
    assert config.SECURITY_SCHEMES == SECURITY_SCHEMAS


@pytest.mark.parametrize(("secure_item"), SECURITY_SCHEMAS)
def test_update_security_scheme_wrong_type(config, secure_item: SecurityScheme):
    # update and validate each schema type
    with pytest.raises(ValidationError):
        secure_item.data.type += "_wrong"


@pytest.mark.parametrize(
    "symbol", [symb for symb in string.punctuation if symb not in "-._"]
)
@pytest.mark.parametrize(("secure_item"), SECURITY_SCHEMAS)
def test_update_security_scheme_wrong_name(
    config, secure_item: SecurityScheme, symbol: str
):
    # update and validate each schema name
    with pytest.raises(ValidationError):
        secure_item.name += symbol

    with pytest.raises(ValidationError):
        secure_item.name = symbol + secure_item.name


@pytest.mark.parametrize(("secure_item"), WRONG_SECURITY_SCHEMAS_DATA)
def test_update_security_scheme_wrong_data(config, secure_item: dict):
    # update and validate each schema type
    with pytest.raises(ValidationError):
        SecurityScheme(**secure_item)
