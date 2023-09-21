from contextlib import nullcontext as does_not_raise
from dataclasses import dataclass
from typing import Any, Union

import pytest

from spectree._pydantic import ValidationError
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
        "skip_validation",
        "validation_model",
        "response_payload",
        "expected_result",
    ],
    [
        (
            False,
            Resp,
            Resp(name="user1", score=[1, 2]),
            ResponseValidationResult({"name": "user1", "score": [1, 2]}),
        ),
        (
            False,
            Resp,
            {"name": "user1", "score": [1, 2]},
            ResponseValidationResult({"name": "user1", "score": [1, 2]}),
        ),
        (
            False,
            Resp,
            RawResponsePayload({"name": "user1", "score": [1, 2]}),
            ResponseValidationResult({"name": "user1", "score": [1, 2]}),
        ),
        (
            False,
            Resp,
            {},
            ValidationError,
        ),
        (
            False,
            Resp,
            {"name": "user1"},
            ValidationError,
        ),
        (
            False,
            RootResp,
            [1, 2, 3],
            ResponseValidationResult([1, 2, 3]),
        ),
        (
            False,
            RootResp,
            RawResponsePayload([1, 2, 3]),
            ResponseValidationResult([1, 2, 3]),
        ),
        (
            False,
            StrDict,
            StrDict(__root__={"key1": "value1", "key2": "value2"}),
            ResponseValidationResult({"key1": "value1", "key2": "value2"}),
        ),
        (
            False,
            RootResp,
            {"name": "user2", "limit": 1},
            ResponseValidationResult({"name": "user2", "limit": 1}),
        ),
        (
            False,
            RootResp,
            RawResponsePayload({"name": "user2", "limit": 1}),
            ResponseValidationResult({"name": "user2", "limit": 1}),
        ),
        (
            False,
            RootResp,
            JSON(name="user3", limit=5),
            ResponseValidationResult({"name": "user3", "limit": 5}),
        ),
        (
            False,
            RootResp,
            RootResp(__root__=JSON(name="user4", limit=23)),
            ResponseValidationResult({"name": "user4", "limit": 23}),
        ),
        (
            False,
            RootResp,
            {},
            ValidationError,
        ),
        (
            False,
            RespList,
            [],
            ResponseValidationResult([]),
        ),
        (
            False,
            RespList,
            [{"name": "user5", "score": [5, 10]}],
            ResponseValidationResult([{"name": "user5", "score": [5, 10]}]),
        ),
        (
            False,
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
            False,
            None,
            {"user_id": "user1", "locale": "en-gb"},
            ResponseValidationResult({"user_id": "user1", "locale": "en-gb"}),
        ),
        (
            True,
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
    skip_validation: bool,
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
            skip_validation=skip_validation,
            validation_model=validation_model,
            response_payload=response_payload,
        )
        assert isinstance(result, ResponseValidationResult)
        assert result == expected_result
