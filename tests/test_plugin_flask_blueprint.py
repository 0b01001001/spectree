from random import randint
from typing import List

import flask
import pytest
from flask import Blueprint, Flask, jsonify, make_response, request

from spectree import Response, SpecTree

from .common import (
    JSON,
    Cookies,
    CustomError,
    Form,
    FormFileUpload,
    Headers,
    ListJSON,
    OptionalAliasResp,
    Order,
    Query,
    QueryList,
    Resp,
    RootResp,
    StrDict,
    UserXmlData,
    api_tag,
    get_paths,
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
app = Blueprint("test_blueprint", __name__)


@app.route("/ping")
@api.validate(headers=Headers, resp=Response(HTTP_202=StrDict), tags=["test", "health"])
def ping():
    """summary

    description"""
    return jsonify(msg="pong"), 202, request.context.headers.dict()


@app.route("/api/file_upload", methods=["POST"])
@api.validate(
    form=FormFileUpload,
)
def file_upload():
    upload = request.context.form.file
    assert upload
    return {"content": upload.stream.read().decode("utf-8")}


@app.route("/api/user/<name>", methods=["POST"])
@api.validate(
    query=Query,
    json=JSON,
    cookies=Cookies,
    form=Form,
    resp=Response(HTTP_200=Resp, HTTP_401=None),
    tags=[api_tag, "test"],
    after=api_after_handler,
)
def user_score(name):
    data_src = request.context.json or request.context.form
    score = [randint(0, int(data_src.limit)) for _ in range(5)]
    score.sort(reverse=request.context.query.order)
    assert request.context.cookies.pub == "abcdefg"
    assert request.cookies["pub"] == "abcdefg"
    return jsonify(name=data_src.name, score=score)


@app.route("/api/user_annotated/<name>", methods=["POST"])
@api.validate(
    resp=Response(HTTP_200=Resp, HTTP_401=None),
    tags=[api_tag, "test"],
    after=api_after_handler,
)
def user_score_annotated(name, query: Query, json: JSON, cookies: Cookies, form: Form):
    data_src = json or form
    score = [randint(0, int(data_src.limit)) for _ in range(5)]
    score.sort(reverse=(query.order == Order.desc))
    assert cookies.pub == "abcdefg"
    assert request.cookies["pub"] == "abcdefg"
    return jsonify(name=data_src.name, score=score)


@app.route("/api/user_skip/<name>", methods=["POST"])
@api.validate(
    query=Query,
    json=JSON,
    cookies=Cookies,
    resp=Response(HTTP_200=Resp, HTTP_401=None),
    tags=[api_tag, "test"],
    after=api_after_handler,
    skip_validation=True,
)
def user_score_skip_validation(name):
    response_format = request.args.get("response_format")
    assert response_format in ("json", "xml")
    json = request.get_json()
    score = [randint(0, json.get("limit")) for _ in range(5)]
    score.sort(reverse=int(request.args.get("order")) == Order.desc)
    assert request.cookies["pub"] == "abcdefg"
    if response_format == "json":
        return jsonify(name=name, x_score=score)
    else:
        return flask.Response(
            UserXmlData(name=name, score=score).dump_xml(),
            content_type="text/xml",
        )


@app.route("/api/user_model/<name>", methods=["POST"])
@api.validate(
    query=Query,
    json=JSON,
    cookies=Cookies,
    resp=Response(HTTP_200=Resp, HTTP_401=None),
    tags=[api_tag, "test"],
    after=api_after_handler,
)
def user_score_model(name):
    score = [randint(0, request.context.json.limit) for _ in range(5)]
    score.sort(reverse=request.context.query.order == Order.desc)
    assert request.context.cookies.pub == "abcdefg"
    assert request.cookies["pub"] == "abcdefg"
    return Resp(name=request.context.json.name, score=score)


@app.route("/api/user/<name>/address/<address_id>", methods=["GET"])
@api.validate(
    query=Query,
    path_parameter_descriptions={
        "name": "The name that uniquely identifies the user.",
        "non-existent-param": "description",
    },
)
def user_address(name, address_id):
    return None


@app.route("/api/no_response", methods=["GET", "POST"])
@api.validate(
    json=StrDict,
)
def no_response():
    return {}


@app.route("/api/set_cookies", methods=["GET"])
@api.validate(resp=Response(HTTP_200=StrDict))
def set_cookies():
    # related to GitHub issue #415
    resp = make_response(jsonify(msg="ping"))
    resp.set_cookie("foo", "hello")
    resp.set_cookie("bar", "world")
    return resp


@app.route("/api/list_json", methods=["POST"])
@api.validate(
    json=ListJSON,
)
def list_json():
    return {}


@app.route("/api/query_list")
@api.validate(query=QueryList)
def query_list():
    assert request.context.query.ids == [1, 2, 3]
    return {}


@app.route("/api/return_list", methods=["GET"])
@api.validate(resp=Response(HTTP_200=List[JSON]))
def return_list():
    pre_serialize = bool(int(request.args.get("pre_serialize", default=0)))
    data = [JSON(name="user1", limit=1), JSON(name="user2", limit=2)]
    return [entry.dict() if pre_serialize else entry for entry in data]


@app.route("/api/return_make_response", methods=["POST"])
@api.validate(json=JSON, headers=Headers, resp=Response(HTTP_201=Resp))
def return_make_response_post():
    model_data = request.context.json
    headers = request.context.headers
    response = make_response(
        Resp(name=model_data.name, score=[model_data.limit]).dict(), 201, headers
    )
    response.set_cookie(
        key="test_cookie",
        value=model_data.name,
        secure=True,
        httponly=True,
        samesite="Strict",
    )
    return response


@app.route("/api/return_make_response", methods=["GET"])
@api.validate(query=JSON, headers=Headers, resp=Response(HTTP_201=Resp))
def return_make_response_get():
    model_data = request.context.query
    headers = request.context.headers
    response = make_response(
        Resp(name=model_data.name, score=[model_data.limit]).dict(), 201, headers
    )
    response.set_cookie(
        key="test_cookie",
        value=model_data.name,
        secure=True,
        httponly=True,
        samesite="Strict",
    )
    return response


@app.route("/api/return_root", methods=["GET"])
@api.validate(resp=Response(HTTP_200=RootResp))
def return_root():
    return get_root_resp_data(
        pre_serialize=bool(int(request.args.get("pre_serialize", default=0))),
        return_what=request.args.get("return_what", default="RootResp"),
    )


@app.route("/api/return_optional_alias", methods=["GET"])
@api.validate(resp=Response(HTTP_200=OptionalAliasResp))
def return_optional_alias():
    return {"schema": "test"}


@app.route("/api/custom_error", methods=["POST"])
@api.validate(resp=Response(HTTP_200=CustomError))
def custom_error(json: CustomError):
    return {"foo": "bar"}


api.register(app)

flask_app = Flask(__name__)
flask_app.config["DEBUG"] = True
flask_app.config["TESTING"] = True
flask_app.register_blueprint(app)
with flask_app.app_context():
    _ = api.spec


@pytest.fixture
def client(request):
    parent_app = Flask(__name__)
    url_prefix = getattr(request, "param", None)
    parent_app.register_blueprint(app, url_prefix=url_prefix)
    with parent_app.test_client() as client:
        yield client


@pytest.mark.parametrize(
    ("client", "prefix"), [(None, ""), ("/prefix", "/prefix")], indirect=["client"]
)
def test_blueprint_prefix(client, prefix):
    resp = client.get(prefix + "/ping")
    assert resp.status_code == 422
    assert resp.headers.get("X-Error") == "Validation Error"

    resp = client.get(prefix + "/ping", headers={"lang": "en-US"})
    assert resp.status_code == 202, resp.text
    assert resp.json == {"msg": "pong"}
    assert resp.headers.get("X-Error") is None
    assert resp.headers.get("X-Validation") == "Pass"
    assert resp.headers.get("lang") == "en-US"


@pytest.fixture
def test_client_and_api(request):
    api_args = ["flask"]
    api_kwargs = {}
    endpoint_kwargs = {
        "headers": Headers,
        "resp": Response(HTTP_200=StrDict),
        "tags": ["test", "health"],
    }
    register_blueprint_kwargs = {}
    if hasattr(request, "param"):
        api_args.extend(request.param.get("api_args", ()))
        api_kwargs.update(request.param.get("api_kwargs", {}))
        endpoint_kwargs.update(request.param.get("endpoint_kwargs", {}))
        register_blueprint_kwargs.update(
            request.param.get("register_blueprint_kwargs", {})
        )

    api = SpecTree(*api_args, **api_kwargs)
    app = Blueprint("test_blueprint", __name__)

    @app.route("/ping")
    @api.validate(**endpoint_kwargs)
    def ping():
        """summary

        description"""
        return jsonify(msg="pong")

    api.register(app)

    flask_app = Flask(__name__)
    flask_app.register_blueprint(app, **register_blueprint_kwargs)

    with flask_app.app_context():
        _ = api.spec

    with flask_app.test_client() as test_client:
        yield test_client, api


@pytest.mark.parametrize(
    ("test_client_and_api", "prefix"),
    [
        ({"register_blueprint_kwargs": {}}, ""),
        ({"register_blueprint_kwargs": {"url_prefix": "/prefix"}}, "/prefix"),
    ],
    indirect=["test_client_and_api"],
)
def test_flask_doc_prefix(test_client_and_api, prefix):
    client, api = test_client_and_api

    resp = client.get(prefix + "/apidoc/openapi.json")
    assert resp.json == api.spec

    resp = client.get(prefix + "/apidoc/redoc/")
    assert resp.status_code == 200

    resp = client.get(prefix + "/apidoc/swagger/")
    assert resp.status_code == 200

    assert get_paths(api.spec) == [
        prefix + "/ping",
    ]
