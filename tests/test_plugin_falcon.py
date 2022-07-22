from random import randint

try:
    from falcon import App
except ImportError:
    from falcon import API as App

import pytest
from falcon import testing

from spectree import Response, SpecTree

from .common import JSON, Cookies, Headers, Query, Resp, StrDict, api_tag


def before_handler(req, resp, err, instance):
    if err:
        resp.set_header("X-Error", "Validation Error")


def after_handler(req, resp, err, instance):
    resp.set_header("X-Name", instance.name)


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
        tags=[api_tag, "test"],
    )
    def on_post(self, req, resp, name, query: Query, json: JSON, cookies: Cookies):
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
        tags=[api_tag, "test"],
    )
    def on_post(self, req, resp, name, query: Query, json: JSON, cookies: Cookies):
        score = [randint(0, req.context.json.limit) for _ in range(5)]
        score.sort(reverse=req.context.query.order)
        assert req.context.cookies.pub == "abcdefg"
        assert req.cookies["pub"] == "abcdefg"
        resp.media = {"name": req.context.json.name, "score": score}


class UserScoreSkip:
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
        tags=[api_tag, "test"],
        skip_validation=True,
    )
    def on_post(self, req, resp, name, query: Query, json: JSON, cookies: Cookies):
        score = [randint(0, req.context.json.limit) for _ in range(5)]
        score.sort(reverse=req.context.query.order)
        assert req.context.cookies.pub == "abcdefg"
        assert req.cookies["pub"] == "abcdefg"
        resp.media = {"name": req.context.json.name, "x_score": score}


class UserScoreModel:
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
        tags=[api_tag, "test"],
    )
    def on_post(self, req, resp, name, query: Query, json: JSON, cookies: Cookies):
        score = [randint(0, req.context.json.limit) for _ in range(5)]
        score.sort(reverse=req.context.query.order)
        assert req.context.cookies.pub == "abcdefg"
        assert req.cookies["pub"] == "abcdefg"
        resp.media = Resp(name=req.context.json.name, score=score)


class UserAddress:
    name = "user's address"

    @api.validate(
        query=Query,
        path_parameter_descriptions={
            "name": "The name that uniquely identifies the user.",
            "non-existent-param": "description",
        },
    )
    def on_get(self, req, resp, name, address_id):
        return None


class NoResponseView:

    name = "no response view"

    @api.validate(
        resp=Response(HTTP_200=None),  # response is None
    )
    def on_get(self, req, resp):
        pass

    @api.validate(
        json=JSON,  # resp is missing completely
    )
    def on_post(self, req, resp, json: JSON):
        pass


app = App()
app.add_route("/ping", Ping())
app.add_route("/api/user/{name}", UserScore())
app.add_route("/api/user_annotated/{name}", UserScoreAnnotated())
app.add_route("/api/user/{name}/address/{address_id}", UserAddress())
app.add_route("/api/user_skip/{name}", UserScoreSkip())
app.add_route("/api/user_model/{name}", UserScoreModel())
app.add_route("/api/no_response", NoResponseView())
api.register(app)


@pytest.fixture
def client():
    return testing.TestClient(app)


def test_falcon_validate(client):
    resp = client.simulate_request(
        "GET", "/ping", headers={"Content-Type": "text/plain"}
    )
    assert resp.status_code == 422
    assert resp.headers.get("X-Error") == "Validation Error", resp.headers

    resp = client.simulate_request(
        "GET", "/ping", headers={"lang": "en-US", "Content-Type": "text/plain"}
    )
    assert resp.json == {"msg": "pong"}
    assert resp.headers.get("X-Error") is None
    assert resp.headers.get("X-Name") == "health check"

    resp = client.simulate_request(
        "GET", "/api/user/falcon", headers={"Content-Type": "text/plain"}
    )
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


def test_falcon_skip_validation(client):
    resp = client.simulate_request(
        "POST",
        "/api/user_skip/falcon?order=1",
        json=dict(name="falcon", limit=10),
        headers={"Cookie": "pub=abcdefg"},
    )
    assert resp.json["name"] == "falcon"
    assert resp.json["x_score"] == sorted(resp.json["x_score"], reverse=True)
    assert resp.headers.get("X-Name") == "sorted random score"


def test_falcon_return_model(client):
    resp = client.simulate_request(
        "POST",
        "/api/user_model/falcon?order=1",
        json=dict(name="falcon", limit=10),
        headers={"Cookie": "pub=abcdefg"},
    )
    assert resp.json["name"] == "falcon"
    assert resp.json["score"] == sorted(resp.json["score"], reverse=True)
    assert resp.headers.get("X-Name") == "sorted random score"


def test_falcon_no_response(client):
    resp = client.simulate_request(
        "POST",
        "/api/no_response",
        json=dict(name="foo", limit=1),
    )
    assert resp.status_code == 200, resp.json

    resp = client.simulate_request(
        "GET",
        "/api/no_response",
    )
    assert resp.status_code == 200


@pytest.fixture
def test_client_and_api(request):
    api_args = ["falcon"]
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

    class Ping:
        name = "health check"

        @api.validate(**endpoint_kwargs)
        def on_get(self, req, resp):
            """summary

            description
            """
            resp.media = {"msg": "pong"}

    app = App()
    app.add_route("/ping", Ping())
    api.register(app)

    return testing.TestClient(app), api


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

    resp = app_client.simulate_request(
        "GET", "/ping", headers={"Content-Type": "text/plain"}
    )

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

    resp = client.simulate_get("/apidoc/openapi.json")
    assert resp.json == api.spec

    for doc_page in expected_doc_pages:
        resp = client.simulate_get(f"/apidoc/{doc_page}")
        assert resp.status_code == 200
