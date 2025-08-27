import pytest
from syrupy.extensions.json import JSONSnapshotExtension
from syrupy.filters import paths


@pytest.fixture
def snapshot_json(snapshot):
    return snapshot.use_extension(JSONSnapshotExtension)


@pytest.fixture
def snapshot_json_exclude_diff(snapshot_json):
    return snapshot_json.with_defaults(
        # exclude those fields that differ between the pydantic v1 & v2
        exclude=paths(
            "components.schemas.FormFileUpload.7068f62",
            "components.schemas.OptionalAliasResp.7068f62",
        )
    )
