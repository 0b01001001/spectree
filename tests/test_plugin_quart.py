from random import randint
from typing import List

import pytest
from quart import Quart, jsonify, request

from spectree import Response, SpecTree

from .common import (
    JSON,
    SECURITY_SCHEMAS,
    Cookies,
    CustomError,
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


def before_handler(req, resp, err, _):
    if err:
        resp.headers["X-Error"] = "Validation Error"


def after_handler(req, resp, err, _):
    resp.headers["X-Validation"] = "Pass"


def api_after_handler(req, resp, err, _):
    resp.headers["X-API"] = "OK"


api = SpecTree("quart", before=before_handler, after=after_handler, annotations=True)
app = Quart(__name__)
app.config["TESTING"] = True

api_secure = SpecTree("quart", security_schemes=SECURITY_SCHEMAS)
app_secure = Quart(__name__)
app_secure.config["TESTING"] = True

api_global_secure = SpecTree(
    "quart", security_schemes=SECURITY_SCHEMAS, security={"auth_apiKey": []}
)
app_global_secure = Quart(__name__)
app_global_secure.config["TESTING"] = True


@app.route("/ping")
@api.validate(headers=Headers, resp=Response(HTTP_200=StrDict), tags=["test", "health"])
async def ping():
    """summary

    description"""
    return jsonify(msg="pong"), 202


@app.route("/api/user/<name>", methods=["POST"])
@api.validate(
    query=Query,
    json=JSON,
    cookies=Cookies,
    resp=Response(HTTP_200=Resp, HTTP_401=None),
    tags=[api_tag, "test"],
    after=api_after_handler,
)
async def user_score(name):
    score = [randint(0, request.context.json.limit) for _ in range(5)]
    score.sort(reverse=request.context.query.order == Order.desc)
    assert request.context.cookies.pub == "abcdefg"
    assert request.cookies["pub"] == "abcdefg"
    return jsonify(name=request.context.json.name, score=score)


@app.route("/api/user_annotated/<name>", methods=["POST"])
@api.validate(
    resp=Response(HTTP_200=Resp, HTTP_401=None),
    tags=[api_tag, "test"],
    after=api_after_handler,
)
async def user_score_annotated(name, query: Query, json: JSON, cookies: Cookies):
    score = [randint(0, json.limit) for _ in range(5)]
    score.sort(reverse=query.order == Order.desc)
    assert cookies.pub == "abcdefg"
    assert request.cookies["pub"] == "abcdefg"
    return jsonify(name=json.name, score=score)


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
async def user_score_skip_validation(name):
    response_format = request.args.get("response_format")
    assert response_format in ("json", "xml")
    json = request.get_json()
    score = [randint(0, json.get("limit")) for _ in range(5)]
    score.sort(reverse=request.args.get("order") == Order.desc)
    assert request.cookies["pub"] == "abcdefg"
    if response_format == "json":
        return jsonify(name=json.get("name"), x_score=score)
    else:
        return app.response_class(
            response=UserXmlData(name=json.get("name"), score=score).dump_xml(),
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
async def user_score_model(name):
    score = [randint(0, request.context.json.limit) for _ in range(5)]
    score.sort(reverse=request.context.query.order == Order.desc)
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
async def user_address(name, address_id):
    return None


@app.route("/api/no_response", methods=["GET", "POST"])
@api.validate(
    json=JSON,
)
async def no_response():
    return {}


@app.route("/api/list_json", methods=["POST"])
@api.validate(
    json=ListJSON,
)
async def list_json():
    return {}


@app.route("/api/return_list")
@api.validate(resp=Response(HTTP_200=List[JSON]))
def return_list():
    pre_serialize = bool(int(request.args.get("pre_serialize", default=0)))
    data = [JSON(name="user1", limit=1), JSON(name="user2", limit=2)]
    return [entry.dict() if pre_serialize else entry for entry in data]


@app.route("/api/return_root", methods=["GET"])
@api.validate(resp=Response(HTTP_200=RootResp))
def return_root():
    return get_root_resp_data(
        pre_serialize=bool(int(request.args.get("pre_serialize", default=0))),
        return_what=request.args.get("return_what", default="RootResp"),
    )


@app.route("/api/custom_error", methods=["POST"])
@api.validate(resp=Response(HTTP_200=CustomError))
def custom_error(json: CustomError):
    return jsonify(foo="bar")


# INFO: ensures that spec is calculated and cached _after_ registering
# view functions for validations. This enables tests to access `api.spec`
# without app_context.
# TODO: this is commented out because it requires async context
# with app.app_context():
#     api.spec
api.register(app)


@pytest.fixture
def client():
    client = app.test_client()
    return client


@pytest.fixture
def test_client_and_api(request):
    api_args = ["quart"]
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
    app = Quart(__name__)
    app.config["TESTING"] = True

    @app.route("/ping")
    @api.validate(**endpoint_kwargs)
    async def ping():
        """summary

        description"""
        return jsonify(msg="pong")

    # INFO: ensures that spec is calculated and cached _after_ registering
    # view functions for validations. This enables tests to access `api.spec`
    # without app_context.
    api.register(app)
    test_client = app.test_client()
    return test_client, api


"""
Secure param check
"""


@app_secure.route("/no-secure-ping", methods=["GET"])
@api_secure.validate(
    resp=Response(HTTP_200=StrDict),
)
async def no_secure_ping():
    """
    No auth type is set
    """
    return jsonify(msg="pong")


@app_secure.route("/apiKey-ping", methods=["GET"])
@api_secure.validate(
    resp=Response(HTTP_200=StrDict),
    security={"auth_apiKey": []},
)
async def apiKey_ping():
    """
    apiKey auth type
    """
    return jsonify(msg="pong")


@app_secure.route("/apiKey-BasicAuth-ping", methods=["GET"])
@api_secure.validate(
    resp=Response(HTTP_200=StrDict),
    security={"auth_apiKey": [], "auth_BasicAuth": []},
)
async def apiKey_BasicAuth_ping():
    """
    Multiple auth types is set - apiKey and BasicAuth
    """
    return jsonify(msg="pong")


@app_secure.route("/BasicAuth-ping", methods=["GET"])
@api_secure.validate(
    resp=Response(HTTP_200=StrDict),
    security={"auth_BasicAuth": []},
)
async def BasicAuth_ping():
    """
    BasicAuth auth type
    """
    return jsonify(msg="pong")


@app_secure.route("/oauth2-flows-ping", methods=["GET"])
@api_secure.validate(
    resp=Response(HTTP_200=StrDict),
    security={"auth_oauth2": ["admin", "read"]},
)
async def oauth_two_ping():
    """
    oauth2 auth type with flow
    """
    return jsonify(msg="pong")


# TODO: this is commented out because it requires async context
# with app_secure.app_context():
#     api_secure.spec

api_secure.register(app_secure)


"""
Global secure params check
"""


@app_global_secure.route("/global-secure-ping", methods=["GET"])
@api_global_secure.validate(
    resp=Response(HTTP_200=StrDict),
)
async def global_auth_ping():
    """
    global auth type
    """
    return jsonify(msg="pong")


@app_global_secure.route("/no-secure-override-ping", methods=["GET"])
@api_global_secure.validate(
    security={},
    resp=Response(HTTP_200=StrDict),
)
async def global_no_secure_ping():
    """
    No auth type is set to override
    """
    return jsonify(msg="pong")


@app_global_secure.route("/oauth2-flows-override-ping", methods=["GET"])
@api_global_secure.validate(
    security={"auth_oauth2": ["admin", "read"]},
    resp=Response(HTTP_200=StrDict),
)
async def global_oauth_two_ping():
    """
    oauth2 auth type with flow to override
    """
    return jsonify(msg="pong")


@app_global_secure.route("/security_and", methods=["GET"])
@api_global_secure.validate(
    security={"auth_apiKey": [], "auth_apiKey_backup": []},
    resp=Response(HTTP_200=StrDict),
)
async def global_security_and():
    """
    global auth AND
    """
    return jsonify(msg="pong")


@app_global_secure.route("/security_or", methods=["GET"])
@api_global_secure.validate(
    security=[{"auth_apiKey": []}, {"auth_apiKey_backup": []}],
    resp=Response(HTTP_200=StrDict),
)
async def global_security_or():
    """
    global auth OR
    """
    return jsonify(msg="pong")


# TODO: this is commented out because it requires async context
# with app_global_secure.app_context():
#     api_global_secure.spec

api_global_secure.register(app_global_secure)
