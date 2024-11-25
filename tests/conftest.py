import pytest
from syrupy.extensions.json import JSONSnapshotExtension
from syrupy.filters import paths


@pytest.fixture
def snapshot_json(snapshot):
    return snapshot.use_extension(JSONSnapshotExtension)


@pytest.fixture
def snapshot_json_exclude_diff(snapshot_json):
    return snapshot_json.with_defaults(
        exclude=paths(
            # exclude those fields that differ between the pydantic v1 & v2
            "components.schemas.RootResp.a9993e3",
            "components.schemas.ListJSON.a9993e3.JSON",
            "components.schemas.OptionalAliasResp.7068f62",
            "components.schemas.StrDict.a9993e3",
            "components.schemas.ValidationError.6a07bef",
            "components.schemas.ValidationError.6a07bef.ValidationErrorElement",
        )
    )
