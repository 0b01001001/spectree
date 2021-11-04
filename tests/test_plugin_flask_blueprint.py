import json
from random import randint

import pytest
from flask import Blueprint, Flask, jsonify, request

from spectree import Response, SpecTree

from .common import JSON, Cookies, Headers, Query, Resp, StrDict, api_tag


def before_handler(req, resp, err, _):
    if err:
        resp.headers["X-Error"] = "Validation Error"


def after_handler(req, resp, err, _):
    resp.headers["X-Validation"] = "Pass"


def api_after_handler(req, resp, err, _):
    resp.headers["X-API"] = "OK"


api = SpecTree("flask", before=before_handler, after=after_handler)
app = Blueprint("test_blueprint", __name__)


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
    score.sort(reverse=request.context.query.order)
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
    score.sort(reverse=query.order)
    assert cookies.pub == "abcdefg"
    assert request.cookies["pub"] == "abcdefg"
    return jsonify(name=json.name, score=score)


api.register(app)

flask_app = Flask(__name__)
flask_app.register_blueprint(app)
with flask_app.app_context():
    api.spec


@pytest.fixture
def client(request):
    parent_app = Flask(__name__)
    parent_app.register_blueprint(app, url_prefix=request.param)
    with parent_app.test_client() as client:
        yield client


@pytest.mark.parametrize(
    ("client", "prefix"), [(None, ""), ("/prefix", "/prefix")], indirect=["client"]
)
def test_flask_validate(client, prefix):
    resp = client.get(prefix + "/ping")
    assert resp.status_code == 422
    assert resp.headers.get("X-Error") == "Validation Error"

    resp = client.get(prefix + "/ping", headers={"lang": "en-US"})
    assert resp.json == {"msg": "pong"}
    assert resp.headers.get("X-Error") is None
    assert resp.headers.get("X-Validation") == "Pass"

    resp = client.post(prefix + "/api/user/flask")
    assert resp.status_code == 422
    assert resp.headers.get("X-Error") == "Validation Error"

    client.set_cookie("flask", "pub", "abcdefg")
    resp = client.post(
        prefix + "/api/user/flask?order=1",
        data=json.dumps(dict(name="flask", limit=10)),
        content_type="application/json",
    )
    assert resp.status_code == 200, resp.json
    assert resp.headers.get("X-Validation") is None
    assert resp.headers.get("X-API") == "OK"
    assert resp.json["name"] == "flask"
    assert resp.json["score"] == sorted(resp.json["score"], reverse=True)

    resp = client.post(
        prefix + "/api/user/flask?order=0",
        data=json.dumps(dict(name="flask", limit=10)),
        content_type="application/json",
    )
    assert resp.json["score"] == sorted(resp.json["score"], reverse=False)


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

    resp = client.get(prefix + "/apidoc/redoc")
    assert resp.status_code == 200

    resp = client.get(prefix + "/apidoc/swagger")
    assert resp.status_code == 200
