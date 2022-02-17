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


def inner_register_func():
    @app.route("/api/user/{name}/address/{address_id}")
    @api.validate(
        query=Query,
        path_parameter_descriptions={
            "name": "The name that uniquely identifies the user.",
            "non-existent-param": "description",
        },
    )
    def user_address(request):
        return None


inner_register_func()
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


@pytest.fixture
def test_client_and_api(request):
    api_args = ["starlette"]
    api_kwargs = {}
    endpoint_kwargs = {
        "headers": Headers,
        "resp": Response(HTTP_200=StrDict),
        "tags": ["test", "health"],
    }
    if hasattr(request, "param"):
        api_args.extend(request.param.get("api_args", ()))
        api_kwargs.update(request.param.get("api_kwargs", {}))
        endpoint_kwargs.update(request.param.get("endpoint_kwargs", {}))

    api = SpecTree(*api_args, **api_kwargs)

    class Ping(HTTPEndpoint):
        name = "Ping"

        @api.validate(**endpoint_kwargs)
        def get(self, request):
            """summary

            description"""
            return JSONResponse({"msg": "pong"})

    app = Starlette(routes=[Route("/ping", Ping)])
    api.register(app)

    with TestClient(app) as client:
        yield client, api


@pytest.mark.parametrize(
    "test_client_and_api, expected_status_code",
    [
        pytest.param(
            {"api_kwargs": {}, "endpoint_kwargs": {}},
            422,
            id="default-global-status-without-override",
        ),
        pytest.param(
            {"api_kwargs": {}, "endpoint_kwargs": {"validation_error_status": 400}},
            400,
            id="default-global-status-with-override",
        ),
        pytest.param(
            {"api_kwargs": {"validation_error_status": 418}, "endpoint_kwargs": {}},
            418,
            id="overridden-global-status-without-override",
        ),
        pytest.param(
            {
                "api_kwargs": {"validation_error_status": 400},
                "endpoint_kwargs": {"validation_error_status": 418},
            },
            418,
            id="overridden-global-status-with-override",
        ),
    ],
    indirect=["test_client_and_api"],
)
def test_validation_error_response_status_code(
    test_client_and_api, expected_status_code
):
    app_client, _ = test_client_and_api

    resp = app_client.get("/ping")

    assert resp.status_code == expected_status_code


@pytest.mark.parametrize(
    "test_client_and_api, expected_doc_pages",
    [
        pytest.param({}, ["redoc", "swagger"], id="default-page-templates"),
        pytest.param(
            {"api_kwargs": {"page_templates": {"custom_page": "{spec_url}"}}},
            ["custom_page"],
            id="custom-page-templates",
        ),
    ],
    indirect=["test_client_and_api"],
)
def test_flask_doc(test_client_and_api, expected_doc_pages):
    client, api = test_client_and_api

    resp = client.get("/apidoc/openapi.json")
    assert resp.json() == api.spec

    for doc_page in expected_doc_pages:
        resp = client.get(f"/apidoc/{doc_page}")
        assert resp.status_code == 200
