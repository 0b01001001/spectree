import pytest
from syrupy.extensions.json import JSONSnapshotExtension
from syrupy.filters import paths


class JSONSnapshotExtensionPatch(JSONSnapshotExtension):
    def serialize(
        self,
        data,
        *,
        exclude=None,
        include=None,
        matcher=None,
    ):
        data = super().serialize(
            data, exclude=exclude, include=include, matcher=matcher
        )
        # match the RFC 9110 updated in Python 3.13
        # ref: https://docs.python.org/3/library/http.html
        return data.replace(
            '"description": "Unprocessable Entity"',
            '"description": "Unprocessable Content"',
        )


@pytest.fixture
def snapshot_json(snapshot):
    return snapshot.use_extension(JSONSnapshotExtensionPatch)


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
