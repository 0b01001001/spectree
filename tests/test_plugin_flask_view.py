import json
from random import randint

import pytest
from flask import Flask, jsonify, request
from flask.views import MethodView

from spectree import Response, SpecTree

from .common import JSON, Cookies, Headers, Query, Resp, StrDict, api_tag


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
        score.sort(reverse=query.order)
        assert cookies.pub == "abcdefg"
        assert request.cookies["pub"] == "abcdefg"
        return jsonify(name=json.name, score=score)


app.add_url_rule("/ping", view_func=Ping.as_view("ping"))
app.add_url_rule("/api/user/<name>", view_func=User.as_view("user"), methods=["POST"])
app.add_url_rule(
    "/api/user_annotated/<name>",
    view_func=UserAnnotated.as_view("user_annotated"),
    methods=["POST"],
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


class TestFlaskValidationErrorResponseStatus:
    @pytest.fixture
    def app_client(self, request):
        api_kwargs = {}
        if request.param["global_validation_error_status"]:
            api_kwargs["validation_error_status"] = request.param[
                "global_validation_error_status"
            ]
        api = SpecTree("flask", **api_kwargs)
        app = Flask(__name__)
        app.config["TESTING"] = True

        class Ping(MethodView):
            @api.validate(
                headers=Headers,
                resp=Response(HTTP_200=StrDict),
                tags=["test", "health"],
                validation_error_status=request.param[
                    "validation_error_status_override"
                ],
            )
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

        with app.test_client() as client:
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


def test_flask_doc(client):
    resp = client.get("/apidoc/openapi.json")
    assert resp.json == api.spec

    resp = client.get("/apidoc/redoc")
    assert resp.status_code == 200

    resp = client.get("/apidoc/swagger")
    assert resp.status_code == 200
