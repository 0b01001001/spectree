import importlib
from contextlib import AsyncExitStack
from dataclasses import dataclass
from http import HTTPStatus
from typing import Any, Union

from starlette.applications import Starlette
from starlette.endpoints import HTTPEndpoint
from starlette.responses import JSONResponse, Response as StarletteResponse
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles
from starlette.testclient import TestClient

from spectree import Response, SpecTree
from spectree.plugins.starlette_plugin import SpecTreeStarletteResponse
from tests.common import (
    UserXmlData,
    api_tag,
    instance_name_after_handler as method_handler,
    validation_error_handler as before_handler,
    validation_pass_handler as after_handler,
)
from tests.common_dataclass import (
    Cookies,
    FormPayload,
    Item,
    Payload,
    Query,
    RequiredLimitQuery,
    Resp,
    RespObject,
    ReturnCase,
)

STARLETTE_USER = "starlette"


@dataclass(frozen=True)
class StarletteAdapterApp:
    client: TestClient
    spec: SpecTree
    create_item: Any
    endpoint_post: Any


def _response(model_case, value: Any) -> StarletteResponse:
    return StarletteResponse(
        model_case.adapter.dump_json(value),
        media_type="application/json",
    )


def build_starlette_adapter_app(model_case) -> StarletteAdapterApp:  # noqa: PLR0915
    pydantic_only = model_case.name == "pydantic"
    headers_model = None
    if pydantic_only:
        headers_model = importlib.import_module("tests.common_pydantic").Headers

    spec = SpecTree(
        "starlette",
        before=before_handler,
        after=after_handler,
        annotations=True,
        model_adapter=model_case.adapter,
    )

    class Ping(HTTPEndpoint):
        name = "Ping"

        @spec.validate(
            headers=headers_model,
            resp=Response(
                HTTP_202=model_case.get_model(dict[str, str], name="StrDict")
            ),
            tags=["test", "health"],
            after=method_handler,
        )
        def get(self, request):
            """summary

            description"""
            return JSONResponse({"msg": "pong"}, status_code=HTTPStatus.ACCEPTED)

    @spec.validate(form=model_case.get_model(FormPayload))
    async def file_upload(request, form: model_case.get_model(FormPayload)):
        assert form.file
        async with AsyncExitStack() as stack:
            stack.push_async_callback(form.file.close)
            content = await form.file.read()
            other = (
                form.other.decode("utf-8")
                if isinstance(form.other, bytes)
                else form.other
            )
            return JSONResponse({"file": content.decode("utf-8"), "other": other})

    @spec.validate(
        query=model_case.get_model(Query),
        json=model_case.get_model(Payload),
        cookies=model_case.get_model(Cookies),
        resp=Response(HTTP_200=model_case.get_model(Resp), HTTP_401=None),
        tags=[api_tag, "test"],
    )
    async def user_score(
        request,
        json: model_case.get_model(Payload),
        query: model_case.get_model(Query),
        cookies: model_case.get_model(Cookies),
    ):
        assert cookies.pub == request.cookies["pub"] == "abcdefg"
        return JSONResponse(
            {
                "name": json.name,
                "score": sorted([json.limit, query.order], reverse=bool(query.order)),
            }
        )

    @spec.validate(
        resp=Response(HTTP_200=model_case.get_model(Resp), HTTP_401=None),
        tags=[api_tag, "test"],
    )
    async def user_score_annotated(
        request,
        query: model_case.get_model(Query),
        json: model_case.get_model(Payload),
        cookies: model_case.get_model(Cookies),
    ):
        assert cookies.pub == request.cookies["pub"] == "abcdefg"
        return JSONResponse(
            {
                "name": json.name,
                "score": sorted([json.limit, query.order], reverse=bool(query.order)),
            }
        )

    @spec.validate(
        query=model_case.get_model(Query),
        json=model_case.get_model(Payload),
        cookies=model_case.get_model(Cookies),
        resp=Response(HTTP_200=model_case.get_model(Resp), HTTP_401=None),
        tags=[api_tag, "test"],
        skip_validation=True,
    )
    async def user_score_skip(request):
        response_format = request.query_params.get("response_format")
        payload = await request.json()
        score = sorted(
            [payload.get("limit"), int(request.query_params.get("order"))],
            reverse=bool(int(request.query_params.get("order"))),
        )
        assert request.cookies["pub"] == "abcdefg"
        if response_format == "json":
            return JSONResponse({"name": payload.get("name"), "x_score": score})
        return StarletteResponse(
            UserXmlData(name=payload.get("name"), score=score).dump_xml(),
            media_type="text/xml",
        )

    @spec.validate(
        query=model_case.get_model(Query),
        json=model_case.get_model(Payload),
        cookies=model_case.get_model(Cookies),
        resp=Response(HTTP_200=model_case.get_model(Resp), HTTP_401=None),
        tags=[api_tag, "test"],
    )
    async def user_score_model(request):
        assert request.context.cookies.pub == request.cookies["pub"] == "abcdefg"
        return SpecTreeStarletteResponse(
            model_case.validate_obj(
                model_case.get_model(Resp),
                {
                    "name": request.context.json.name,
                    "score": sorted(
                        [request.context.json.limit, request.context.query.order],
                        reverse=bool(request.context.query.order),
                    ),
                },
            ),
        )

    @spec.validate(resp=Response(HTTP_200=None))
    async def no_response(
        request,
        json: model_case.get_model(dict[str, str], name="StrDict"),
    ):
        return JSONResponse({})

    @spec.validate()
    async def list_json(request, json: model_case.get_model(list[Payload])):
        return JSONResponse({})

    @spec.validate(
        resp=Response(HTTP_200=model_case.list_of(model_case.get_model(Payload)))
    )
    async def return_list(request):
        data = [
            {"name": "user1", "limit": 1},
            {"name": "user2", "limit": 2},
        ]
        if bool(int(request.query_params.get("pre_serialize", 0))):
            return JSONResponse(data)
        return _response(
            model_case,
            model_case.validate_obj(model_case.get_model(list[Payload]), data),
        )

    @spec.validate(
        resp=Response(
            HTTP_200=model_case.get_model(
                Union[Payload, list[int]],
                name="RootPayload",
            )
        )
    )
    async def return_root(request):
        return_case = request.query_params.get(
            "return_case",
            ReturnCase.ROOT_MODEL.value,
        )
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
        return _response(model_case, response_cases[return_case])

    @spec.validate()
    async def return_model(request):
        return_case = request.query_params.get(
            "return_case",
            ReturnCase.MODEL.value,
        )
        payload_data = {"name": "user1", "limit": 1}
        response_cases = {
            ReturnCase.PAYLOAD.value: payload_data,
            ReturnCase.MODEL.value: model_case.validate_obj(
                model_case.get_model(Payload),
                payload_data,
            ),
            ReturnCase.RAW_LIST.value: [1, 2, 3, 4],
            ReturnCase.MODEL_LIST.value: [
                model_case.validate_obj(model_case.get_model(Payload), payload_data)
            ],
        }
        return _response(model_case, response_cases[return_case])

    @spec.validate(
        resp=Response(HTTP_200=model_case.list_of(model_case.get_model(Item)))
    )
    async def create_item(
        request,
        query: model_case.get_model(RequiredLimitQuery),
        json: model_case.get_model(Payload),
    ):
        return JSONResponse([{"name": json.name, "limit": query.limit}])

    class ItemsEndpoint(HTTPEndpoint):
        @spec.validate(
            resp=Response(HTTP_200=model_case.list_of(model_case.get_model(Item)))
        )
        async def post(
            self,
            request,
            query: model_case.get_model(RequiredLimitQuery),
            json: model_case.get_model(Payload),
        ):
            return JSONResponse([{"name": json.name, "limit": query.limit}])

    if pydantic_only:
        common_pydantic = importlib.import_module("tests.common_pydantic")
        CustomError = common_pydantic.CustomError
        OptionalAliasResp = common_pydantic.OptionalAliasResp
        RespFromAttrs = common_pydantic.RespFromAttrs

        @spec.validate(resp=Response(HTTP_200=OptionalAliasResp))
        async def return_optional_alias(request):
            return JSONResponse({"schema": "test"})

        @spec.validate(resp=Response(HTTP_200=CustomError))
        async def custom_error(request, json: CustomError):
            return JSONResponse({"foo": "bar"})

        @spec.validate(
            resp=Response(HTTP_200=RespFromAttrs),
            force_resp_serialize=True,
        )
        async def force_serialize(request):
            return SpecTreeStarletteResponse(
                RespObject(name=STARLETTE_USER, score=[1, 2, 3], comment="hello")
            )

    api_routes = [
        Mount(
            "/user",
            routes=[Route("/{name}", user_score, methods=["POST"])],
        ),
        Mount(
            "/user_annotated",
            routes=[
                Route("/{name}", user_score_annotated, methods=["POST"]),
            ],
        ),
        Mount(
            "/user_skip",
            routes=[Route("/{name}", user_score_skip, methods=["POST"])],
        ),
        Mount(
            "/user_model",
            routes=[Route("/{name}", user_score_model, methods=["POST"])],
        ),
        Route("/no_response", no_response, methods=["POST", "GET"]),
        Route("/file_upload", file_upload, methods=["POST"]),
        Route("/list_json", list_json, methods=["POST"]),
        Route("/return_list", return_list, methods=["GET"]),
        Route("/return_root", return_root, methods=["GET"]),
        Route("/return_model", return_model, methods=["GET"]),
        Route("/items", create_item, methods=["POST"]),
        Route("/view-items", ItemsEndpoint),
    ]
    if pydantic_only:
        api_routes.extend(
            [
                Route("/return_optional_alias", return_optional_alias, methods=["GET"]),
                Route("/custom_error", custom_error, methods=["POST"]),
                Route("/force_serialize", force_serialize, methods=["GET"]),
            ]
        )

    app = Starlette(
        routes=[
            Route("/ping", Ping),
            Mount("/api", routes=api_routes),
            Mount("/static", app=StaticFiles(directory="docs"), name="static"),
        ]
    )

    def user_address(request):
        return None

    user_address.__annotations__ = {
        "query": model_case.get_model(Query),
    }
    user_address = spec.validate(
        path_parameter_descriptions={
            "name": "The name that uniquely identifies the user.",
            "non-existent-param": "description",
        }
    )(user_address)
    app.routes.append(Route("/api/user/{name}/address/{address_id}", user_address))

    spec.register(app)

    return StarletteAdapterApp(
        client=TestClient(app),
        spec=spec,
        create_item=create_item,
        endpoint_post=ItemsEndpoint.post,
    )
