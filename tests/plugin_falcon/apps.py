import importlib
from dataclasses import dataclass
from functools import wraps
from typing import Any, Union

import falcon
import pytest
from falcon import testing as falcon_testing
from falcon.asgi import App as FalconASGIApp

from spectree import Response, SpecTree
from tests.common import (
    api_tag,
    instance_name_after_handler as after_handler,
    validation_error_handler as before_handler,
)
from tests.common_dataclass import (
    Cookies,
    FormPayload,
    Item,
    OptionalPayload,
    Payload,
    Query,
    Resp,
    RespObject,
    ReturnCase,
)

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
                file_content = None
                if form.file:
                    async with form.file.stream as stream:
                        file_content = await stream.read()
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
                    async with form.file.stream as stream:
                        async for chunk in stream:
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
                file_content = None
                if form.file:
                    with form.file.stream as stream:
                        file_content = stream.read()
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
