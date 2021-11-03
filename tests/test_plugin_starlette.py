from random import randint

import pytest
from starlette.applications import Starlette
from starlette.endpoints import HTTPEndpoint
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles
from starlette.testclient import TestClient

from spectree import Response, SpecTree

from .common import JSON, Cookies, Headers, Query, Resp, StrDict, api_tag


def before_handler(req, resp, err, instance):
    if err:
        resp.headers["X-Error"] = "Validation Error"


def after_handler(req, resp, err, instance):
    resp.headers["X-Validation"] = "Pass"


def method_handler(req, resp, err, instance):
    resp.headers["X-Name"] = instance.name


api = SpecTree(
    "starlette", before=before_handler, after=after_handler, annotations=True
)


class Ping(HTTPEndpoint):
    name = "Ping"

    @api.validate(
        headers=Headers,
        resp=Response(HTTP_200=StrDict),
        tags=["test", "health"],
        after=method_handler,
    )
    def get(self, request):
        """summary

        description"""
        return JSONResponse({"msg": "pong"})


@api.validate(
    query=Query,
    json=JSON,
    cookies=Cookies,
    resp=Response(HTTP_200=Resp, HTTP_401=None),
    tags=[api_tag, "test"],
)
async def user_score(request):
    score = [randint(0, request.context.json.limit) for _ in range(5)]
    score.sort(reverse=request.context.query.order)
    assert request.context.cookies.pub == "abcdefg"
    assert request.cookies["pub"] == "abcdefg"
    return JSONResponse({"name": request.context.json.name, "score": score})


@api.validate(
    resp=Response(HTTP_200=Resp, HTTP_401=None),
    tags=[api_tag, "test"],
)
async def user_score_annotated(request, query: Query, json: JSON, cookies: Cookies):
    score = [randint(0, json.limit) for _ in range(5)]
    score.sort(reverse=query.order)
    assert cookies.pub == "abcdefg"
    assert request.cookies["pub"] == "abcdefg"
    return JSONResponse({"name": json.name, "score": score})


app = Starlette(
    routes=[
        Route("/ping", Ping),
        Mount(
            "/api",
            routes=[
                Mount(
                    "/user",
                    routes=[
                        Route("/{name}", user_score, methods=["POST"]),
                    ],
                ),
                Mount(
                    "/user_annotated",
                    routes=[
                        Route("/{name}", user_score_annotated, methods=["POST"]),
                    ],
                ),
            ],
        ),
        Mount("/static", app=StaticFiles(directory="docs"), name="static"),
    ]
)
api.register(app)


@pytest.fixture
def client():
    with TestClient(app) as client:
        yield client


def test_starlette_validate(client):
    resp = client.get("/ping")
    assert resp.status_code == 422
    assert resp.headers.get("X-Error") == "Validation Error", resp.headers

    resp = client.get("/ping", headers={"lang": "en-US"})
    assert resp.json() == {"msg": "pong"}
    assert resp.headers.get("X-Error") is None
    assert resp.headers.get("X-Name") == "Ping"
    assert resp.headers.get("X-Validation") is None

    for fragment in ("user", "user_annotated"):
        resp = client.post(f"/api/{fragment}/starlette")
        assert resp.status_code == 422
        assert resp.headers.get("X-Error") == "Validation Error"

        resp = client.post(
            f"/api/{fragment}/starlette?order=1",
            json=dict(name="starlette", limit=10),
            cookies=dict(pub="abcdefg"),
        )
        resp_body = resp.json()
        assert resp_body["name"] == "starlette"
        assert resp_body["score"] == sorted(resp_body["score"], reverse=True)
        assert resp.headers.get("X-Validation") == "Pass"

        resp = client.post(
            f"/api/{fragment}/starlette?order=0",
            json=dict(name="starlette", limit=10),
            cookies=dict(pub="abcdefg"),
        )
        resp_body = resp.json()
        assert resp_body["name"] == "starlette"
        assert resp_body["score"] == sorted(resp_body["score"], reverse=False)
        assert resp.headers.get("X-Validation") == "Pass"


class TestStarletteValidationErrorResponseStatus:
    @pytest.fixture
    def app_client(self, request):
        api_kwargs = {}
        if request.param["global_validation_error_status"]:
            api_kwargs["validation_error_status"] = request.param[
                "global_validation_error_status"
            ]
        api = SpecTree("starlette", **api_kwargs)

        class Ping(HTTPEndpoint):
            name = "Ping"

            @api.validate(
                headers=Headers,
                resp=Response(HTTP_200=StrDict),
                tags=["test", "health"],
                after=method_handler,
                validation_error_status=request.param[
                    "validation_error_status_override"
                ],
            )
            def get(self, request):
                """summary
                description"""
                return JSONResponse({"msg": "pong"})

        app = Starlette(routes=[Route("/ping", Ping)])
        api.register(app)

        with TestClient(app) as client:
            yield client

    @pytest.mark.parametrize(
        "app_client, expected_status_code",
        [
            pytest.param(
                {
                    "global_validation_error_status": None,
                    "validation_error_status_override": None,
                },
                422,
                id="default-global-status-without-override",
            ),
            pytest.param(
                {
                    "global_validation_error_status": None,
                    "validation_error_status_override": 400,
                },
                400,
                id="default-global-status-with-override",
            ),
            pytest.param(
                {
                    "global_validation_error_status": 418,
                    "validation_error_status_override": None,
                },
                418,
                id="overridden-global-status-without-override",
            ),
            pytest.param(
                {
                    "global_validation_error_status": 400,
                    "validation_error_status_override": 418,
                },
                418,
                id="overridden-global-status-with-override",
            ),
        ],
        indirect=["app_client"],
    )
    def test_validation_error_response_status_code(
        self, app_client, expected_status_code
    ):
        resp = app_client.get("/ping")

        assert resp.status_code == expected_status_code


def test_starlette_doc(client):
    resp = client.get("/apidoc/openapi.json")
    assert resp.json() == api.spec

    resp = client.get("/apidoc/redoc")
    assert resp.status_code == 200

    resp = client.get("/apidoc/swagger")
    assert resp.status_code == 200
