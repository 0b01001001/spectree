from random import randint

import falcon
import pytest
from falcon import testing

from spectree import Response, SpecTree

from .common import JSON, Cookies, Headers, Query, Resp, StrDict


def before_handler(req, resp, err, instance):
    if err:
        resp.set_header("X-Error", "Validation Error")


def after_handler(req, resp, err, instance):
    print(instance.name)
    resp.set_header("X-Name", instance.name)
    print(resp.get_header("X-Name"))


api = SpecTree("falcon", before=before_handler, after=after_handler, annotations=True)


class Ping:
    name = "health check"

    @api.validate(headers=Headers, tags=["test", "health"])
    def on_get(self, req, resp):
        """summary
        description
        """
        resp.media = {"msg": "pong"}


class UserScore:
    name = "sorted random score"

    def extra_method(self):
        pass

    @api.validate(resp=Response(HTTP_200=StrDict))
    def on_get(self, req, resp, name):
        self.extra_method()
        resp.media = {"name": name}

    @api.validate(
        query=Query,
        json=JSON,
        cookies=Cookies,
        resp=Response(HTTP_200=Resp, HTTP_401=None),
        tags=["api", "test"],
    )
    def on_post(self, req, resp, name):
        score = [randint(0, req.context.json.limit) for _ in range(5)]
        score.sort(reverse=req.context.query.order)
        assert req.context.cookies.pub == "abcdefg"
        assert req.cookies["pub"] == "abcdefg"
        resp.media = {"name": req.context.json.name, "score": score}


class UserScoreAnnotated:
    name = "sorted random score"

    def extra_method(self):
        pass

    @api.validate(resp=Response(HTTP_200=StrDict))
    def on_get(self, req, resp, name):
        self.extra_method()
        resp.media = {"name": name}

    @api.validate(
        resp=Response(HTTP_200=Resp, HTTP_401=None),
        tags=["api", "test"],
    )
    def on_post(self, req, resp, name, query: Query, json: JSON, cookies: Cookies):
        score = [randint(0, req.context.json.limit) for _ in range(5)]
        score.sort(reverse=req.context.query.order)
        assert req.context.cookies.pub == "abcdefg"
        assert req.cookies["pub"] == "abcdefg"
        resp.media = {"name": req.context.json.name, "score": score}


app = falcon.API()
app.add_route("/ping", Ping())
app.add_route("/api/user/{name}", UserScore())
app.add_route("/api/user_annotated/{name}", UserScoreAnnotated())
api.register(app)


@pytest.fixture
def client():
    return testing.TestClient(app)


def test_falcon_validate(client):
    resp = client.simulate_request("GET", "/ping")
    assert resp.status_code == 422
    assert resp.headers.get("X-Error") == "Validation Error", resp.headers

    resp = client.simulate_request("GET", "/ping", headers={"lang": "en-US"})
    assert resp.json == {"msg": "pong"}
    assert resp.headers.get("X-Error") is None
    assert resp.headers.get("X-Name") == "health check"

    resp = client.simulate_request("GET", "/api/user/falcon")
    assert resp.json == {"name": "falcon"}

    resp = client.simulate_request("POST", "/api/user/falcon")
    assert resp.status_code == 422
    assert resp.headers.get("X-Error") == "Validation Error"
    assert resp.headers.get("X-Name") is None

    resp = client.simulate_request(
        "POST",
        "/api/user/falcon?order=1",
        json=dict(name="falcon", limit=10),
        headers={"Cookie": "pub=abcdefg"},
    )
    assert resp.json["name"] == "falcon"
    assert resp.json["score"] == sorted(resp.json["score"], reverse=True)
    assert resp.headers.get("X-Name") == "sorted random score"

    resp = client.simulate_request(
        "POST",
        "/api/user/falcon?order=0",
        json=dict(name="falcon", limit=10),
        headers={"Cookie": "pub=abcdefg"},
    )
    assert resp.json["name"] == "falcon"
    assert resp.json["score"] == sorted(resp.json["score"], reverse=False)
    assert resp.headers.get("X-Name") == "sorted random score"


def test_falcon_doc(client):
    resp = client.simulate_get("/apidoc/openapi.json")
    assert resp.json == api.spec

    resp = client.simulate_get("/apidoc/redoc")
    assert resp.status_code == 200

    resp = client.simulate_get("/apidoc/swagger")
    assert resp.status_code == 200
