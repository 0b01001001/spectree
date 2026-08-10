from pathlib import Path

import pytest
from syrupy.extensions.json import JSONSnapshotExtension

from tests.model_cases import MODEL_CASE_PARAMS, build_model_case


def pytest_ignore_collect(collection_path, config):
    path = Path(str(collection_path))
    if path.parent.name == "import_module" or path.name == "import_module":
        return True
    return None


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture(params=MODEL_CASE_PARAMS)
def model_case(request):
    return build_model_case(request.param)


@pytest.fixture
def snapshot_json(snapshot):
    return snapshot.use_extension(JSONSnapshotExtension).with_defaults()
