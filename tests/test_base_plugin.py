import json
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Union

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


def _union_of(*types_: Any) -> Any:
    return Union[types_]


ROOT_RESP_DEF = _union_of(JSON, list[int])
STR_DICT_DEF = dict[str, str]
RESP_LIST_DEF = list[Resp]


@dataclass(frozen=True, slots=True)
class ResponsePayloads:
    model_case: Any

    @property
    def resp(self) -> Any:
        return self.model_case.get_model(Resp)

    @property
    def json(self) -> Any:
        return self.model_case.get_model(JSON)

    @property
    def root_resp(self) -> Any:
        return self.model_case.get_model(ROOT_RESP_DEF)

    @property
    def str_dict(self) -> Any:
        return self.model_case.get_model(STR_DICT_DEF)

    @property
    def complex_resp(self) -> Any:
        return self.model_case.get_model(ComplexResp)

    def response_payload(self, name: str) -> Any:
        method_name = name.replace("-", "_")
        try:
            builder = getattr(self, method_name)
        except AttributeError as exc:
            raise ValueError(f"unknown response payload case: {name}") from exc
        return builder()

    def resp_instance(self):
        return self.resp(name="user1", score=[1, 2])

    def resp_dict(self):
        return {"name": "user1", "score": [1, 2]}

    def resp_raw_dict(self):
        return RawResponsePayload({"name": "user1", "score": [1, 2]})

    def empty_dict(self):
        return {}

    def resp_missing_score(self):
        return {"name": "user1"}

    def root_list(self):
        return [1, 2, 3]

    def root_raw_list(self):
        return RawResponsePayload([1, 2, 3])

    def str_dict_instance(self):
        return self.model_case.validate_obj(
            self.str_dict,
            {"key1": "value1", "key2": "value2"},
        )

    def root_json_dict(self):
        return {"name": "user2", "limit": 1}

    def root_raw_json_dict(self):
        return RawResponsePayload({"name": "user2", "limit": 1})

    def json_instance(self):
        return self.json(name="user3", limit=5)

    def root_json_instance(self):
        return self.model_case.validate_obj(
            self.root_resp,
            self.json(name="user4", limit=23),
        )

    def empty_list(self):
        return []

    def resp_list_dict(self):
        return [{"name": "user5", "score": [5, 10]}]

    def resp_list_instances(self):
        return [
            self.resp(name="user6", score=[10, 20]),
            self.resp(name="user7", score=[30, 40]),
        ]

    def plain_dict(self):
        return {"user_id": "user1", "locale": "en-gb"}

    def dummy_response(self):
        return DummyResponse(
            payload="<html></html>".encode(),
            content_type="text/html",
        )

    def complex_instance(self):
        return self.complex_resp(
            date=datetime(2025, 1, 1),
            uuid=uuid.UUID("48b417cd-a884-4e54-9f5b-85c584e5ce77"),
        )


@pytest.fixture
def response_payloads(model_case):
    return ResponsePayloads(model_case=model_case)


def _normalize_result(result: ResponseValidationResult) -> ResponseValidationResult:
    payload = result.payload
    if isinstance(payload, bytes):
        payload = json.loads(payload)
    return ResponseValidationResult(payload)


@pytest.mark.parametrize(
    "validation_model_def, response_payload_name, expected_payload",
    [
        (Resp, "resp-instance", {"name": "user1", "score": [1, 2]}),
        (Resp, "resp-dict", {"name": "user1", "score": [1, 2]}),
        (Resp, "resp-raw-dict", {"name": "user1", "score": [1, 2]}),
        (ROOT_RESP_DEF, "root-list", [1, 2, 3]),
        (ROOT_RESP_DEF, "root-raw-list", [1, 2, 3]),
        (
            STR_DICT_DEF,
            "str-dict-instance",
            {"key1": "value1", "key2": "value2"},
        ),
        (ROOT_RESP_DEF, "root-json-dict", {"name": "user2", "limit": 1}),
        (ROOT_RESP_DEF, "root-raw-json-dict", {"name": "user2", "limit": 1}),
        (ROOT_RESP_DEF, "json-instance", {"name": "user3", "limit": 5}),
        (ROOT_RESP_DEF, "root-json-instance", {"name": "user4", "limit": 23}),
        (RESP_LIST_DEF, "empty-list", []),
        (RESP_LIST_DEF, "resp-list-dict", [{"name": "user5", "score": [5, 10]}]),
        (
            RESP_LIST_DEF,
            "resp-list-instances",
            [
                {"name": "user6", "score": [10, 20]},
                {"name": "user7", "score": [30, 40]},
            ],
        ),
        (None, "plain-dict", {"user_id": "user1", "locale": "en-gb"}),
        (
            None,
            "dummy-response",
            DummyResponse(payload="<html></html>".encode(), content_type="text/html"),
        ),
        (
            ComplexResp,
            "complex-instance",
            {
                "date": "2025-01-01T00:00:00",
                "uuid": "48b417cd-a884-4e54-9f5b-85c584e5ce77",
            },
        ),
    ],
)
def test_validate_response(
    model_case,
    response_payloads,
    validation_model_def,
    response_payload_name,
    expected_payload,
):
    result = validate_response(
        model_adapter=model_case.adapter,
        validation_model=model_case.get_model(validation_model_def),
        response_payload=response_payloads.response_payload(response_payload_name),
    )

    assert _normalize_result(result) == ResponseValidationResult(expected_payload)


@pytest.mark.parametrize(
    "validation_model_def, response_payload_name",
    [
        (Resp, "empty-dict"),
        (Resp, "resp-missing-score"),
        (ROOT_RESP_DEF, "empty-dict"),
    ],
)
def test_validate_response_rejects_invalid_payload(
    model_case,
    response_payloads,
    validation_model_def,
    response_payload_name,
):
    validation_model = model_case.get_model(validation_model_def)
    response_payload = response_payloads.response_payload(response_payload_name)

    with pytest.raises(model_case.adapter.validation_error):
        validate_response(
            model_adapter=model_case.adapter,
            validation_model=validation_model,
            response_payload=response_payload,
        )
