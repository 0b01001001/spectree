import json
from random import randint

import pytest
from flask import Flask, jsonify, request
from flask.views import MethodView

from spectree import Response, SpecTree

from .common import JSON, Cookies, Headers, Order, Query, Resp, StrDict, api_tag


def before_handler(req, resp, err, _):
    if err:
        resp.headers["X-Error"] = "Validation Error"


def after_handler(req, resp, err, _):
    resp.headers["X-Validation"] = "Pass"


def api_after_handler(req, resp, err, _):
    resp.headers["X-API"] = "OK"


api = SpecTree("flask", before=before_handler, after=after_handler, annotations=True)
app = Flask(__name__)
app.config["TESTING"] = True


class Ping(MethodView):
    @api.validate(
        headers=Headers, resp=Response(HTTP_200=StrDict), tags=["test", "health"]
    )
    def get(self):
        """summary

        description"""
        return jsonify(msg="pong")


class User(MethodView):
    @api.validate(
        query=Query,
        json=JSON,
        cookies=Cookies,
        resp=Response(HTTP_200=Resp, HTTP_401=None),
        tags=[api_tag, "test"],
        after=api_after_handler,
    )
    def post(self, name):
        score = [randint(0, request.context.json.limit) for _ in range(5)]
        score.sort(reverse=request.context.query.order)
        assert request.context.cookies.pub == "abcdefg"
        assert request.cookies["pub"] == "abcdefg"
        return jsonify(name=request.context.json.name, score=score)


class UserAnnotated(MethodView):
    @api.validate(
        resp=Response(HTTP_200=Resp, HTTP_401=None),
        tags=[api_tag, "test"],
        after=api_after_handler,
    )
    def post(self, name, query: Query, json: JSON, cookies: Cookies):
        score = [randint(0, json.limit) for _ in range(5)]
        score.sort(reverse=True if query.order == Order.desc else False)
        assert cookies.pub == "abcdefg"
        assert request.cookies["pub"] == "abcdefg"
        return jsonify(name=json.name, score=score)


class UserSkip(MethodView):
    @api.validate(
        query=Query,
        json=JSON,
        cookies=Cookies,
        resp=Response(HTTP_200=Resp, HTTP_401=None),
        tags=[api_tag, "test"],
        after=api_after_handler,
        skip_validation=True,
    )
    def post(self, name, query: Query, json: JSON, cookies: Cookies):
        score = [randint(0, request.context.json.limit) for _ in range(5)]
        score.sort(reverse=True if request.context.query.order == Order.desc else False)
        assert request.context.cookies.pub == "abcdefg"
        assert request.cookies["pub"] == "abcdefg"
        return jsonify(name=request.context.json.name, x_score=score)


class UserModel(MethodView):
    @api.validate(
        query=Query,
        json=JSON,
        cookies=Cookies,
        resp=Response(HTTP_200=Resp, HTTP_401=None),
        tags=[api_tag, "test"],
        after=api_after_handler,
    )
    def post(self, name, query: Query, json: JSON, cookies: Cookies):
        score = [randint(0, request.context.json.limit) for _ in range(5)]
        score.sort(reverse=True if request.context.query.order == Order.desc else False)
        assert request.context.cookies.pub == "abcdefg"
        assert request.cookies["pub"] == "abcdefg"
        return Resp(name=request.context.json.name, score=score)


class UserAddress(MethodView):
    @api.validate(
        query=Query,
        path_parameter_descriptions={
            "name": "The name that uniquely identifies the user.",
            "non-existent-param": "description",
        },
    )
    def get(self, name, address_id):
        return None


class NoResponseView(MethodView):
    @api.validate(
        resp=Response(HTTP_200=None),  # response is None
    )
    def get(self):
        return {}

    @api.validate(
        json=Query,  # resp is missing completely
    )
    def post(self, json: Query):
        return {}


app.add_url_rule("/ping", view_func=Ping.as_view("ping"))
app.add_url_rule("/api/user/<name>", view_func=User.as_view("user"), methods=["POST"])
app.add_url_rule(
    "/api/user_annotated/<name>",
    view_func=UserAnnotated.as_view("user_annotated"),
    methods=["POST"],
)
app.add_url_rule(
    "/api/user_skip/<name>",
    view_func=UserSkip.as_view("user_skip"),
    methods=["POST"],
)
app.add_url_rule(
    "/api/user_model/<name>",
    view_func=UserModel.as_view("user_model"),
    methods=["POST"],
)
app.add_url_rule(
    "/api/user/<name>/address/<address_id>",
    view_func=UserAddress.as_view("user_address"),
    methods=["GET"],
)
app.add_url_rule(
    "/api/no_response",
    view_func=NoResponseView.as_view("no_response_view"),
)

# INFO: ensures that spec is calculated and cached _after_ registering
# view functions for validations. This enables tests to access `api.spec`
# without app_context.
with app.app_context():
    api.spec


api.register(app)


@pytest.fixture
def client():
    with app.test_client() as client:
        yield client


def test_flask_validate(client):
    resp = client.get("/ping")
    assert resp.status_code == 422
    assert resp.headers.get("X-Error") == "Validation Error"

    resp = client.get("/ping", headers={"lang": "en-US"})
    assert resp.json == {"msg": "pong"}
    assert resp.headers.get("X-Error") is None
    assert resp.headers.get("X-Validation") == "Pass"

    resp = client.post("api/user/flask")
    assert resp.status_code == 422
    assert resp.headers.get("X-Error") == "Validation Error"

    client.set_cookie("flask", "pub", "abcdefg")
    for fragment in ("user", "user_annotated"):
        resp = client.post(
            f"/api/{fragment}/flask?order=1",
            data=json.dumps(dict(name="flask", limit=10)),
            content_type="application/json",
        )
        assert resp.status_code == 200, resp.json
        assert resp.headers.get("X-Validation") is None
        assert resp.headers.get("X-API") == "OK"
        assert resp.json["name"] == "flask"
        assert resp.json["score"] == sorted(resp.json["score"], reverse=True)

        resp = client.post(
            f"/api/{fragment}/flask?order=0",
            data=json.dumps(dict(name="flask", limit=10)),
            content_type="application/json",
        )
        assert resp.json["score"] == sorted(resp.json["score"], reverse=False)

        resp = client.post(
            f"/api/{fragment}/flask?order=0",
            data="name=flask&limit=10",
            content_type="application/x-www-form-urlencoded",
        )
        assert resp.json["score"] == sorted(resp.json["score"], reverse=False)

    resp = client.get("/api/no_response")
    assert resp.status_code == 200

    resp = client.post("/api/no_response", data={"order": 1})
    assert resp.status_code == 200


def test_flask_skip_validation(client):
    client.set_cookie("flask", "pub", "abcdefg")

    resp = client.post(
        "/api/user_skip/flask?order=1",
        data=json.dumps(dict(name="flask", limit=10)),
        content_type="application/json",
    )
    assert resp.status_code == 200, resp.json
    assert resp.headers.get("X-Validation") is None
    assert resp.headers.get("X-API") == "OK"
    assert resp.json["name"] == "flask"
    assert resp.json["x_score"] == sorted(resp.json["x_score"], reverse=True)


def test_flask_return_model(client):
    client.set_cookie("flask", "pub", "abcdefg")

    resp = client.post(
        "/api/user_model/flask?order=1",
        data=json.dumps(dict(name="flask", limit=10)),
        content_type="application/json",
    )
    assert resp.status_code == 200, resp.json
    assert resp.headers.get("X-Validation") is None
    assert resp.headers.get("X-API") == "OK"
    assert resp.json["name"] == "flask"
    assert resp.json["score"] == sorted(resp.json["score"], reverse=True)


@pytest.fixture
def test_client_and_api(request):
    api_args = ["flask"]
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
    app = Flask(__name__)
    app.config["TESTING"] = True

    class Ping(MethodView):
        @api.validate(**endpoint_kwargs)
        def get(self):
            """summary

            description"""
            return jsonify(msg="pong")

    app.add_url_rule("/ping", view_func=Ping.as_view("ping"))

    # INFO: ensures that spec is calculated and cached _after_ registering
    # view functions for validations. This enables tests to access `api.spec`
    # without app_context.
    with app.app_context():
        api.spec
    api.register(app)

    with app.test_client() as test_client:
        yield test_client, api


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
    assert resp.json == api.spec

    for doc_page in expected_doc_pages:
        resp = client.get(f"/apidoc/{doc_page}")
        assert resp.status_code == 200
