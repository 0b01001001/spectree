from random import randint

import pytest
from flask import Flask, jsonify, request
from flask.views import MethodView

from spectree import Response, SpecTree

from .common import JSON, Cookies, Headers, Order, Query, Resp, StrDict, api_tag

# import tests to execute
from .flask_imports import *  # NOQA


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
        json=JSON,  # resp is missing completely
    )
    def post(self, json: JSON):
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
