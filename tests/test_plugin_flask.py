from random import randint
from typing import List

import pytest
from flask import Flask, jsonify, make_response, request

from spectree import Response, SpecTree

from .common import (
    JSON,
    SECURITY_SCHEMAS,
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
app.config["DEBUG"] = True

api_secure = SpecTree("flask", security_schemes=SECURITY_SCHEMAS)
app_secure = Flask(__name__)
app_secure.config["TESTING"] = True
app_secure.config["DEBUG"] = True

api_global_secure = SpecTree(
    "flask", security_schemes=SECURITY_SCHEMAS, security={"auth_apiKey": []}
)
app_global_secure = Flask(__name__)
app_global_secure.config["TESTING"] = True
app_global_secure.config["DEBUG"] = True


@app.route("/ping")
@api.validate(resp=Response(HTTP_202=StrDict), tags=["test", "health"])
def ping(headers: Headers):
    """summary

    description"""
    return jsonify(msg="pong"), 202, headers


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
    score.sort(reverse=(request.context.query.order == Order.desc))
    assert request.context.cookies.pub == "abcdefg"
    assert request.cookies["pub"] == "abcdefg"
    return jsonify(name=data_src.name, score=score)


@app.route("/api/user_annotated/<name>", methods=["POST"])
@api.validate(
    resp=Response(HTTP_200=Resp, HTTP_401=None),
    tags=[api_tag, "test"],
    after=api_after_handler,
)
def user_score_annotated(name, query: Query, json: JSON, form: Form, cookies: Cookies):
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
    score.sort(reverse=(int(request.args.get("order")) == Order.desc))
    assert request.cookies["pub"] == "abcdefg"
    if response_format == "json":
        return jsonify(name=name, x_score=score)
    else:
        return app.response_class(
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
    score.sort(reverse=(request.context.query.order == Order.desc))
    assert request.context.cookies.pub == "abcdefg"
    assert request.cookies["pub"] == "abcdefg"
    return Resp(name=request.context.json.name, score=score), 200


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
def json_list():
    return {}


@app.route("/api/set_cookies", methods=["GET"])
@api.validate(resp=Response(HTTP_200=StrDict))
def set_cookies():
    # related to GitHub issue #415
    resp = make_response(jsonify(msg="ping"))
    resp.set_cookie("foo", "hello")
    resp.set_cookie("bar", "world")
    return resp


@app.route("/api/query_list", methods=["GET"])
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
def return_optional_alias_resp():
    return {"schema": "test"}


@app.route("/api/custom_error", methods=["POST"])
@api.validate(resp=Response(HTTP_200=CustomError))
def custom_error(json: CustomError):
    return {"foo": "bar"}


# INFO: ensures that spec is calculated and cached _after_ registering
# view functions for validations. This enables tests to access `api.spec`
# without app_context.
with app.app_context():
    _ = api.spec
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
    app.config["DEBUG"] = True

    @app.route("/ping")
    @api.validate(**endpoint_kwargs)
    def ping():
        """summary

        description"""
        return jsonify(msg="pong")

    # INFO: ensures that spec is calculated and cached _after_ registering
    # view functions for validations. This enables tests to access `api.spec`
    # without app_context.
    with app.app_context():
        _ = api.spec
    api.register(app)

    with app.test_client() as test_client:
        yield test_client, api


"""
Secure param check
"""


@app_secure.route("/no-secure-ping", methods=["GET"])
@api_secure.validate(
    resp=Response(HTTP_200=StrDict),
)
def no_secure_ping():
    """
    No auth type is set
    """
    return jsonify(msg="pong")


@app_secure.route("/apiKey-ping", methods=["GET"])
@api_secure.validate(
    resp=Response(HTTP_200=StrDict),
    security={"auth_apiKey": []},
)
def apiKey_ping():
    """
    apiKey auth type
    """
    return jsonify(msg="pong")


@app_secure.route("/apiKey-BasicAuth-ping", methods=["GET"])
@api_secure.validate(
    resp=Response(HTTP_200=StrDict),
    security={"auth_apiKey": [], "auth_BasicAuth": []},
)
def apiKey_BasicAuth_ping():
    """
    Multiple auth types is set - apiKey and BasicAuth
    """
    return jsonify(msg="pong")


@app_secure.route("/BasicAuth-ping", methods=["GET"])
@api_secure.validate(
    resp=Response(HTTP_200=StrDict),
    security={"auth_BasicAuth": []},
)
def BasicAuth_ping():
    """
    BasicAuth auth type
    """
    return jsonify(msg="pong")


@app_secure.route("/oauth2-flows-ping", methods=["GET"])
@api_secure.validate(
    resp=Response(HTTP_200=StrDict),
    security={"auth_oauth2": ["admin", "read"]},
)
def oauth_two_ping():
    """
    oauth2 auth type with flow
    """
    return jsonify(msg="pong")


with app_secure.app_context():
    _ = api_secure.spec

api_secure.register(app_secure)


"""
Global secure params check
"""


@app_global_secure.route("/global-secure-ping", methods=["GET"])
@api_global_secure.validate(
    resp=Response(HTTP_200=StrDict),
)
def global_auth_ping():
    """
    global auth type
    """
    return jsonify(msg="pong")


@app_global_secure.route("/no-secure-override-ping", methods=["GET"])
@api_global_secure.validate(
    security={},
    resp=Response(HTTP_200=StrDict),
)
def global_no_secure_ping():
    """
    No auth type is set to override
    """
    return jsonify(msg="pong")


@app_global_secure.route("/oauth2-flows-override-ping", methods=["GET"])
@api_global_secure.validate(
    security={"auth_oauth2": ["admin", "read"]},
    resp=Response(HTTP_200=StrDict),
)
def global_oauth_two_ping():
    """
    oauth2 auth type with flow to override
    """
    return jsonify(msg="pong")


@app_global_secure.route("/security_and", methods=["GET"])
@api_global_secure.validate(
    security={"auth_apiKey": [], "auth_apiKey_backup": []},
    resp=Response(HTTP_200=StrDict),
)
def global_security_and():
    """
    global auth AND
    """
    return jsonify(msg="pong")


@app_global_secure.route("/security_or", methods=["GET"])
@api_global_secure.validate(
    security=[{"auth_apiKey": []}, {"auth_apiKey_backup": []}],
    resp=Response(HTTP_200=StrDict),
)
def global_security_or():
    """
    global auth OR
    """
    return jsonify(msg="pong")


with app_global_secure.app_context():
    _ = api_global_secure.spec

api_global_secure.register(app_global_secure)
