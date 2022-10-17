from random import randint

import pytest
from quart import Quart, jsonify, request

from spectree import Response, SpecTree

from .common import (
    JSON,
    SECURITY_SCHEMAS,
    Cookies,
    Headers,
    Order,
    Query,
    Resp,
    StrDict,
    api_tag,
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
    return jsonify(msg="pong")


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
    score.sort(reverse=True if request.context.query.order == Order.desc else False)
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
    score.sort(reverse=True if query.order == Order.desc else False)
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
async def user_score_model(name):
    score = [randint(0, request.context.json.limit) for _ in range(5)]
    score.sort(reverse=True if request.context.query.order == Order.desc else False)
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


# INFO: ensures that spec is calculated and cached _after_ registering
# view functions for validations. This enables tests to access `api.spec`
# without app_context.
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


# with app_global_secure.app_context():
#     api_global_secure.spec

api_global_secure.register(app_global_secure)
