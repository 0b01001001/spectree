import pytest
from syrupy.extensions.json import JSONSnapshotExtension


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def snapshot_json(snapshot):
    return snapshot.use_extension(JSONSnapshotExtension).with_defaults()
