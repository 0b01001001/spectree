import importlib.util
from pathlib import Path

import pytest
from syrupy.extensions.json import JSONSnapshotExtension

from tests.model_cases import MODEL_CASE_PARAMS, build_model_case

_MSGSPEC_TEST_FILES = {
    "test_msgspec.py",
    "test_plugin_falcon_msgspec.py",
    "test_plugin_with_msgspec.py",
    "test_msgspec_plugin.py",
}
_MSGSPEC_AVAILABLE = importlib.util.find_spec("msgspec") is not None


def pytest_ignore_collect(collection_path, config):
    if _MSGSPEC_AVAILABLE:
        return False
    return Path(str(collection_path)).name in _MSGSPEC_TEST_FILES


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture(params=MODEL_CASE_PARAMS)
def model_case(request):
    return build_model_case(request.param)


@pytest.fixture
def snapshot_json(snapshot):
    return snapshot.use_extension(JSONSnapshotExtension).with_defaults()
