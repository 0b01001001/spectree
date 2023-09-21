from random import randint
from typing import List

import pytest
from flask import Flask, jsonify, make_response, request
from flask.views import MethodView

from spectree import Response, SpecTree

from .common import (
    JSON,
    Cookies,
    Form,
    FormFileUpload,
    Headers,
    ListJSON,
    Order,
    Query,
    Resp,
    RootResp,
    StrDict,
    UserXmlData,
    api_tag,
    get_root_resp_data,
)

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
        headers=Headers, resp=Response(HTTP_202=StrDict), tags=["test", "health"]
    )
    def get(self):
        """summary

        description"""
        return jsonify(msg="pong"), 202


class FileUploadView(MethodView):
    @api.validate(
        form=FormFileUpload,
    )
    def post(self, form: FormFileUpload):
        upload = form.file
        assert upload
        return {"content": upload.stream.read().decode("utf-8")}


class User(MethodView):
    @api.validate(
        query=Query,
        json=JSON,
        form=Form,
        cookies=Cookies,
        resp=Response(HTTP_200=Resp, HTTP_401=None),
        tags=[api_tag, "test"],
        after=api_after_handler,
    )
    def post(self, name):
        data_src = request.context.json or request.context.form
        score = [randint(0, int(data_src.limit)) for _ in range(5)]
        score.sort(reverse=request.context.query.order)
        assert request.context.cookies.pub == "abcdefg"
        assert request.cookies["pub"] == "abcdefg"
        return jsonify(name=data_src.name, score=score)


class UserAnnotated(MethodView):
    @api.validate(
        resp=Response(HTTP_200=Resp, HTTP_401=None),
        tags=[api_tag, "test"],
        after=api_after_handler,
    )
    def post(self, name, query: Query, json: JSON, form: Form, cookies: Cookies):
        data_src = json or form
        score = [randint(0, int(data_src.limit)) for _ in range(5)]
        score.sort(reverse=True if query.order == Order.desc else False)
        assert cookies.pub == "abcdefg"
        assert request.cookies["pub"] == "abcdefg"
        return jsonify(name=data_src.name, score=score)


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
    def post(self, name, query: Query, json: JSON, form: Form, cookies: Cookies):
        response_format = request.args.get("response_format")
        assert response_format in ("json", "xml")
        data_src = json or form
        score = [randint(0, int(data_src.limit)) for _ in range(5)]
        score.sort(reverse=(query.order == Order.desc))
        assert cookies.pub == "abcdefg"
        assert request.cookies["pub"] == "abcdefg"
        if response_format == "json":
            return jsonify(name=request.context.json.name, x_score=score)
        else:
            return app.response_class(
                UserXmlData(name=request.context.json.name, score=score).dump_xml(),
                content_type="text/xml",
            )


class UserModel(MethodView):
    @api.validate(
        query=Query,
        json=JSON,
        cookies=Cookies,
        resp=Response(HTTP_200=Resp, HTTP_401=None),
        tags=[api_tag, "test"],
        after=api_after_handler,
    )
    def post(self, name, query: Query, json: JSON, form: Form, cookies: Cookies):
        data_src = json or form
        score = [randint(0, int(data_src.limit)) for _ in range(5)]
        score.sort(reverse=(query.order == Order.desc))
        assert cookies.pub == "abcdefg"
        assert request.cookies["pub"] == "abcdefg"
        return Resp(name=data_src.name, score=score)


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
        json=StrDict,  # resp is missing completely
    )
    def post(self, json: JSON):
        return {}


class ListJsonView(MethodView):
    @api.validate(
        json=ListJSON,
    )
    def post(self):
        return {}


class ReturnListView(MethodView):
    @api.validate(
        resp=Response(HTTP_200=List[JSON]),
    )
    def get(self):
        pre_serialize = bool(int(request.args.get("pre_serialize", default=0)))
        data = [JSON(name="user1", limit=1), JSON(name="user2", limit=2)]
        return [entry.dict() if pre_serialize else entry for entry in data]


class ReturnMakeResponseView(MethodView):
    @api.validate(
        json=JSON,
        resp=Response(HTTP_201=Resp),
    )
    def post(self):
        model_data = JSON(**request.json)
        response = make_response(
            Resp(name=model_data.name, score=[model_data.limit]).dict(), 201
        )
        return response

    @api.validate(
        query=JSON,
        resp=Response(HTTP_201=Resp),
    )
    def get(self):
        model_data = JSON(**request.args)
        response = make_response(
            Resp(name=model_data.name, score=[model_data.limit]).dict(), 201
        )
        return response


class ReturnRootView(MethodView):
    @api.validate(resp=Response(HTTP_200=RootResp))
    def get(self):
        return get_root_resp_data(
            pre_serialize=bool(int(request.args.get("pre_serialize", default=0))),
            return_what=request.args.get("return_what", default="RootResp"),
        )


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
app.add_url_rule(
    "/api/file_upload",
    view_func=FileUploadView.as_view("file_upload_view"),
)
app.add_url_rule(
    "/api/list_json",
    view_func=ListJsonView.as_view("list_json_view"),
)
app.add_url_rule(
    "/api/return_list",
    view_func=ReturnListView.as_view("return_list_view"),
)
app.add_url_rule(
    "/api/return_make_response",
    view_func=ReturnMakeResponseView.as_view("return_make_response"),
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
