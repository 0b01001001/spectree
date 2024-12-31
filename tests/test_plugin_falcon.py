from random import randint
from typing import List

import falcon
import pytest
from falcon import HTTP_202, App, testing

from spectree import Response, SpecTree
from spectree._pydantic import (
    PYDANTIC2,
    BaseModel,
    InternalBaseModel,
)

from .common import (
    JSON,
    Cookies,
    CustomError,
    FormFileUpload,
    Headers,
    ListJSON,
    OptionalAliasResp,
    Order,
    Query,
    Resp,
    RootResp,
    StrDict,
    UserXmlData,
    api_tag,
    get_root_resp_data,
)


def before_handler(req, resp, err, instance):
    if err:
        resp.set_header("X-Error", "Validation Error")


def after_handler(req, resp, err, instance):
    if hasattr(instance, "name"):
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
        resp.status = HTTP_202


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
        response_format = req.params.get("response_format")
        assert response_format in ("json", "xml")
        score = [randint(0, req.media.get("limit")) for _ in range(5)]
        score.sort(reverse=int(req.params.get("order")) == Order.desc)
        assert req.cookies["pub"] == "abcdefg"
        if response_format == "json":
            resp.media = {"name": req.media.get("name"), "x_score": score}
        else:
            resp.content_type = falcon.MEDIA_XML
            resp.text = UserXmlData(name=req.media.get("name"), score=score).dump_xml()


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
        json=StrDict,  # resp is missing completely
    )
    def on_post(self, req, resp, json: JSON):
        pass


class FileUploadView:
    name = "file upload view"

    @api.validate(
        form=FormFileUpload,
    )
    def on_post(self, req, resp, form: FormFileUpload):
        assert form.file
        file_content = form.file
        resp.media = {"file": file_content.decode("utf-8")}


class ListJsonView:
    name = "json list request view"

    @api.validate()
    def on_post(self, req, resp, json: ListJSON):  # type: ignore
        pass


class ReturnListView:
    name = "return list request view"

    @api.validate(resp=Response(HTTP_200=List[JSON]))
    def on_get(self, req, resp):
        pre_serialize = bool(int(req.params.get("pre_serialize", 0)))
        data = [JSON(name="user1", limit=1), JSON(name="user2", limit=2)]
        resp.media = [entry.dict() if pre_serialize else entry for entry in data]


class ReturnRootView:
    name = "return root request view"

    @api.validate(resp=Response(HTTP_200=RootResp))
    def on_get(self, req, resp):
        resp.media = get_root_resp_data(
            pre_serialize=bool(int(req.params.get("pre_serialize", 0))),
            return_what=req.params.get("return_what", "RootResp"),
        )


class CustomErrorView:
    name = "custom error view"

    @api.validate(resp=Response(HTTP_200=CustomError))
    def on_post(self, req, resp, json: CustomError):
        resp.media = {"foo": "bar"}
        resp.status = falcon.HTTP_422


class ReturnOptionalAliasView:
    @api.validate(resp=Response(HTTP_200=OptionalAliasResp))
    def on_get(self, req, resp):
        resp.media = {"schema": "test"}


class ViewWithCustomSerializer:
    name = "view with custom serializer"

    @api.validate(
        resp=Response(HTTP_200=Resp),
    )
    def on_get(self, req, resp):
        resp.data = Resp(name="falcon", score=[1, 2, 3]).json().encode("utf-8")

    @api.validate(
        resp=Response(HTTP_200=Resp),
    )
    def on_post(self, req, resp):
        resp.text = Resp(name="falcon", score=[1, 2, 3]).json()


app = App()
app.add_route("/ping", Ping())
app.add_route("/api/user/{name}", UserScore())
app.add_route("/api/user_annotated/{name}", UserScoreAnnotated())
app.add_route("/api/user/{name}/address/{address_id}", UserAddress())
app.add_route("/api/user_skip/{name}", UserScoreSkip())
app.add_route("/api/user_model/{name}", UserScoreModel())
app.add_route("/api/no_response", NoResponseView())
app.add_route("/api/file_upload", FileUploadView())
app.add_route("/api/list_json", ListJsonView())
app.add_route("/api/return_list", ReturnListView())
app.add_route("/api/return_root", ReturnRootView())
app.add_route("/api/return_optional_alias", ReturnOptionalAliasView())
app.add_route("/api/custom_serializer", ViewWithCustomSerializer())
app.add_route("/api/custom_error", CustomErrorView())
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
    assert resp.status_code == 202
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


@pytest.mark.parametrize("response_format", ["json", "xml"])
def test_falcon_skip_validation(client, response_format: str):
    resp = client.simulate_request(
        "POST",
        f"/api/user_skip/falcon?order=1&response_format={response_format}",
        json=dict(name="falcon", limit=10),
        headers={"Cookie": "pub=abcdefg"},
    )
    assert resp.headers.get("X-Name") == "sorted random score"
    if response_format == "json":
        assert resp.json["name"] == "falcon"
        assert resp.json["x_score"] == sorted(resp.json["x_score"], reverse=True)
    else:
        user_xml_data = UserXmlData.parse_xml(resp.text)
        assert user_xml_data.name == "falcon"
        assert user_xml_data.score == sorted(user_xml_data.score, reverse=True)


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


def test_falcon_list_json_request_sync(client):
    resp = client.simulate_request(
        "POST",
        "/api/list_json",
        json=[dict(name="foo", limit=1)],
    )
    assert resp.status_code == 200


@pytest.mark.parametrize("pre_serialize", [False, True])
def test_falcon_return_list_request_sync(client, pre_serialize: bool):
    resp = client.simulate_request(
        "GET", f"/api/return_list?pre_serialize={int(pre_serialize)}"
    )
    assert resp.status_code == 200
    assert resp.json == [
        {"name": "user1", "limit": 1},
        {"name": "user2", "limit": 2},
    ]


@pytest.mark.parametrize("pre_serialize", [False, True])
@pytest.mark.parametrize(
    "return_what", ["RootResp_JSON", "RootResp_List", "JSON", "List"]
)
def test_falcon_return_root_request_sync(client, pre_serialize: bool, return_what: str):
    resp = client.simulate_request(
        "GET",
        f"/api/return_root?pre_serialize={int(pre_serialize)}"
        f"&return_what={return_what}",
    )
    assert resp.status_code == 200
    if return_what in ("RootResp_JSON", "JSON"):
        assert resp.json == {"name": "user1", "limit": 1}
    elif return_what in ("RootResp_List", "List"):
        assert resp.json == [1, 2, 3, 4]


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
def test_falcon_doc(test_client_and_api, expected_doc_pages):
    client, api = test_client_and_api

    resp = client.simulate_get("/apidoc/openapi.json")
    assert resp.json == api.spec

    for doc_page in expected_doc_pages:
        resp = client.simulate_get(f"/apidoc/{doc_page}")
        assert resp.status_code == 200


def test_falcon_file_upload_sync(client):
    boundary = "xxx"
    file_content = "abcdef"
    body = (
        f"--{boundary}\r\n"
        'Content-Disposition: form-data; name="file"; filename="test.txt"\r\n'
        "Content-Type: text/plain\r\n\r\n"
        f"{file_content}\r\n"
        f"--{boundary}--\r\n"
    )

    resp = client.simulate_post(
        "/api/file_upload",
        headers={
            "Content-Type": "multipart/form-data; boundary=%s" % boundary,
        },
        body=body.encode("utf-8"),
    )
    assert resp.status_code == 200, resp.text
    assert resp.headers["content-type"] == "application/json"
    assert resp.json["file"] == file_content


def test_falcon_custom_serializer(client):
    resp = client.simulate_get(
        "/api/custom_serializer",
    )
    assert resp.status_code == 200
    assert resp.json["name"] == "falcon"
    assert resp.json["score"] == [1, 2, 3]

    resp = client.simulate_post(
        "/api/custom_serializer",
    )
    assert resp.status_code == 200
    assert resp.json["name"] == "falcon"
    assert resp.json["score"] == [1, 2, 3]


def test_falcon_optional_alias_response(client):
    resp = client.simulate_get(
        "/api/return_optional_alias",
    )
    assert resp.status_code == 200, resp.json
    assert resp.json == {"schema": "test"}, resp.json


@pytest.mark.skipif(not PYDANTIC2, reason="only matters if using both model types")
def test_falcon_validate_both_v1_and_v2_validation_errors(client):
    class CompatibilityView:
        name = "validation works for both pydantic v1 and v2 models simultaneously"

        class V1(InternalBaseModel):
            value: int

        class V2(BaseModel):
            value: int

        @api.validate(
            resp=Response(HTTP_200=Resp),
        )
        def on_post_v1(self, req, resp, json: V1):
            resp.media = Resp(name="falcon v1", score=[1, 2, 3])

        @api.validate(
            resp=Response(HTTP_200=Resp),
        )
        def on_post_v2(self, req, resp, json: V2):
            resp.media = Resp(name="falcon v2", score=[1, 2, 3])

    app.add_route("/api/compatibility/v1", CompatibilityView(), suffix="v1")
    app.add_route("/api/compatibility/v2", CompatibilityView(), suffix="v2")

    resp = client.simulate_request(
        "POST", "/api/compatibility/v1", json={"value": "invalid"}
    )
    assert resp.status_code == 422

    resp = client.simulate_request(
        "POST", "/api/compatibility/v2", json={"value": "invalid"}
    )
    assert resp.status_code == 422


def test_custom_error(client):
    # error in request
    resp = client.simulate_post("/api/custom_error", json={"foo": "bar"})
    assert resp.status_code == 422

    # error in response
    resp = client.simulate_post("/api/custom_error", json={"foo": "foo"})
    assert resp.status_code == 500
