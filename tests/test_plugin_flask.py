import json
from random import randint

import pytest
from flask import Flask, jsonify, request

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


api = SpecTree("flask", before=before_handler, after=after_handler, annotations=True)
app = Flask(__name__)
app.config["TESTING"] = True

api_secure = SpecTree("flask", security_schemes=SECURITY_SCHEMAS)
app_secure = Flask(__name__)
app_secure.config["TESTING"] = True

api_global_secure = SpecTree(
    "flask", security_schemes=SECURITY_SCHEMAS, security={"auth_apiKey": []}
)
app_global_secure = Flask(__name__)
app_global_secure.config["TESTING"] = True


@app.route("/ping")
@api.validate(headers=Headers, resp=Response(HTTP_200=StrDict), tags=["test", "health"])
def ping():
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
def user_score(name):
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
def user_score_annotated(name, query: Query, json: JSON, cookies: Cookies):
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
    json=Query,
)
def no_response():
    return {}


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
        assert resp.status_code == 200, resp.json
        assert resp.json["score"] == sorted(resp.json["score"], reverse=False)

        resp = client.post(
            f"/api/{fragment}/flask?order=0",
            data="name=flask&limit=10",
            content_type="application/x-www-form-urlencoded",
        )
        assert resp.status_code == 200, resp.json
        assert resp.json["score"] == sorted(resp.json["score"], reverse=False)


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
        resp = client.get(f"/apidoc/{doc_page}/")
        assert resp.status_code == 200

        resp = client.get(f"/apidoc/{doc_page}")
        assert resp.status_code == 308


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
    api_secure.spec

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
    api_global_secure.spec

api_global_secure.register(app_global_secure)
