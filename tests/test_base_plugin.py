import json
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional, Union

import pytest

from spectree.model_adapter import ModelClass
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


@dataclass(frozen=True, slots=True)
class BasePluginModels:
    resp: Any
    json: Any
    root_resp: Any
    str_dict: Any
    complex_resp: Any
    resp_list: Any


@dataclass(frozen=True, slots=True)
class ResponsePayloadFactory:
    model_case: Any
    models: BasePluginModels

    def resp_instance(self):
        return self.models.resp(name="user1", score=[1, 2])

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
            self.models.str_dict,
            {"key1": "value1", "key2": "value2"},
        )

    def root_json_dict(self):
        return {"name": "user2", "limit": 1}

    def root_raw_json_dict(self):
        return RawResponsePayload({"name": "user2", "limit": 1})

    def json_instance(self):
        return self.models.json(name="user3", limit=5)

    def root_json_instance(self):
        return self.model_case.validate_obj(
            self.models.root_resp,
            self.models.json(name="user4", limit=23),
        )

    def empty_list(self):
        return []

    def resp_list_dict(self):
        return [{"name": "user5", "score": [5, 10]}]

    def resp_list_instances(self):
        return [
            self.models.resp(name="user6", score=[10, 20]),
            self.models.resp(name="user7", score=[30, 40]),
        ]

    def plain_dict(self):
        return {"user_id": "user1", "locale": "en-gb"}

    def dummy_response(self):
        return DummyResponse(
            payload="<html></html>".encode(),
            content_type="text/html",
        )

    def complex_instance(self):
        return self.models.complex_resp(
            date=datetime(2025, 1, 1),
            uuid=uuid.UUID("48b417cd-a884-4e54-9f5b-85c584e5ce77"),
        )


def _union_of(*types_: Any) -> Any:
    return Union[types_]


@pytest.fixture
def base_plugin_models(model_case):
    resp_model = model_case.convert_dataclass(Resp)
    json_model = model_case.convert_dataclass(JSON)
    complex_resp_model = model_case.convert_dataclass(ComplexResp)
    root_resp_model = model_case.adapter.make_root_model(
        _union_of(json_model, list[int]),
        name="RootResp",
        module=__name__,
    )
    str_dict_model = model_case.adapter.make_root_model(
        dict[str, str],
        name="StrDict",
        module=__name__,
    )

    return BasePluginModels(
        resp=resp_model,
        json=json_model,
        root_resp=root_resp_model,
        str_dict=str_dict_model,
        complex_resp=complex_resp_model,
        resp_list=model_case.adapter.make_list_model(resp_model),
    )


def _get_model(models: BasePluginModels, name: Optional[str]) -> Optional[ModelClass]:
    if name is None:
        return None
    return getattr(models, name)


def _get_response_payload(model_case, models: BasePluginModels, name: str):
    factory = ResponsePayloadFactory(model_case, models)
    method_name = name.replace("-", "_")
    try:
        builder = getattr(factory, method_name)
    except AttributeError as exc:
        raise ValueError(f"unknown response payload case: {name}") from exc
    return builder()


def _normalize_result(result: ResponseValidationResult) -> ResponseValidationResult:
    payload = result.payload
    if isinstance(payload, bytes):
        payload = json.loads(payload)
    return ResponseValidationResult(payload)


@pytest.mark.parametrize(
    "validation_model_name, response_payload_name, expected_payload",
    [
        ("resp", "resp-instance", {"name": "user1", "score": [1, 2]}),
        ("resp", "resp-dict", {"name": "user1", "score": [1, 2]}),
        ("resp", "resp-raw-dict", {"name": "user1", "score": [1, 2]}),
        ("root_resp", "root-list", [1, 2, 3]),
        ("root_resp", "root-raw-list", [1, 2, 3]),
        (
            "str_dict",
            "str-dict-instance",
            {"key1": "value1", "key2": "value2"},
        ),
        ("root_resp", "root-json-dict", {"name": "user2", "limit": 1}),
        ("root_resp", "root-raw-json-dict", {"name": "user2", "limit": 1}),
        ("root_resp", "json-instance", {"name": "user3", "limit": 5}),
        ("root_resp", "root-json-instance", {"name": "user4", "limit": 23}),
        ("resp_list", "empty-list", []),
        ("resp_list", "resp-list-dict", [{"name": "user5", "score": [5, 10]}]),
        (
            "resp_list",
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
            "complex_resp",
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
    base_plugin_models,
    validation_model_name,
    response_payload_name,
    expected_payload,
):
    result = validate_response(
        model_adapter=model_case.adapter,
        validation_model=_get_model(base_plugin_models, validation_model_name),
        response_payload=_get_response_payload(
            model_case,
            base_plugin_models,
            response_payload_name,
        ),
    )

    assert _normalize_result(result) == ResponseValidationResult(expected_payload)


@pytest.mark.parametrize(
    "validation_model_name, response_payload_name",
    [
        ("resp", "empty-dict"),
        ("resp", "resp-missing-score"),
        ("root_resp", "empty-dict"),
    ],
)
def test_validate_response_rejects_invalid_payload(
    model_case,
    base_plugin_models,
    validation_model_name,
    response_payload_name,
):
    validation_model = _get_model(base_plugin_models, validation_model_name)
    response_payload = _get_response_payload(
        model_case,
        base_plugin_models,
        response_payload_name,
    )

    with pytest.raises(model_case.adapter.validation_error):
        validate_response(
            model_adapter=model_case.adapter,
            validation_model=validation_model,
            response_payload=response_payload,
        )
