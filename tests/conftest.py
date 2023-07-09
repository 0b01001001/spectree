from pathlib import Path

import pytest
from syrupy.extensions.json import JSONSnapshotExtension
from syrupy.location import PyTestLocation


def create_validator_fixture(validator: str):
    class VersionedJSONExtension(JSONSnapshotExtension):
        @classmethod
        def dirname(cls, *, test_location: "PyTestLocation") -> str:
            return str(
                Path(test_location.filepath).parent.joinpath(
                    "__snapshots__", f"{validator}"
                )
            )

    return VersionedJSONExtension


PydanticJSONExtension1 = create_validator_fixture(validator="pydantic1")
PydanticJSONExtension2 = create_validator_fixture(validator="pydantic2")


@pytest.fixture
def snapshot_pydantic1(snapshot):
    return snapshot.use_extension(PydanticJSONExtension1)


@pytest.fixture
def snapshot_pydantic2(snapshot):
    return snapshot.use_extension(PydanticJSONExtension2)
