from random import randint

import pytest
from flask import Blueprint, Flask, jsonify, request

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
    StrDict,
    api_tag,
    get_paths,
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
@api.validate(headers=Headers, resp=Response(HTTP_200=StrDict), tags=["test", "health"])
def ping():
    """summary

    description"""
    return jsonify(msg="pong")


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
    score = [randint(0, request.context.json.limit) for _ in range(5)]
    score.sort(reverse=True if request.context.query.order == Order.desc else False)
    assert request.context.cookies.pub == "abcdefg"
    assert request.cookies["pub"] == "abcdefg"
    return jsonify(name=request.context.json.name, x_score=score)


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
    score.sort(reverse=True if request.context.query.order == Order.desc else False)
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


@app.route("/api/list_json", methods=["POST"])
@api.validate(
    json=ListJSON,
)
def list_json():
    return {}


api.register(app)

flask_app = Flask(__name__)
flask_app.register_blueprint(app)
with flask_app.app_context():
    api.spec


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
    assert resp.status_code == 200
    assert resp.json == {"msg": "pong"}
    assert resp.headers.get("X-Error") is None
    assert resp.headers.get("X-Validation") == "Pass"


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
        api.spec
    api.register(app)

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
