import pytest
from pydantic import ValidationError

from spectree.config import Config

from .common import SECURITY_SCHEMAS


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
    assert config.AUTH_METHODS is None

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


def test_update_auth_method(config):
    # update and validate each schema
    for key, value in SECURITY_SCHEMAS.items():
        config.update(auth_methods={key: value})
        assert config.AUTH_METHODS == {key: value}


def test_update_auth_methods(config):
    # update and validate ALL schemas
    config.update(auth_methods=SECURITY_SCHEMAS)
    assert config.AUTH_METHODS == SECURITY_SCHEMAS


def test_update_auth_method_wrong_type(config):
    # update and validate each schema
    for key, value in SECURITY_SCHEMAS.items():
        value["type"] = value["type"] + "_wrong"

        with pytest.raises(ValidationError):
            config.update(auth_methods={key: value})


def test_update_auth_methods_wrong_types(config):
    # update and validate ALL schemas
    for key, value in SECURITY_SCHEMAS.items():
        value["type"] = value["type"] + "_wrong"
        SECURITY_SCHEMAS[key] = value

    with pytest.raises(ValidationError):
        config.update(auth_methods=SECURITY_SCHEMAS)
