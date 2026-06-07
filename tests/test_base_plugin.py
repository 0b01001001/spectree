import json
import uuid
from dataclasses import asdict, dataclass, is_dataclass
from datetime import datetime
from typing import Union

import pytest

from spectree.plugins.base import (
    RawResponsePayload,
    ResponseValidationResult,
    validate_response,
)


@dataclass(frozen=True)
class DummyResponse:
    payload: bytes
    content_type: str


@dataclass
class Resp:
    name: str
    score: list[int]


@dataclass
class JSON:
    name: str
    limit: int


@dataclass
class ComplexResp:
    date: datetime
    uuid: uuid.UUID


@pytest.mark.parametrize(
    "validation_model_def, response_payload, expected_payload",
    [
        (Resp, {"name": "user1", "score": [1, 2]}, {"name": "user1", "score": [1, 2]}),
        (
            Resp,
            RawResponsePayload({"name": "user1", "score": [1, 2]}),
            {"name": "user1", "score": [1, 2]},
        ),
        (
            Resp,
            Resp(name="user1", score=[1, 2]),
            {"name": "user1", "score": [1, 2]},
        ),
        (Union[JSON, list[int]], [1, 2, 3], [1, 2, 3]),
        (Union[JSON, list[int]], RawResponsePayload([1, 2, 3]), [1, 2, 3]),
        (
            dict[str, str],
            {"key1": "value1", "key2": "value2"},
            {"key1": "value1", "key2": "value2"},
        ),
        (
            Union[JSON, list[int]],
            {"name": "user2", "limit": 1},
            {"name": "user2", "limit": 1},
        ),
        (
            Union[JSON, list[int]],
            RawResponsePayload({"name": "user2", "limit": 1}),
            {"name": "user2", "limit": 1},
        ),
        (list[Resp], [], []),
        (
            list[Resp],
            [{"name": "user5", "score": [5, 10]}],
            [
                {"name": "user5", "score": [5, 10]},
            ],
        ),
        (
            list[Resp],
            [
                Resp(name="user6", score=[10, 20]),
                Resp(name="user7", score=[30, 40]),
            ],
            [
                {"name": "user6", "score": [10, 20]},
                {"name": "user7", "score": [30, 40]},
            ],
        ),
        (
            None,
            {"user_id": "user1", "locale": "en-gb"},
            {"user_id": "user1", "locale": "en-gb"},
        ),
        (
            None,
            DummyResponse(payload="<html></html>".encode(), content_type="text/html"),
            DummyResponse(payload="<html></html>".encode(), content_type="text/html"),
        ),
        (
            ComplexResp,
            {
                "date": datetime(2025, 1, 1),
                "uuid": uuid.UUID("48b417cd-a884-4e54-9f5b-85c584e5ce77"),
            },
            {
                "date": datetime(2025, 1, 1),
                "uuid": uuid.UUID("48b417cd-a884-4e54-9f5b-85c584e5ce77"),
            },
        ),
    ],
)
def test_validate_response(
    model_case,
    validation_model_def,
    response_payload,
    expected_payload,
):
    validation_model = model_case.get_model(validation_model_def)
    if (
        validation_model is not None
        and is_dataclass(response_payload)
        and not isinstance(response_payload, RawResponsePayload)
    ):
        response_payload = model_case.validate_obj(
            model_case.get_model(type(response_payload)),
            asdict(response_payload),
        )
    elif (
        validation_model is not None
        and isinstance(response_payload, list)
        and any(is_dataclass(item) for item in response_payload)
    ):
        response_payload = [
            model_case.validate_obj(model_case.get_model(type(item)), asdict(item))
            if is_dataclass(item)
            else item
            for item in response_payload
        ]

    result = validate_response(
        model_adapter=model_case.adapter,
        validation_model=validation_model,
        response_payload=response_payload,
    )
    payload = result.payload
    if isinstance(payload, bytes):
        payload = json.loads(payload)

    assert ResponseValidationResult(payload) == ResponseValidationResult(
        expected_payload
    )


@pytest.mark.parametrize(
    "validation_model_def, response_payload",
    [
        (Resp, {}),
        (Resp, {"name": "user1"}),
        (Union[JSON, list[int]], {}),
    ],
)
def test_validate_response_rejects_invalid_payload(
    model_case,
    validation_model_def,
    response_payload,
):
    validation_model = model_case.get_model(validation_model_def)

    with pytest.raises(model_case.adapter.validation_error):
        validate_response(
            model_adapter=model_case.adapter,
            validation_model=validation_model,
            response_payload=response_payload,
        )
