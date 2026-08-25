import io
from http import HTTPStatus

import pytest
from starlette.applications import Starlette
from starlette.endpoints import HTTPEndpoint
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from spectree import SpecTree
from spectree.metadata import get_function_metadata
from spectree.plugins.starlette_plugin import SpecTreeStarletteResponse
from spectree.utils import get_model_key
from tests.common import UserXmlData
from tests.common_dataclass import Item, RequiredLimitQuery, ReturnCase
from tests.model_cases import PYDANTIC_MODEL_CASE_PARAMS
from tests.plugin_starlette.apps import (
    STARLETTE_USER,
    build_starlette_adapter_app,
)


@pytest.fixture
def starlette_adapter_app(model_case):
    adapter_app = build_starlette_adapter_app(model_case)
    with adapter_app.client:
        yield adapter_app


def test_spec_tree_starlette_response_requires_active_model_adapter():
    with pytest.raises(
        RuntimeError, match="must be rendered inside a SpecTree request"
    ):
        SpecTreeStarletteResponse({"name": "user1"})


@pytest.mark.parametrize("model_case", PYDANTIC_MODEL_CASE_PARAMS, indirect=True)
def test_starlette_pydantic_header_validation_preserves_existing_behavior(
    model_case,
    starlette_adapter_app,
):
    response = starlette_adapter_app.client.get("/ping")

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert response.headers.get("X-Error") == "Validation Error"

    response = starlette_adapter_app.client.get("/ping", headers={"lang": "en-US"})

    assert response.status_code == HTTPStatus.ACCEPTED
    assert response.json() == {"msg": "pong"}
    assert response.headers.get("X-Error") is None
    assert response.headers.get("X-Name") == "Ping"
    assert response.headers.get("X-Validation") is None


@pytest.mark.parametrize("path", ["/api/user", "/api/user_annotated"])
def test_starlette_model_adapter_validation_flow(starlette_adapter_app, path):
    starlette_adapter_app.client.cookies = {"pub": "abcdefg"}

    response = starlette_adapter_app.client.post(
        f"{path}/{STARLETTE_USER}?order=1",
        json={"name": STARLETTE_USER, "limit": 10},
    )

    assert response.status_code == HTTPStatus.OK
    assert response.json() == {"name": STARLETTE_USER, "score": [10, 1]}
    assert response.headers.get("X-Validation") == "Pass"

    response = starlette_adapter_app.client.post(
        f"{path}/{STARLETTE_USER}?order=0",
        json={"name": STARLETTE_USER, "limit": 10},
    )

    assert response.status_code == HTTPStatus.OK
    assert response.json() == {"name": STARLETTE_USER, "score": [0, 10]}
    assert response.headers.get("X-Validation") == "Pass"


@pytest.mark.parametrize("path", ["/api/user", "/api/user_annotated"])
def test_starlette_model_adapter_validation_error(starlette_adapter_app, path):
    starlette_adapter_app.client.cookies.clear()

    response = starlette_adapter_app.client.post(f"{path}/{STARLETTE_USER}")

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert response.headers.get("X-Error") == "Validation Error"


@pytest.mark.parametrize("response_format", ["json", "xml"])
def test_starlette_model_adapter_skip_validation(
    starlette_adapter_app,
    response_format,
):
    starlette_adapter_app.client.cookies = {"pub": "abcdefg"}

    response = starlette_adapter_app.client.post(
        f"/api/user_skip/{STARLETTE_USER}?order=1&response_format={response_format}",
        json={"name": STARLETTE_USER, "limit": 10},
    )

    assert response.status_code == HTTPStatus.OK
    assert response.headers.get("X-Validation") == "Pass"
    if response_format == "json":
        assert response.json() == {"name": STARLETTE_USER, "x_score": [10, 1]}
    else:
        user_xml_data = UserXmlData.parse_xml(response.text)
        assert user_xml_data.name == STARLETTE_USER
        assert user_xml_data.score == [10, 1]


def test_starlette_model_adapter_model_instance_response(starlette_adapter_app):
    starlette_adapter_app.client.cookies = {"pub": "abcdefg"}

    response = starlette_adapter_app.client.post(
        f"/api/user_model/{STARLETTE_USER}?order=1",
        json={"name": STARLETTE_USER, "limit": 10},
    )

    assert response.status_code == HTTPStatus.OK
    assert response.json() == {"name": STARLETTE_USER, "score": [10, 1]}
    assert response.headers.get("X-Validation") == "Pass"


def test_starlette_model_adapter_no_response(starlette_adapter_app):
    response = starlette_adapter_app.client.get("/api/no_response")
    assert response.status_code == HTTPStatus.OK

    response = starlette_adapter_app.client.post(
        "/api/no_response",
        json={"key": "value"},
    )
    assert response.status_code == HTTPStatus.OK


def test_starlette_model_adapter_list_json_request(starlette_adapter_app):
    response = starlette_adapter_app.client.post(
        "/api/list_json",
        json=[{"name": STARLETTE_USER, "limit": 1}],
    )

    assert response.status_code == HTTPStatus.OK


@pytest.mark.parametrize("pre_serialize", [False, True])
def test_starlette_model_adapter_return_list(starlette_adapter_app, pre_serialize):
    response = starlette_adapter_app.client.get(
        f"/api/return_list?pre_serialize={int(pre_serialize)}"
    )

    assert response.status_code == HTTPStatus.OK
    assert response.json() == [
        {"name": "user1", "limit": 1},
        {"name": "user2", "limit": 2},
    ]


@pytest.mark.parametrize(
    "return_case, expected_payload",
    [
        pytest.param(
            ReturnCase.PAYLOAD,
            {"name": "user1", "limit": 1},
            id="payload-dict",
        ),
        pytest.param(
            ReturnCase.MODEL, {"name": "user1", "limit": 1}, id="payload-model"
        ),
        pytest.param(
            ReturnCase.ROOT_MODEL,
            {"name": "user1", "limit": 1},
            id="root-payload-model",
        ),
        pytest.param(ReturnCase.RAW_LIST, [1, 2, 3, 4], id="list"),
        pytest.param(ReturnCase.ROOT_LIST, [1, 2, 3, 4], id="root-list-model"),
    ],
)
def test_starlette_model_adapter_return_root(
    starlette_adapter_app,
    return_case,
    expected_payload,
):
    response = starlette_adapter_app.client.get(
        f"/api/return_root?return_case={return_case.value}"
    )

    assert response.status_code == HTTPStatus.OK
    assert response.json() == expected_payload


@pytest.mark.parametrize(
    "return_case, expected_payload",
    [
        pytest.param(
            ReturnCase.PAYLOAD,
            {"name": "user1", "limit": 1},
            id="payload-dict",
        ),
        pytest.param(
            ReturnCase.MODEL, {"name": "user1", "limit": 1}, id="payload-model"
        ),
        pytest.param(ReturnCase.RAW_LIST, [1, 2, 3, 4], id="list"),
        pytest.param(
            ReturnCase.MODEL_LIST,
            [{"name": "user1", "limit": 1}],
            id="model-list",
        ),
    ],
)
def test_starlette_model_adapter_return_model_without_response_model(
    starlette_adapter_app,
    return_case,
    expected_payload,
):
    response = starlette_adapter_app.client.get(
        f"/api/return_model?return_case={return_case.value}"
    )

    assert response.status_code == HTTPStatus.OK
    assert response.json() == expected_payload


def test_starlette_model_adapter_upload_file(starlette_adapter_app):
    file_content = "abcdef"
    file_io = io.BytesIO(file_content.encode("utf-8"))

    response = starlette_adapter_app.client.post(
        "/api/file_upload",
        files={"file": ("test.txt", file_io, "text/plain")},
        data={"other": "test"},
    )

    assert response.status_code == HTTPStatus.OK
    assert response.json() == {"file": file_content, "other": "test"}


@pytest.mark.parametrize("model_case", PYDANTIC_MODEL_CASE_PARAMS, indirect=True)
def test_starlette_pydantic_optional_alias_response(model_case, starlette_adapter_app):
    response = starlette_adapter_app.client.get("/api/return_optional_alias")

    assert response.status_code == HTTPStatus.OK
    assert response.json() == {"schema": "test"}


@pytest.mark.parametrize("model_case", PYDANTIC_MODEL_CASE_PARAMS, indirect=True)
def test_starlette_pydantic_custom_error(model_case, starlette_adapter_app):
    response = starlette_adapter_app.client.post(
        "/api/custom_error", json={"foo": "bar"}
    )
    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY

    response = starlette_adapter_app.client.post(
        "/api/custom_error", json={"foo": "foo"}
    )
    assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR


@pytest.mark.parametrize("model_case", PYDANTIC_MODEL_CASE_PARAMS, indirect=True)
def test_starlette_pydantic_force_response_serialize_from_attributes(
    model_case,
    starlette_adapter_app,
):
    response = starlette_adapter_app.client.get("/api/force_serialize")

    assert response.status_code == HTTPStatus.OK
    assert response.json() == {"name": STARLETTE_USER, "score": [1, 2, 3]}


@pytest.mark.parametrize("path", ["/api/items", "/api/view-items"])
def test_starlette_model_adapter_item_validation_flow(starlette_adapter_app, path):
    response = starlette_adapter_app.client.post(
        f"{path}?limit=3",
        json={"name": "demo", "limit": 999},
    )

    assert response.status_code == HTTPStatus.OK
    assert response.json() == [{"name": "demo", "limit": 3}]


@pytest.mark.parametrize("path", ["/api/items", "/api/view-items"])
def test_starlette_model_adapter_item_validation_error(starlette_adapter_app, path):
    response = starlette_adapter_app.client.post(
        f"{path}?limit=bad",
        json={"name": "demo", "limit": 999},
    )

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    errors = response.json()
    assert isinstance(errors, list)
    assert errors[0]["loc"] == ["limit"]
    assert errors[0]["msg"]
    assert errors[0]["type"]


def test_starlette_model_adapter_response_models_and_spec(
    model_case,
    starlette_adapter_app,
):
    expected_list_model = model_case.get_model(list[Item])

    for handler in (
        starlette_adapter_app.create_item,
        starlette_adapter_app.endpoint_post,
    ):
        assert (
            get_function_metadata(handler).resp.find_model(
                HTTPStatus.UNPROCESSABLE_ENTITY
            )
            is starlette_adapter_app.spec.model_adapter.validation_error
        )

        response_model = get_function_metadata(handler).resp.find_model(HTTPStatus.OK)
        assert get_model_key(response_model) == get_model_key(expected_list_model)

    spec = starlette_adapter_app.spec.spec
    expected_response_ref = f"#/components/schemas/{get_model_key(expected_list_model)}"
    validation_error = starlette_adapter_app.spec.model_adapter.validation_error
    validation_ref = f"#/components/schemas/{get_model_key(validation_error)}"

    for path in ("/api/items", "/api/view-items"):
        responses = spec["paths"][path]["post"]["responses"]
        ok_schema = responses[str(HTTPStatus.OK.value)]["content"]["application/json"][
            "schema"
        ]
        validation_schema = responses[str(HTTPStatus.UNPROCESSABLE_ENTITY.value)][
            "content"
        ]["application/json"]["schema"]

        assert ok_schema["$ref"] == expected_response_ref
        assert validation_schema["$ref"] == validation_ref

    request_schema = spec["paths"]["/api/no_response"]["post"]["requestBody"][
        "content"
    ]["application/json"]["schema"]
    named_model = model_case.get_model(dict[str, str], name="StrDict")
    assert (
        request_schema["$ref"] == f"#/components/schemas/{get_model_key(named_model)}"
    )

    for path in ("/api/user/{name}", "/api/user_annotated/{name}"):
        operation = spec["paths"][path]["post"]
        assert operation["tags"] == ["API", "test"]
        assert "401" in operation["responses"]


@pytest.mark.parametrize(
    "api_kwargs, endpoint_kwargs, expected_status_code",
    [
        pytest.param({}, {}, HTTPStatus.UNPROCESSABLE_ENTITY, id="default"),
        pytest.param(
            {},
            {"validation_error_status": 400},
            HTTPStatus.BAD_REQUEST,
            id="endpoint",
        ),
        pytest.param(
            {"validation_error_status": 418},
            {},
            HTTPStatus.IM_A_TEAPOT,
            id="global",
        ),
        pytest.param(
            {"validation_error_status": 400},
            {"validation_error_status": 418},
            HTTPStatus.IM_A_TEAPOT,
            id="endpoint-over-global",
        ),
    ],
)
def test_starlette_model_adapter_validation_error_status_code(
    model_case,
    api_kwargs,
    endpoint_kwargs,
    expected_status_code,
):
    spec = SpecTree("starlette", model_adapter=model_case.adapter, **api_kwargs)

    class Ping(HTTPEndpoint):
        @spec.validate(
            query=model_case.get_model(RequiredLimitQuery), **endpoint_kwargs
        )
        def get(self, request):
            return JSONResponse({"msg": "pong"})

    app = Starlette(routes=[Route("/ping", Ping)])
    spec.register(app)

    with TestClient(app) as client:
        response = client.get("/ping")

    assert response.status_code == expected_status_code


@pytest.mark.parametrize(
    "api_kwargs, expected_doc_pages",
    [
        pytest.param({}, ["redoc", "swagger"], id="default-pages"),
        pytest.param(
            {"page_templates": {"custom_page": "{spec_url}"}},
            ["custom_page"],
            id="custom-pages",
        ),
    ],
)
def test_starlette_model_adapter_doc_pages(model_case, api_kwargs, expected_doc_pages):
    spec = SpecTree("starlette", model_adapter=model_case.adapter, **api_kwargs)

    class Ping(HTTPEndpoint):
        @spec.validate()
        def get(self, request):
            return JSONResponse({"msg": "pong"})

    app = Starlette(routes=[Route("/ping", Ping)])
    spec.register(app)

    with TestClient(app) as client:
        assert client.get("/apidoc/openapi.json").json() == spec.spec
        for doc_page in expected_doc_pages:
            assert client.get(f"/apidoc/{doc_page}").status_code == HTTPStatus.OK
