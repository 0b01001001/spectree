import pytest

from spectree.config import Config


@pytest.fixture
def config():
    return Config()


def test_update_config(config):
    default = Config()

    config.update(title='demo', version='latest')
    assert config.DOMAIN is None
    assert config.FILENAME == default.FILENAME
    assert config.TITLE == 'demo'
    assert config.VERSION == 'latest'

    config.update(unknown='missing')
    with pytest.raises(AttributeError):
        assert config.unknown


def test_update_ui(config):
    config.update(ui='swagger')
    assert config.UI == 'swagger'

    with pytest.raises(AssertionError) as e:
        config.update(ui='python')
    assert 'UI' in str(e.value)


def test_update_mode(config):
    config.update(mode='greedy')
    assert config.MODE == 'greedy'

    with pytest.raises(AssertionError) as e:
        config.update(mode='true')
    assert 'MODE' in str(e.value)
