from random import randint

import pytest
from falcon import testing

from spectree import Response, SpecTree

from .common import JSON, Cookies, Headers, Query, Resp, StrDict, api_tag

App = pytest.importorskip("falcon.asgi.App", reason="Missing required Falcon 3.0")


def before_handler(req, resp, err, instance):
    if err:
        resp.set_header("X-Error", "Validation Error")


def after_handler(req, resp, err, instance):
    print(instance.name)
    resp.set_header("X-Name", instance.name)
    print(resp.get_header("X-Name"))


api = SpecTree(
    "falcon-asgi", before=before_handler, after=after_handler, annotations=True
)


class Ping:
    name = "health check"

    @api.validate(headers=Headers, tags=["test", "health"])
    async def on_get(self, req, resp):
        """summary
        description
        """
        resp.media = {"msg": "pong"}


class UserScore:
    name = "sorted random score"

    def extra_method(self):
        pass

    @api.validate(resp=Response(HTTP_200=StrDict))
    async def on_get(self, req, resp, name):
        self.extra_method()
        resp.media = {"name": name}

    @api.validate(
        query=Query,
        json=JSON,
        cookies=Cookies,
        resp=Response(HTTP_200=Resp, HTTP_401=None),
        tags=[api_tag, "test"],
    )
    async def on_post(self, req, resp, name):
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
    async def on_get(self, req, resp, name):
        self.extra_method()
        resp.media = {"name": name}

    @api.validate(
        resp=Response(HTTP_200=Resp, HTTP_401=None),
        tags=[api_tag, "test"],
    )
    async def on_post(
        self, req, resp, name, query: Query, json: JSON, cookies: Cookies
    ):
        score = [randint(0, req.context.json.limit) for _ in range(5)]
        score.sort(reverse=req.context.query.order)
        assert req.context.cookies.pub == "abcdefg"
        assert req.cookies["pub"] == "abcdefg"
        resp.media = {"name": req.context.json.name, "score": score}


app = App()
app.add_route("/ping", Ping())
app.add_route("/api/user/{name}", UserScore())
app.add_route("/api/user_annotated/{name}", UserScoreAnnotated())
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


class TestFalconValidationErrorResponseStatus:
    @pytest.fixture
    def app_client(self, request):
        api_kwargs = {}
        if request.param["global_validation_error_status"]:
            api_kwargs["validation_error_status"] = request.param[
                "global_validation_error_status"
            ]
        api = SpecTree("falcon-asgi", **api_kwargs)

        class Ping:
            name = "health check"

            @api.validate(
                headers=Headers,
                tags=["test", "health"],
                validation_error_status=request.param[
                    "validation_error_status_override"
                ],
            )
            async def on_get(self, req, resp):
                """summary
                description
                """
                resp.media = {"msg": "pong"}

        app = App()
        app.add_route("/ping", Ping())
        api.register(app)

        return testing.TestClient(app)

    @pytest.mark.parametrize(
        "app_client, expected_status_code",
        [
            pytest.param(
                {
                    "global_validation_error_status": None,
                    "validation_error_status_override": None,
                },
                422,
                id="default-global-status-without-override",
            ),
            pytest.param(
                {
                    "global_validation_error_status": None,
                    "validation_error_status_override": 400,
                },
                400,
                id="default-global-status-with-override",
            ),
            pytest.param(
                {
                    "global_validation_error_status": 418,
                    "validation_error_status_override": None,
                },
                418,
                id="overridden-global-status-without-override",
            ),
            pytest.param(
                {
                    "global_validation_error_status": 400,
                    "validation_error_status_override": 418,
                },
                418,
                id="overridden-global-status-with-override",
            ),
        ],
        indirect=["app_client"],
    )
    def test_validation_error_response_status_code(
        self, app_client, expected_status_code
    ):
        resp = app_client.simulate_request(
            "GET", "/ping", headers={"Content-Type": "text/plain"}
        )

        assert resp.status_code == expected_status_code


def test_falcon_doc(client):
    resp = client.simulate_get("/apidoc/openapi.json")
    assert resp.json == api.spec

    resp = client.simulate_get("/apidoc/redoc")
    assert resp.status_code == 200

    resp = client.simulate_get("/apidoc/swagger")
    assert resp.status_code == 200
