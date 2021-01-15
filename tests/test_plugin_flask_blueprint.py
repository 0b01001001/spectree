import json
from random import randint

import pytest
from flask import Blueprint, Flask, jsonify, request

from spectree import Response, SpecTree

from .common import JSON, Cookies, Headers, Query, Resp, StrDict


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
    tags=["api", "test"],
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
    tags=["api", "test"],
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


@pytest.mark.parametrize(
    ("client", "prefix"), [(None, ""), ("/prefix", "/prefix")], indirect=["client"]
)
def test_flask_doc(client, prefix):
    resp = client.get(prefix + "/apidoc/openapi.json")
    assert resp.json == api.spec

    resp = client.get(prefix + "/apidoc/redoc")
    assert resp.status_code == 200

    resp = client.get(prefix + "/apidoc/swagger")
    assert resp.status_code == 200
