import inspect
import io
import re
from http import HTTPStatus

import pytest

from spectree.utils import get_model_key
from tests.common import UserXmlData, build_security_schemes, get_paths
from tests.common_dataclass import Item, Payload, RequiredLimitQuery, ReturnCase
from tests.model_cases import PYDANTIC_MODEL_CASE_PARAMS
from tests.plugin_flask.apps import (
    FLASK_USER,
    QUART_BACKEND,
    WERKZEUG_BACKENDS,
    FlaskAdapterApp,
    build_flask_adapter_app,
    build_flask_blueprint_adapter_app,
    build_flask_view_adapter_app,
    build_werkzeug_global_secure_adapter_app,
    build_werkzeug_ping_adapter_app,
    build_werkzeug_secure_adapter_app,
)


async def _spec_data(adapter_app):
    if adapter_app.backend == QUART_BACKEND:
        async with adapter_app.app.app_context():
            return adapter_app.spec.spec
    with adapter_app.app.app_context():
        return adapter_app.spec.spec


async def _client_request(adapter_app, method: str, path: str, **kwargs):
    response = getattr(adapter_app.client, method)(path, **kwargs)
    if inspect.isawaitable(response):
        return await response
    return response


async def _response_json(response):
    json_data = response.json
    if inspect.isawaitable(json_data):
        return await json_data
    return json_data


@pytest.fixture
def flask_adapter_app(model_case):
    adapter_app = build_flask_adapter_app(model_case)
    with adapter_app.client as client:
        yield FlaskAdapterApp(
            client=client,
            spec=adapter_app.spec,
            create_item=adapter_app.create_item,
            blueprint_create_item=adapter_app.blueprint_create_item,
            view_post=adapter_app.view_post,
        )


@pytest.mark.anyio
@pytest.mark.parametrize("backend", WERKZEUG_BACKENDS)
async def test_werkzeug_model_adapter_secure_spec(model_case, backend):
    security_schemes = build_security_schemes(model_case)
    adapter_app = build_werkzeug_secure_adapter_app(model_case, backend)
    spec = await _spec_data(adapter_app)

    assert [*spec["components"]["securitySchemes"].keys()] == [
        scheme.name for scheme in security_schemes
    ]

    paths = spec["paths"]
    for path, path_data in paths.items():
        security = path_data["get"].get("security")
        if path == "/no-secure-ping":
            assert security is None
            continue

        for secure_key, secure_value in security[0].items():
            assert secure_key in [scheme.name for scheme in security_schemes]

            if secure_value:
                scopes = [
                    scheme.data.flows["authorizationCode"]["scopes"]
                    for scheme in security_schemes
                    if scheme.name == secure_key
                ]
                assert set(secure_value).issubset(*scopes)


@pytest.mark.anyio
@pytest.mark.parametrize("backend", WERKZEUG_BACKENDS)
async def test_werkzeug_model_adapter_secure_global_spec(model_case, backend):
    security_schemes = build_security_schemes(model_case)
    adapter_app = build_werkzeug_global_secure_adapter_app(model_case, backend)
    spec = await _spec_data(adapter_app)

    assert [*spec["components"]["securitySchemes"].keys()] == [
        scheme.name for scheme in security_schemes
    ]
    assert spec["security"] == [{"auth_apiKey": []}]

    paths = spec["paths"]
    assert paths["/no-secure-override-ping"]["get"].get("security") == []
    assert paths["/oauth2-flows-override-ping"]["get"].get("security") == [
        {"auth_oauth2": ["admin", "read"]}
    ]
    assert paths["/global-secure-ping"]["get"].get("security") is None
    assert paths["/security_and"]["get"].get("security") == [
        {"auth_apiKey": [], "auth_apiKey_backup": []}
    ]
    assert paths["/security_or"]["get"].get("security") == [
        {"auth_apiKey": []},
        {"auth_apiKey_backup": []},
    ]


@pytest.mark.parametrize("model_case", PYDANTIC_MODEL_CASE_PARAMS, indirect=True)
def test_flask_pydantic_header_validation_preserves_existing_behavior(
    model_case,
    flask_adapter_app,
):
    response = flask_adapter_app.client.get("/ping")
    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert response.headers.get("X-Error") == "Validation Error"

    response = flask_adapter_app.client.get("/ping", headers={"lang": "en-US"})
    assert response.status_code == HTTPStatus.ACCEPTED
    assert response.json == {"msg": "pong"}
    assert response.headers.get("X-Error") is None
    assert response.headers.get("X-Validation") == "Pass"
    assert response.headers.get("lang") == "en-US"


def test_flask_model_adapter_get_route(flask_adapter_app):
    response = flask_adapter_app.client.get(
        f"/api/user/{FLASK_USER}",
        headers={"Content-Type": "text/plain"},
    )

    assert response.status_code == HTTPStatus.OK
    assert response.json == {"name": FLASK_USER}


@pytest.mark.parametrize("path", ["/api/user", "/api/user_annotated"])
def test_flask_model_adapter_validation_flow(flask_adapter_app, path):
    flask_adapter_app.client.set_cookie(
        key="pub",
        value="abcdefg",
        secure=True,
        httponly=True,
        samesite="Strict",
    )

    response = flask_adapter_app.client.post(
        f"{path}/{FLASK_USER}?order=1",
        json={"name": FLASK_USER, "limit": 10},
    )

    assert response.status_code == HTTPStatus.OK
    assert response.json == {"name": FLASK_USER, "score": [10, 1]}
    assert response.headers.get("X-API") == "OK"
    assert response.headers.get("X-Validation") is None

    response = flask_adapter_app.client.post(
        f"{path}/{FLASK_USER}?order=0",
        data={"name": FLASK_USER, "limit": 10},
        content_type="application/x-www-form-urlencoded",
    )

    assert response.status_code == HTTPStatus.OK
    assert response.json == {"name": FLASK_USER, "score": [0, 10]}


@pytest.mark.parametrize("path", ["/api/user", "/api/user_annotated"])
def test_flask_model_adapter_validation_error(flask_adapter_app, path):
    response = flask_adapter_app.client.post(f"{path}/{FLASK_USER}")

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert response.headers.get("X-Error") == "Validation Error"


@pytest.mark.parametrize("response_format", ["json", "xml"])
def test_flask_model_adapter_skip_validation(flask_adapter_app, response_format):
    flask_adapter_app.client.set_cookie(
        key="pub",
        value="abcdefg",
        secure=True,
        httponly=True,
        samesite="Strict",
    )

    response = flask_adapter_app.client.post(
        f"/api/user_skip/{FLASK_USER}?order=1&response_format={response_format}",
        json={"name": FLASK_USER, "limit": 10},
    )

    assert response.status_code == HTTPStatus.OK
    assert response.headers.get("X-API") == "OK"
    assert response.headers.get("X-Validation") is None
    if response_format == "json":
        assert response.json == {"name": FLASK_USER, "x_score": [10, 1]}
    else:
        assert response.content_type == "text/xml"
        user_xml_data = UserXmlData.parse_xml(response.text)
        assert user_xml_data.name == FLASK_USER
        assert user_xml_data.score == [10, 1]


def test_flask_model_adapter_model_instance_response(flask_adapter_app):
    flask_adapter_app.client.set_cookie(
        key="pub",
        value="abcdefg",
        secure=True,
        httponly=True,
        samesite="Strict",
    )

    response = flask_adapter_app.client.post(
        f"/api/user_model/{FLASK_USER}?order=1",
        json={"name": FLASK_USER, "limit": 10},
    )

    assert response.status_code == HTTPStatus.OK
    assert response.json == {"name": FLASK_USER, "score": [10, 1]}
    assert response.headers.get("X-API") == "OK"


def test_flask_model_adapter_no_response(flask_adapter_app):
    response = flask_adapter_app.client.get("/api/no_response")
    assert response.status_code == HTTPStatus.OK

    response = flask_adapter_app.client.post(
        "/api/no_response",
        json={"key": "value"},
    )
    assert response.status_code == HTTPStatus.OK


def test_flask_model_adapter_list_json_request(flask_adapter_app):
    response = flask_adapter_app.client.post(
        "/api/list_json",
        json=[{"name": "user1", "limit": 1}],
    )

    assert response.status_code == HTTPStatus.OK


def test_flask_model_adapter_query_list(flask_adapter_app):
    response = flask_adapter_app.client.get("/api/query_list?ids=1&ids=2&ids=3")
    assert response.status_code == HTTPStatus.OK


@pytest.mark.parametrize("pre_serialize", [False, True])
def test_flask_model_adapter_return_list(flask_adapter_app, pre_serialize):
    response = flask_adapter_app.client.get(
        f"/api/return_list?pre_serialize={int(pre_serialize)}"
    )

    assert response.status_code == HTTPStatus.OK
    assert response.json == [
        {"name": "user1", "limit": 1},
        {"name": "user2", "limit": 2},
    ]


@pytest.mark.parametrize(
    "return_case, expected_payload",
    [
        pytest.param(ReturnCase.PAYLOAD, {"name": "user1", "limit": 1}, id="payload"),
        pytest.param(ReturnCase.MODEL, {"name": "user1", "limit": 1}, id="model"),
        pytest.param(
            ReturnCase.ROOT_MODEL,
            {"name": "user1", "limit": 1},
            id="root-model",
        ),
        pytest.param(ReturnCase.RAW_LIST, [1, 2, 3, 4], id="raw-list"),
        pytest.param(ReturnCase.ROOT_LIST, [1, 2, 3, 4], id="root-list"),
    ],
)
@pytest.mark.parametrize("pre_serialize", [False, True])
def test_flask_model_adapter_return_root(
    flask_adapter_app,
    return_case,
    expected_payload,
    pre_serialize,
):
    response = flask_adapter_app.client.get(
        "/api/return_root"
        f"?return_case={return_case.value}&pre_serialize={int(pre_serialize)}"
    )

    assert response.status_code == HTTPStatus.OK
    assert response.json == expected_payload


@pytest.mark.parametrize(
    "return_case, expected_payload",
    [
        pytest.param(ReturnCase.PAYLOAD, {"name": "user1", "limit": 1}, id="payload"),
        pytest.param(ReturnCase.MODEL, {"name": "user1", "limit": 1}, id="model"),
        pytest.param(ReturnCase.RAW_LIST, [1, 2, 3, 4], id="raw-list"),
        pytest.param(
            ReturnCase.MODEL_LIST,
            [{"name": "user1", "limit": 1}],
            id="model-list",
        ),
    ],
)
def test_flask_model_adapter_return_model_without_response_model(
    flask_adapter_app,
    return_case,
    expected_payload,
):
    response = flask_adapter_app.client.get(
        f"/api/return_model?return_case={return_case.value}"
    )

    assert response.status_code == HTTPStatus.OK
    assert response.json == expected_payload


@pytest.mark.parametrize("method", ["get", "post"])
def test_flask_model_adapter_make_response(model_case, flask_adapter_app, method):
    payload = model_case.get_model(Payload)(
        limit=7,
        name="user make_response name",
    )
    request_kwargs = {
        "headers": {"lang": "en-US"},
    }
    if method == "get":
        request_kwargs["query_string"] = model_case.dump_python(payload)
    else:
        request_kwargs["json"] = model_case.dump_python(payload)

    response = getattr(flask_adapter_app.client, method)(
        "/api/return_make_response",
        **request_kwargs,
    )

    assert response.status_code == HTTPStatus.CREATED
    assert response.json == {"name": payload.name, "score": [payload.limit]}
    assert response.headers.get("lang") == "en-US"
    cookie_result = re.match(
        r"^test_cookie=\"((\w+\s?){3})\"; Secure; HttpOnly; Path=/; SameSite=Strict$",
        response.headers.get("Set-Cookie"),
    )
    assert cookie_result
    assert cookie_result.group(1) == payload.name


def test_flask_model_adapter_return_string_status(flask_adapter_app):
    response = flask_adapter_app.client.get("/api/return_string_status")

    assert response.status_code == HTTPStatus.OK
    assert response.text == "Response text string"


def test_flask_model_adapter_invalid_response(flask_adapter_app):
    response = flask_adapter_app.client.get("/api/invalid_response")

    assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR


def test_flask_model_adapter_upload_file(flask_adapter_app):
    file_content = "abcdef"
    file_io = io.BytesIO(file_content.encode("utf-8"))

    response = flask_adapter_app.client.post(
        "/api/file_upload",
        data={"file": (file_io, "test.txt"), "other": "test"},
        content_type="multipart/form-data",
    )

    assert response.status_code == HTTPStatus.OK
    assert response.json == {"content": file_content, "other": "test"}


def test_flask_model_adapter_set_cookies(flask_adapter_app):
    response = flask_adapter_app.client.get("/api/set_cookies")

    assert response.status_code == HTTPStatus.OK
    set_cookies = response.headers.getlist("Set-Cookie")
    assert len(set_cookies) == 2
    assert any(cookie.startswith("foo=hello") for cookie in set_cookies)
    assert any(cookie.startswith("bar=world") for cookie in set_cookies)


@pytest.mark.parametrize("model_case", PYDANTIC_MODEL_CASE_PARAMS, indirect=True)
def test_flask_pydantic_optional_alias_response(model_case, flask_adapter_app):
    response = flask_adapter_app.client.get("/api/return_optional_alias")

    assert response.status_code == HTTPStatus.OK
    assert response.json == {"schema": "test"}


@pytest.mark.parametrize("model_case", PYDANTIC_MODEL_CASE_PARAMS, indirect=True)
def test_flask_pydantic_custom_error(model_case, flask_adapter_app):
    response = flask_adapter_app.client.post("/api/custom_error", json={"foo": "bar"})
    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY

    response = flask_adapter_app.client.post("/api/custom_error", json={"foo": "foo"})
    assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR


@pytest.mark.parametrize("model_case", PYDANTIC_MODEL_CASE_PARAMS, indirect=True)
def test_flask_pydantic_force_response_serialize_from_attributes(
    model_case,
    flask_adapter_app,
):
    response = flask_adapter_app.client.get("/api/force_serialize")

    assert response.status_code == HTTPStatus.OK
    assert response.json == {"name": FLASK_USER, "score": [1, 2, 3]}


@pytest.mark.parametrize("path", ["/api/items", "/bp/items", "/api/view-items"])
def test_flask_model_adapter_item_validation_flow(flask_adapter_app, path):
    response = flask_adapter_app.client.post(
        f"{path}?limit=3",
        json={"name": "demo", "limit": 999},
    )

    assert response.status_code == HTTPStatus.OK
    assert response.json == [{"name": "demo", "limit": 3}]


@pytest.mark.parametrize("path", ["/api/items", "/bp/items", "/api/view-items"])
def test_flask_model_adapter_item_validation_error(flask_adapter_app, path):
    response = flask_adapter_app.client.post(
        f"{path}?limit=bad",
        json={"name": "demo", "limit": 999},
    )

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    errors = response.get_json()
    assert isinstance(errors, list)
    assert errors[0]["loc"] == ["limit"]
    assert errors[0]["msg"]
    assert errors[0]["type"]


def test_flask_model_adapter_response_models_and_spec(model_case, flask_adapter_app):
    expected_list_model = model_case.get_model(list[Item])

    for handler in (
        flask_adapter_app.create_item,
        flask_adapter_app.blueprint_create_item,
        flask_adapter_app.view_post,
    ):
        assert handler is not None
        assert (
            handler.resp.find_model(HTTPStatus.UNPROCESSABLE_ENTITY)
            is flask_adapter_app.spec.model_adapter.validation_error
        )

        response_model = handler.resp.find_model(HTTPStatus.OK)
        assert get_model_key(response_model) == get_model_key(expected_list_model)

    spec = flask_adapter_app.spec.spec
    expected_response_ref = f"#/components/schemas/{get_model_key(expected_list_model)}"
    validation_error = flask_adapter_app.spec.model_adapter.validation_error
    validation_ref = f"#/components/schemas/{get_model_key(validation_error)}"

    for path in ("/api/items", "/bp/items", "/api/view-items"):
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

    for path in (
        "/api/user/{name}",
        "/api/user_annotated/{name}",
        "/api/user_model/{name}",
    ):
        operation = spec["paths"][path]["post"]
        assert operation["tags"] == ["API", "test"]
        assert "401" in operation["responses"]


@pytest.mark.parametrize("model_case", PYDANTIC_MODEL_CASE_PARAMS, indirect=True)
@pytest.mark.parametrize(
    "builder",
    [build_flask_adapter_app, build_flask_view_adapter_app],
    ids=["function", "view"],
)
def test_flask_pydantic_route_styles_preserve_header_behavior(model_case, builder):
    adapter_app = builder(model_case)
    with adapter_app.client as client:
        response = client.get("/ping")
        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY

        response = client.get("/ping", headers={"lang": "en-US"})
        assert response.status_code == HTTPStatus.ACCEPTED
        assert response.json == {"msg": "pong"}
        assert response.headers.get("lang") == "en-US"


@pytest.mark.parametrize("model_case", PYDANTIC_MODEL_CASE_PARAMS, indirect=True)
@pytest.mark.parametrize("prefix", [None, "/prefix"])
def test_flask_pydantic_blueprint_prefix(model_case, prefix):
    adapter_app = build_flask_blueprint_adapter_app(model_case, url_prefix=prefix)
    path_prefix = prefix or ""

    with adapter_app.client as client:
        response = client.get(f"{path_prefix}/ping")
        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
        assert response.headers.get("X-Error") == "Validation Error"

        response = client.get(f"{path_prefix}/ping", headers={"lang": "en-US"})
        assert response.status_code == HTTPStatus.ACCEPTED
        assert response.json == {"msg": "pong"}
        assert response.headers.get("X-Validation") == "Pass"
        assert response.headers.get("lang") == "en-US"


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
@pytest.mark.anyio
@pytest.mark.parametrize("backend", WERKZEUG_BACKENDS)
async def test_werkzeug_model_adapter_validation_error_status_code(
    model_case,
    backend,
    api_kwargs,
    endpoint_kwargs,
    expected_status_code,
):
    adapter_app = build_werkzeug_ping_adapter_app(
        backend,
        model_case,
        api_kwargs=api_kwargs,
        endpoint_kwargs={
            "query": model_case.get_model(RequiredLimitQuery),
            **endpoint_kwargs,
        },
    )
    response = await _client_request(adapter_app, "get", "/ping")

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
@pytest.mark.anyio
@pytest.mark.parametrize("backend", WERKZEUG_BACKENDS)
async def test_werkzeug_model_adapter_doc_pages(
    model_case,
    backend,
    api_kwargs,
    expected_doc_pages,
):
    adapter_app = build_werkzeug_ping_adapter_app(
        backend,
        model_case,
        api_kwargs=api_kwargs,
    )
    spec = await _spec_data(adapter_app)

    response = await _client_request(adapter_app, "get", "/apidoc/openapi.json")
    assert await _response_json(response) == spec

    for doc_page in expected_doc_pages:
        response = await _client_request(adapter_app, "get", f"/apidoc/{doc_page}/")
        assert response.status_code == HTTPStatus.OK

        response = await _client_request(adapter_app, "get", f"/apidoc/{doc_page}")
        assert response.status_code == HTTPStatus.PERMANENT_REDIRECT


@pytest.mark.parametrize("prefix", [None, "/prefix"])
def test_flask_model_adapter_blueprint_doc_prefix(model_case, prefix):
    adapter_app = build_flask_blueprint_adapter_app(model_case, url_prefix=prefix)
    path_prefix = prefix or ""

    with adapter_app.client as client:
        assert (
            client.get(f"{path_prefix}/apidoc/openapi.json").json
            == adapter_app.spec.spec
        )
        assert client.get(f"{path_prefix}/apidoc/redoc/").status_code == HTTPStatus.OK
        assert client.get(f"{path_prefix}/apidoc/swagger/").status_code == HTTPStatus.OK

    assert all(
        path.startswith(path_prefix) for path in get_paths(adapter_app.spec.spec)
    )
