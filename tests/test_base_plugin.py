from contextlib import nullcontext as does_not_raise
from dataclasses import dataclass
from typing import Any, Union

import pytest
from pydantic import ValidationError

from spectree._types import OptionalModelType
from spectree.plugins.base import (
    RawResponsePayload,
    ResponseValidationResult,
    validate_response,
)
from spectree.utils import gen_list_model
from tests.common import JSON, Resp, RootResp, StrDict

RespList = gen_list_model(Resp)


@dataclass(frozen=True)
class DummyResponse:
    payload: bytes
    content_type: str


@pytest.mark.parametrize(
    [
        "validation_model",
        "response_payload",
        "expected_result",
    ],
    [
        (
            Resp,
            Resp(name="user1", score=[1, 2]),
            ResponseValidationResult({"name": "user1", "score": [1, 2]}),
        ),
        (
            Resp,
            {"name": "user1", "score": [1, 2]},
            ResponseValidationResult({"name": "user1", "score": [1, 2]}),
        ),
        (
            Resp,
            RawResponsePayload({"name": "user1", "score": [1, 2]}),
            ResponseValidationResult({"name": "user1", "score": [1, 2]}),
        ),
        (
            Resp,
            {},
            ValidationError,
        ),
        (
            Resp,
            {"name": "user1"},
            ValidationError,
        ),
        (
            RootResp,
            [1, 2, 3],
            ResponseValidationResult([1, 2, 3]),
        ),
        (
            RootResp,
            RawResponsePayload([1, 2, 3]),
            ResponseValidationResult([1, 2, 3]),
        ),
        (
            StrDict,
            StrDict.parse_obj({"key1": "value1", "key2": "value2"}),
            ResponseValidationResult({"key1": "value1", "key2": "value2"}),
        ),
        (
            RootResp,
            {"name": "user2", "limit": 1},
            ResponseValidationResult({"name": "user2", "limit": 1}),
        ),
        (
            RootResp,
            RawResponsePayload({"name": "user2", "limit": 1}),
            ResponseValidationResult({"name": "user2", "limit": 1}),
        ),
        (
            RootResp,
            JSON(name="user3", limit=5),
            ResponseValidationResult({"name": "user3", "limit": 5}),
        ),
        (
            RootResp,
            RootResp.parse_obj(JSON(name="user4", limit=23)),
            ResponseValidationResult({"name": "user4", "limit": 23}),
        ),
        (
            RootResp,
            {},
            ValidationError,
        ),
        (
            RespList,
            [],
            ResponseValidationResult([]),
        ),
        (
            RespList,
            [{"name": "user5", "score": [5, 10]}],
            ResponseValidationResult([{"name": "user5", "score": [5, 10]}]),
        ),
        (
            RespList,
            [Resp(name="user6", score=[10, 20]), Resp(name="user7", score=[30, 40])],
            ResponseValidationResult(
                [
                    {"name": "user6", "score": [10, 20]},
                    {"name": "user7", "score": [30, 40]},
                ]
            ),
        ),
        (
            None,
            {"user_id": "user1", "locale": "en-gb"},
            ResponseValidationResult({"user_id": "user1", "locale": "en-gb"}),
        ),
        (
            None,
            DummyResponse(payload="<html></html>".encode(), content_type="text/html"),
            ResponseValidationResult(
                DummyResponse(
                    payload="<html></html>".encode(), content_type="text/html"
                )
            ),
        ),
    ],
)
def test_validate_response(
    validation_model: OptionalModelType,
    response_payload: Any,
    expected_result: Union[ResponseValidationResult, ValidationError],
):
    runtime_expectation = (
        pytest.raises(ValidationError)
        if expected_result == ValidationError
        else does_not_raise()
    )
    with runtime_expectation:
        result = validate_response(
            validation_model=validation_model,
            response_payload=response_payload,
        )
        assert isinstance(result, ResponseValidationResult)
        assert result == expected_result
