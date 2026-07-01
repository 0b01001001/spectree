import importlib
from dataclasses import dataclass
from enum import Enum
from functools import wraps
from http import HTTPStatus
from typing import Any, Union

import falcon
import pytest
from falcon import testing as falcon_testing
from falcon.asgi import App as FalconASGIApp

from spectree import Response, SpecTree
from spectree.utils import get_model_key
from tests.common import (
    UserXmlData,
    api_tag,
)
from tests.common import (
    instance_name_after_handler as after_handler,
)
from tests.common import (
    validation_error_handler as before_handler,
)
from tests.common_dataclass import (
    Cookies,
    FormPayload,
    Item,
    OptionalPayload,
    Payload,
    Query,
    RequiredLimitQuery,
    Resp,
    RespObject,
)
from tests.model_cases import PYDANTIC_MODEL_CASE_PARAMS

FALCON_BACKEND = "falcon"
FALCON_ASGI_BACKEND = "falcon-asgi"
FALCON_USER = "falcon"
FALCON_BACKEND_PARAMS = [
    pytest.param(FALCON_BACKEND, id=FALCON_BACKEND),
    pytest.param(FALCON_ASGI_BACKEND, id=FALCON_ASGI_BACKEND),
]
FALCON_ASGI_BACKEND_PARAMS = [
    pytest.param(FALCON_ASGI_BACKEND, id=FALCON_ASGI_BACKEND),
]


@dataclass(frozen=True)
class FalconAdapterApp:
    backend: str
    client: falcon_testing.TestClient
    spec: SpecTree


class ReturnCase(str, Enum):
    PAYLOAD = "Payload"
    MODEL = "Model"
    ROOT_MODEL = "RootModel"
    RAW_LIST = "RawList"
    ROOT_LIST = "RootList"
    MODEL_LIST = "ModelList"


def backend_view(backend):
    if backend != FALCON_ASGI_BACKEND:
        return lambda func: func

    def as_async(func):
        @wraps(func)
        async def view(*args, **kwargs):
            return func(*args, **kwargs)

        return view

    return as_async


def backend_app(backend):
    if backend == FALCON_ASGI_BACKEND:
        return FalconASGIApp()
    return falcon.App()


def build_falcon_adapter_app(backend: str, model_case) -> FalconAdapterApp:  # noqa: PLR0915
    view = backend_view(backend)
    pydantic_only = model_case.name == "pydantic"
    headers_model = None
    if pydantic_only:
        headers_model = importlib.import_module("tests.common_pydantic").Headers

    spec = SpecTree(
        backend,
        before=before_handler,
        after=after_handler,
        annotations=True,
        model_adapter=model_case.adapter,
    )

    class Ping:
        name = "health check"

        @spec.validate(
            headers=headers_model,
            resp=Response(
                HTTP_202=model_case.get_model(dict[str, str], name="StrDict")
            ),
            tags=["test", "health"],
        )
        @view
        def on_get(self, req, resp):
            """summary

            description
            """
            resp.media = {"msg": "pong"}
            resp.status = falcon.HTTP_202

    class UserScore:
        name = "sorted score"

        def extra_method(self):
            pass

        @spec.validate(
            resp=Response(HTTP_200=model_case.get_model(dict[str, str], name="StrDict"))
        )
        @view
        def on_get(self, req, resp, name):
            self.extra_method()
            resp.media = {"name": name}

        @spec.validate(
            query=model_case.get_model(Query),
            json=model_case.get_model(Payload),
            cookies=model_case.get_model(Cookies),
            resp=Response(HTTP_200=model_case.get_model(Resp), HTTP_401=None),
            tags=[api_tag, "test"],
        )
        @view
        def on_post(
            self,
            req,
            resp,
            name,
            query: model_case.get_model(Query),
            json: model_case.get_model(Payload),
            cookies: model_case.get_model(Cookies),
        ):
            self.extra_method()
            assert req.context.cookies.pub == cookies.pub == "abcdefg"
            resp.media = {
                "name": json.name,
                "score": sorted([json.limit, query.order], reverse=bool(query.order)),
            }

    class UserScoreAnnotated:
        name = "annotated sorted score"

        def extra_method(self):
            pass

        @spec.validate(
            resp=Response(HTTP_200=model_case.get_model(dict[str, str], name="StrDict"))
        )
        @view
        def on_get(self, req, resp, name):
            self.extra_method()
            resp.media = {"name": name}

        @spec.validate(
            resp=Response(HTTP_200=model_case.get_model(Resp), HTTP_401=None),
            tags=[api_tag, "test"],
        )
        @view
        def on_post(
            self,
            req,
            resp,
            name,
            query: model_case.get_model(Query),
            json: model_case.get_model(Payload),
            cookies: model_case.get_model(Cookies),
        ):
            self.extra_method()
            assert req.context.cookies.pub == cookies.pub == "abcdefg"
            resp.media = {
                "name": json.name,
                "score": sorted([json.limit, query.order], reverse=bool(query.order)),
            }

    class UserScoreModel:
        name = "sorted score model"

        def extra_method(self):
            pass

        @spec.validate(
            resp=Response(HTTP_200=model_case.get_model(dict[str, str], name="StrDict"))
        )
        @view
        def on_get(self, req, resp, name):
            self.extra_method()
            resp.media = {"name": name}

        @spec.validate(
            query=model_case.get_model(Query),
            json=model_case.get_model(Payload),
            cookies=model_case.get_model(Cookies),
            resp=Response(HTTP_200=model_case.get_model(Resp), HTTP_401=None),
            tags=[api_tag, "test"],
        )
        @view
        def on_post(
            self,
            req,
            resp,
            name,
            query: model_case.get_model(Query),
            json: model_case.get_model(Payload),
            cookies: model_case.get_model(Cookies),
        ):
            self.extra_method()
            assert req.context.cookies.pub == cookies.pub == "abcdefg"
            resp.media = model_case.validate_obj(
                model_case.get_model(Resp),
                {
                    "name": json.name,
                    "score": sorted(
                        [json.limit, query.order],
                        reverse=bool(query.order),
                    ),
                },
            )

    class OptionalUserScore:
        name = "optional score"

        def extra_method(self):
            pass

        @spec.validate(
            json=model_case.get_model(OptionalPayload),
            resp=Response(HTTP_200=model_case.get_model(Resp)),
        )
        @view
        def on_post(self, req, resp, json: model_case.get_model(OptionalPayload)):
            self.extra_method()
            limit = json.limit or 10
            resp.media = {"name": json.name or "unknown", "score": [limit]}

    class UserAddress:
        name = "user's address"

        @spec.validate(
            query=model_case.get_model(Query),
            path_parameter_descriptions={
                "name": "The name that uniquely identifies the user.",
                "non-existent-param": "description",
            },
        )
        @view
        def on_get(self, req, resp, name, address_id):
            return None

    class NoResponseView:
        name = "no response view"

        @spec.validate(resp=Response(HTTP_200=None))
        @view
        def on_get(self, req, resp):
            pass

        @spec.validate(json=model_case.get_model(dict[str, str], name="StrDict"))
        @view
        def on_post(
            self,
            req,
            resp,
            json: model_case.get_model(dict[str, str], name="StrDict"),
        ):
            pass

    class ListJsonView:
        @spec.validate(json=model_case.get_model(list[Payload]))
        @view
        def on_post(self, req, resp, json: model_case.get_model(list[Payload])):
            pass

    class ReturnListView:
        @spec.validate(
            resp=Response(HTTP_200=model_case.list_of(model_case.get_model(Item)))
        )
        @view
        def on_get(self, req, resp):
            data = [
                {"name": "user1", "limit": 1},
                {"name": "user2", "limit": 2},
            ]
            if bool(int(req.params.get("pre_serialize", 0))):
                resp.media = data
            else:
                resp.media = [
                    model_case.validate_obj(model_case.get_model(Item), item)
                    for item in data
                ]

    class ReturnRootView:
        @spec.validate(
            resp=Response(
                HTTP_200=model_case.get_model(
                    Union[Payload, list[int]],
                    name="RootPayload",
                )
            )
        )
        @view
        def on_get(self, req, resp):
            return_case = req.params.get("return_case", ReturnCase.PAYLOAD.value)
            payload_data = {"name": "user1", "limit": 1}
            response_cases = {
                ReturnCase.PAYLOAD.value: payload_data,
                ReturnCase.MODEL.value: model_case.validate_obj(
                    model_case.get_model(Payload),
                    payload_data,
                ),
                ReturnCase.ROOT_MODEL.value: model_case.validate_obj(
                    model_case.get_model(Union[Payload, list[int]], name="RootPayload"),
                    payload_data,
                ),
                ReturnCase.RAW_LIST.value: [1, 2, 3, 4],
                ReturnCase.ROOT_LIST.value: model_case.validate_obj(
                    model_case.get_model(Union[Payload, list[int]], name="RootPayload"),
                    [1, 2, 3, 4],
                ),
            }
            resp.media = response_cases[return_case]

    class ReturnModelView:
        @spec.validate()
        @view
        def on_get(self, req, resp):
            return_case = req.params.get("return_case", ReturnCase.MODEL.value)
            payload_data = {"name": "user1", "limit": 1}
            response_cases = {
                ReturnCase.PAYLOAD.value: payload_data,
                ReturnCase.MODEL.value: model_case.validate_obj(
                    model_case.get_model(Payload),
                    payload_data,
                ),
                ReturnCase.RAW_LIST.value: [1, 2, 3, 4],
                ReturnCase.MODEL_LIST.value: [
                    model_case.validate_obj(
                        model_case.get_model(Payload),
                        payload_data,
                    )
                ],
            }
            resp.media = response_cases[return_case]

    if pydantic_only:
        # These routes preserve legacy pydantic-only behavior; the shared
        # adapter coverage stays on dataclass model definitions.
        common_pydantic = importlib.import_module("tests.common_pydantic")
        CustomError = common_pydantic.CustomError
        OptionalAliasResp = common_pydantic.OptionalAliasResp
        RespFromAttrs = common_pydantic.RespFromAttrs

        class ReturnOptionalAliasView:
            @spec.validate(resp=Response(HTTP_200=OptionalAliasResp))
            @view
            def on_get(self, req, resp):
                resp.media = {"schema": "test"}

        class CustomErrorView:
            name = "custom error view"

            @spec.validate(resp=Response(HTTP_200=CustomError))
            @view
            def on_post(self, req, resp, json: CustomError):
                resp.media = {"foo": "bar"}
                resp.status = falcon.HTTP_422

        class ForcedSerializerView:
            name = "view with forced response serialization"

            @spec.validate(
                resp=Response(HTTP_200=RespFromAttrs),
                force_resp_serialize=True,
            )
            @view
            def on_get(self, req, resp):
                resp.media = RespObject(
                    name=FALCON_USER,
                    score=[1, 2, 3],
                    comment="hello",
                )

    app = backend_app(backend)
    file_upload_view_cls: type[Any]

    if backend == FALCON_ASGI_BACKEND:

        class AsyncFileUploadView:
            @spec.validate(form=model_case.get_model(FormPayload))
            async def on_post(
                self,
                req,
                resp,
                form: model_case.get_model(FormPayload),
            ):
                file_content = await form.file.stream.read() if form.file else None
                other = (
                    form.other.decode("utf-8")
                    if isinstance(form.other, bytes)
                    else form.other
                )
                resp.media = {
                    "file": (
                        file_content.decode("utf-8")
                        if file_content is not None
                        else None
                    ),
                    "other": other,
                }

        class FileIterView:
            @spec.validate(form=model_case.get_model(FormPayload))
            async def on_post(
                self,
                req,
                resp,
                form: model_case.get_model(FormPayload),
            ):
                length = 0
                if form.file:
                    async for chunk in form.file.stream:
                        length += len(chunk)
                other = (
                    form.other.decode("utf-8")
                    if isinstance(form.other, bytes)
                    else form.other
                )
                resp.media = {"length": length, "other": other}

        file_upload_view_cls = AsyncFileUploadView
    else:

        class SyncFileUploadView:
            @spec.validate(form=model_case.get_model(FormPayload))
            def on_post(
                self,
                req,
                resp,
                form: model_case.get_model(FormPayload),
            ):
                file_content = form.file.stream.read() if form.file else None
                other = (
                    form.other.decode("utf-8")
                    if isinstance(form.other, bytes)
                    else form.other
                )
                resp.media = {
                    "file": (
                        file_content.decode("utf-8")
                        if file_content is not None
                        else None
                    ),
                    "other": other,
                }

        file_upload_view_cls = SyncFileUploadView

    class CustomSerializerView:
        @spec.validate(resp=Response(HTTP_200=model_case.get_model(Resp)))
        @view
        def on_get(self, req, resp):
            resp.data = model_case.adapter.dump_json(
                model_case.validate_obj(
                    model_case.get_model(Resp),
                    {"name": FALCON_USER, "score": [1, 2, 3]},
                )
            )

        @spec.validate(resp=Response(HTTP_200=model_case.get_model(Resp)))
        @view
        def on_post(self, req, resp):
            resp.text = model_case.adapter.dump_json(
                model_case.validate_obj(
                    model_case.get_model(Resp),
                    {"name": FALCON_USER, "score": [1, 2, 3]},
                )
            ).decode("utf-8")

    app.add_route("/ping", Ping())
    app.add_route("/api/user/{name}", UserScore())
    app.add_route("/api/user_annotated/{name}", UserScoreAnnotated())
    app.add_route("/api/user/{name}/address/{address_id}", UserAddress())
    app.add_route("/api/user_model/{name}", UserScoreModel())
    app.add_route("/api/user_optional", OptionalUserScore())
    app.add_route("/api/no_response", NoResponseView())
    app.add_route("/api/list_json", ListJsonView())
    app.add_route("/api/return_list", ReturnListView())
    app.add_route("/api/return_root", ReturnRootView())
    app.add_route("/api/return_model", ReturnModelView())
    app.add_route("/api/file_upload", file_upload_view_cls())
    if backend == FALCON_ASGI_BACKEND:
        app.add_route("/api/file_iter", FileIterView())
    app.add_route("/api/custom_serializer", CustomSerializerView())
    if pydantic_only:
        app.add_route("/api/return_optional_alias", ReturnOptionalAliasView())
        app.add_route("/api/force_serialize", ForcedSerializerView())
        app.add_route("/api/custom_error", CustomErrorView())
    spec.register(app)

    return FalconAdapterApp(
        backend=backend,
        client=falcon_testing.TestClient(app),
        spec=spec,
    )


@pytest.fixture(params=FALCON_BACKEND_PARAMS)
def falcon_adapter_app(request, model_case):
    return build_falcon_adapter_app(request.param, model_case)


@pytest.mark.parametrize("model_case", PYDANTIC_MODEL_CASE_PARAMS, indirect=True)
def test_falcon_pydantic_header_validation_preserves_existing_behavior(
    model_case,
    falcon_adapter_app,
):
    # This preserves the legacy pydantic Headers validator that normalizes
    # Falcon's request header casing.
    response = falcon_adapter_app.client.simulate_get(
        "/ping",
        headers={"Content-Type": "text/plain"},
    )

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert response.headers.get("X-Error") == "Validation Error"

    response = falcon_adapter_app.client.simulate_get(
        "/ping",
        headers={"lang": "en-US", "Content-Type": "text/plain"},
    )

    assert response.status_code == HTTPStatus.ACCEPTED
    assert response.json == {"msg": "pong"}
    assert response.headers.get("X-Error") is None
    assert response.headers.get("X-Name") == "health check"


@pytest.mark.parametrize("model_case", PYDANTIC_MODEL_CASE_PARAMS, indirect=True)
def test_falcon_pydantic_optional_alias_response(model_case, falcon_adapter_app):
    response = falcon_adapter_app.client.simulate_get("/api/return_optional_alias")

    assert response.status_code == HTTPStatus.OK
    assert response.json == {"schema": "test"}


@pytest.mark.parametrize("model_case", PYDANTIC_MODEL_CASE_PARAMS, indirect=True)
def test_falcon_pydantic_custom_error(model_case, falcon_adapter_app):
    response = falcon_adapter_app.client.simulate_post(
        "/api/custom_error",
        json={"foo": "bar"},
    )
    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY

    response = falcon_adapter_app.client.simulate_post(
        "/api/custom_error",
        json={"foo": "foo"},
    )
    assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR


def test_falcon_model_adapter_get_route(falcon_adapter_app):
    response = falcon_adapter_app.client.simulate_get(
        f"/api/user/{FALCON_USER}",
        headers={"Content-Type": "text/plain"},
    )

    assert response.status_code == HTTPStatus.OK
    assert response.json == {"name": FALCON_USER}


def test_falcon_model_adapter_validation_flow(falcon_adapter_app):
    response = falcon_adapter_app.client.simulate_post(
        f"/api/user/{FALCON_USER}?order=1",
        json={"name": "demo", "limit": 3},
        headers={"Cookie": "pub=abcdefg"},
    )

    assert response.status_code == HTTPStatus.OK
    assert response.json == {"name": "demo", "score": [3, 1]}
    assert response.headers.get("X-Name") == "sorted score"


def test_falcon_model_adapter_annotation_validation_flow(falcon_adapter_app):
    response = falcon_adapter_app.client.simulate_post(
        f"/api/user_annotated/{FALCON_USER}?order=0",
        json={"name": "demo", "limit": 3},
        headers={"Cookie": "pub=abcdefg"},
    )

    assert response.status_code == HTTPStatus.OK
    assert response.json == {"name": "demo", "score": [0, 3]}
    assert response.headers.get("X-Name") == "annotated sorted score"


def test_falcon_model_adapter_model_instance_response(falcon_adapter_app):
    response = falcon_adapter_app.client.simulate_post(
        f"/api/user_model/{FALCON_USER}?order=1",
        json={"name": "demo", "limit": 3},
        headers={"Cookie": "pub=abcdefg"},
    )

    assert response.status_code == HTTPStatus.OK
    assert response.json == {"name": "demo", "score": [3, 1]}
    assert response.headers.get("X-Name") == "sorted score model"


def test_falcon_model_adapter_validation_error(falcon_adapter_app):
    response = falcon_adapter_app.client.simulate_post(
        f"/api/user/{FALCON_USER}?order=bad",
        json={"name": "demo", "limit": 3},
        headers={"Cookie": "pub=abcdefg"},
    )

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert response.headers.get("X-Error") == "Validation Error"
    assert isinstance(response.json, list)
    assert response.json[0]["loc"] == ["order"]
    assert response.json[0]["msg"]
    assert response.json[0]["type"]

    response = falcon_adapter_app.client.simulate_post(f"/api/user/{FALCON_USER}")

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert response.headers.get("X-Error") == "Validation Error"
    assert response.headers.get("X-Name") is None


def test_falcon_model_adapter_optional_json(falcon_adapter_app):
    response = falcon_adapter_app.client.simulate_post("/api/user_optional")
    assert response.status_code == HTTPStatus.OK
    assert response.json == {"name": "unknown", "score": [10]}

    response = falcon_adapter_app.client.simulate_post(
        "/api/user_optional",
        json={"name": "optional", "limit": 5},
    )
    assert response.status_code == HTTPStatus.OK
    assert response.json == {"name": "optional", "score": [5]}


@pytest.mark.parametrize("backend", FALCON_BACKEND_PARAMS)
@pytest.mark.parametrize("response_format", ["json", "xml"])
def test_falcon_model_adapter_skip_validation(backend, model_case, response_format):
    spec = SpecTree(
        backend,
        before=before_handler,
        after=after_handler,
        annotations=False,
        model_adapter=model_case.adapter,
    )

    if backend == FALCON_ASGI_BACKEND:

        class UserScoreSkip:
            name = "skip validation score"

            @spec.validate(
                query=model_case.get_model(Query),
                json=model_case.get_model(Payload),
                cookies=model_case.get_model(Cookies),
                resp=Response(HTTP_200=model_case.get_model(Resp), HTTP_401=None),
                tags=[api_tag, "test"],
                skip_validation=True,
            )
            async def on_post(self, req, resp, name):
                media = await req.get_media()
                response_format = req.params.get("response_format")
                assert response_format in ("json", "xml")
                score = sorted(
                    [media.get("limit"), int(req.params.get("order"))],
                    reverse=bool(int(req.params.get("order"))),
                )
                assert req.cookies["pub"] == "abcdefg"
                if response_format == "json":
                    resp.media = {"name": media.get("name"), "x_score": score}
                else:
                    resp.content_type = falcon.MEDIA_XML
                    resp.text = UserXmlData(
                        name=media.get("name"),
                        score=score,
                    ).dump_xml()
    else:

        class UserScoreSkip:
            name = "skip validation score"

            @spec.validate(
                query=model_case.get_model(Query),
                json=model_case.get_model(Payload),
                cookies=model_case.get_model(Cookies),
                resp=Response(HTTP_200=model_case.get_model(Resp), HTTP_401=None),
                tags=[api_tag, "test"],
                skip_validation=True,
            )
            def on_post(self, req, resp, name):
                response_format = req.params.get("response_format")
                assert response_format in ("json", "xml")
                score = sorted(
                    [req.media.get("limit"), int(req.params.get("order"))],
                    reverse=bool(int(req.params.get("order"))),
                )
                assert req.cookies["pub"] == "abcdefg"
                if response_format == "json":
                    resp.media = {"name": req.media.get("name"), "x_score": score}
                else:
                    resp.content_type = falcon.MEDIA_XML
                    resp.text = UserXmlData(
                        name=req.media.get("name"),
                        score=score,
                    ).dump_xml()

    app = backend_app(backend)
    app.add_route("/api/user_skip/{name}", UserScoreSkip())
    spec.register(app)
    operation = spec.spec["paths"]["/api/user_skip/{name}"]["post"]
    assert operation["tags"] == ["API", "test"]
    assert "401" in operation["responses"]

    response = falcon_testing.TestClient(app).simulate_post(
        f"/api/user_skip/{FALCON_USER}?order=1&response_format={response_format}",
        json={"name": FALCON_USER, "limit": 10},
        headers={"Cookie": "pub=abcdefg"},
    )

    assert response.status_code == HTTPStatus.OK
    assert response.headers.get("X-Name") == "skip validation score"
    if response_format == "json":
        assert response.json == {"name": FALCON_USER, "x_score": [10, 1]}
    else:
        assert response.content_type == falcon.MEDIA_XML
        user_xml_data = UserXmlData.parse_xml(response.text)
        assert user_xml_data.name == FALCON_USER
        assert user_xml_data.score == [10, 1]


def test_falcon_model_adapter_no_response(falcon_adapter_app):
    response = falcon_adapter_app.client.simulate_get("/api/no_response")
    assert response.status_code == HTTPStatus.OK

    response = falcon_adapter_app.client.simulate_post(
        "/api/no_response",
        json={"key": "value"},
    )
    assert response.status_code == HTTPStatus.OK


def test_falcon_model_adapter_list_json_request(falcon_adapter_app):
    response = falcon_adapter_app.client.simulate_post(
        "/api/list_json",
        json=[{"name": "user1", "limit": 1}],
    )

    assert response.status_code == HTTPStatus.OK


@pytest.mark.parametrize("pre_serialize", [False, True])
def test_falcon_model_adapter_return_list(falcon_adapter_app, pre_serialize):
    response = falcon_adapter_app.client.simulate_get(
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
def test_falcon_model_adapter_return_root(
    falcon_adapter_app,
    return_case,
    expected_payload,
):
    response = falcon_adapter_app.client.simulate_get(
        f"/api/return_root?return_case={return_case.value}"
    )

    assert response.status_code == HTTPStatus.OK
    assert response.json == expected_payload


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
def test_falcon_model_adapter_return_model_without_response_model(
    falcon_adapter_app,
    return_case,
    expected_payload,
):
    response = falcon_adapter_app.client.simulate_get(
        f"/api/return_model?return_case={return_case.value}"
    )

    assert response.status_code == HTTPStatus.OK
    assert response.json == expected_payload


def test_falcon_model_adapter_doc(falcon_adapter_app):
    response = falcon_adapter_app.client.simulate_get("/apidoc/openapi.json")
    assert response.status_code == HTTPStatus.OK
    assert response.json == falcon_adapter_app.spec.spec

    response = falcon_adapter_app.client.simulate_get("/apidoc/redoc")
    assert response.status_code == HTTPStatus.OK

    response = falcon_adapter_app.client.simulate_get("/apidoc/swagger")
    assert response.status_code == HTTPStatus.OK


def test_falcon_model_adapter_file_upload(falcon_adapter_app):
    boundary = "xxx"
    file_content = "abcdef"
    body = (
        f"--{boundary}\r\n"
        'Content-Disposition: form-data; name="file"; filename="test.txt"\r\n'
        "Content-Type: text/plain\r\n\r\n"
        f"{file_content}\r\n"
        f"--{boundary}\r\n"
        'Content-Disposition: form-data; name="other"\r\n\r\n'
        "test\r\n"
        f"--{boundary}--\r\n"
    )

    response = falcon_adapter_app.client.simulate_post(
        "/api/file_upload",
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        body=body.encode("utf-8"),
    )
    assert response.status_code == HTTPStatus.OK
    assert response.json == {"file": file_content, "other": "test"}

    response = falcon_adapter_app.client.simulate_post(
        "/api/file_upload",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        body="other=test".encode("utf-8"),
    )
    assert response.status_code == HTTPStatus.OK
    assert response.json == {"file": None, "other": "test"}


@pytest.mark.parametrize(
    "falcon_adapter_app",
    FALCON_ASGI_BACKEND_PARAMS,
    indirect=True,
)
def test_falcon_model_adapter_asgi_file_iter(falcon_adapter_app):
    boundary = "xxx"
    file_content = "abcdefghijklmn" * 1000
    body = (
        f"--{boundary}\r\n"
        'Content-Disposition: form-data; name="file"; filename="test.txt"\r\n'
        "Content-Type: text/plain\r\n\r\n"
        f"{file_content}\r\n"
        f"--{boundary}\r\n"
        'Content-Disposition: form-data; name="other"\r\n\r\n'
        "test\r\n"
        f"--{boundary}--\r\n"
    )

    response = falcon_adapter_app.client.simulate_post(
        "/api/file_iter",
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        body=body.encode("utf-8"),
    )

    assert response.status_code == HTTPStatus.OK
    assert response.json == {"length": len(file_content), "other": "test"}


@pytest.mark.parametrize("method", ["GET", "POST"])
def test_falcon_model_adapter_custom_serializer(falcon_adapter_app, method):
    response = falcon_adapter_app.client.simulate_request(
        method,
        "/api/custom_serializer",
    )

    assert response.status_code == HTTPStatus.OK
    assert response.json == {"name": FALCON_USER, "score": [1, 2, 3]}


@pytest.mark.parametrize("model_case", PYDANTIC_MODEL_CASE_PARAMS, indirect=True)
def test_falcon_pydantic_force_response_serialize_from_attributes(
    model_case,
    falcon_adapter_app,
):
    response = falcon_adapter_app.client.simulate_get("/api/force_serialize")

    assert response.status_code == HTTPStatus.OK
    assert response.json == {"name": FALCON_USER, "score": [1, 2, 3]}


def test_falcon_model_adapter_response_models_and_spec(model_case, falcon_adapter_app):
    spec = falcon_adapter_app.spec.spec
    responses = spec["paths"]["/api/return_list"]["get"]["responses"]
    response_model = model_case.get_model(list[Item])
    assert responses[str(HTTPStatus.OK.value)]["content"]["application/json"]["schema"][
        "$ref"
    ] == (f"#/components/schemas/{get_model_key(response_model)}")
    validation_error = falcon_adapter_app.spec.model_adapter.validation_error
    assert responses[str(HTTPStatus.UNPROCESSABLE_ENTITY.value)]["content"][
        "application/json"
    ]["schema"]["$ref"] == (f"#/components/schemas/{get_model_key(validation_error)}")

    named_model = model_case.get_model(dict[str, str], name="StrDict")
    request_schema = spec["paths"]["/api/no_response"]["post"]["requestBody"][
        "content"
    ]["application/json"]["schema"]
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


@pytest.mark.parametrize("backend", FALCON_BACKEND_PARAMS)
@pytest.mark.parametrize(
    "api_kwargs, endpoint_kwargs, expected_status_code",
    [
        pytest.param({}, {}, HTTPStatus.UNPROCESSABLE_ENTITY, id="default"),
        pytest.param(
            {}, {"validation_error_status": 400}, HTTPStatus.BAD_REQUEST, id="endpoint"
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
def test_falcon_model_adapter_validation_error_status_code(
    backend,
    model_case,
    api_kwargs,
    endpoint_kwargs,
    expected_status_code,
):
    spec = SpecTree(backend, model_adapter=model_case.adapter, **api_kwargs)

    view = backend_view(backend)

    class Ping:
        @spec.validate(
            query=model_case.get_model(RequiredLimitQuery), **endpoint_kwargs
        )
        @view
        def on_get(self, req, resp):
            resp.media = {"msg": "pong"}

    app = backend_app(backend)

    app.add_route("/ping", Ping())
    spec.register(app)

    response = falcon_testing.TestClient(app).simulate_get("/ping")

    assert response.status_code == expected_status_code


@pytest.mark.parametrize("backend", FALCON_BACKEND_PARAMS)
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
def test_falcon_model_adapter_doc_pages(
    backend,
    model_case,
    api_kwargs,
    expected_doc_pages,
):
    spec = SpecTree(backend, model_adapter=model_case.adapter, **api_kwargs)

    view = backend_view(backend)

    class Ping:
        @spec.validate()
        @view
        def on_get(self, req, resp):
            resp.media = {"msg": "pong"}

    app = backend_app(backend)

    app.add_route("/ping", Ping())
    spec.register(app)
    client = falcon_testing.TestClient(app)

    assert client.simulate_get("/apidoc/openapi.json").json == spec.spec
    for doc_page in expected_doc_pages:
        assert client.simulate_get(f"/apidoc/{doc_page}").status_code == HTTPStatus.OK
