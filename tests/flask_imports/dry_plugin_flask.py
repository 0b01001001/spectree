import io
import random
import re

import pytest

from tests.common import JSON, UserXmlData


@pytest.mark.parametrize("response_format", ["json", "xml"])
def test_flask_skip_validation(client, response_format: str):
    client.set_cookie(
        key="pub", value="abcdefg", secure=True, httponly=True, samesite="Strict"
    )
    assert response_format in ("json", "xml")
    resp = client.post(
        f"/api/user_skip/flask?order=1&response_format={response_format}",
        json=dict(name="flask", limit=10),
        content_type="application/json",
    )
    assert resp.status_code == 200
    assert resp.headers.get("X-Validation") is None
    assert resp.headers.get("X-API") == "OK"
    if response_format == "json":
        assert resp.content_type == "application/json"
        assert resp.json["name"] == "flask"
        assert resp.json["x_score"] == sorted(resp.json["x_score"], reverse=True)
    else:
        assert resp.content_type == "text/xml"
        user_xml_data = UserXmlData.parse_xml(resp.text)
        assert user_xml_data.name == "flask"
        assert user_xml_data.score == sorted(user_xml_data.score, reverse=True)


def test_flask_return_model(client):
    client.set_cookie(
        key="pub", value="abcdefg", secure=True, httponly=True, samesite="Strict"
    )

    resp = client.post(
        "/api/user_model/flask?order=1",
        json=dict(name="flask", limit=10),
        content_type="application/json",
    )
    assert resp.status_code == 200, resp.text
    assert resp.headers.get("X-Validation") is None
    assert resp.headers.get("X-API") == "OK"
    assert resp.json["name"] == "flask"
    assert resp.json["score"] == sorted(resp.json["score"], reverse=True)


@pytest.mark.parametrize(
    ["test_client_and_api", "expected_status_code"],
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
def test_flask_validation_error_response_status_code(
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


def test_flask_validate_basic(client):
    resp = client.get("/ping")
    assert resp.status_code == 422
    assert resp.headers.get("X-Error") == "Validation Error"

    resp = client.get("/ping", headers={"lang": "en-US"})
    assert resp.json == {"msg": "pong"}
    assert resp.headers.get("X-Error") is None
    assert resp.headers.get("X-Validation") == "Pass"
    assert resp.headers.get("lang") == "en-US", resp.headers

    resp = client.post("api/user/flask")
    assert resp.status_code == 422
    assert resp.headers.get("X-Error") == "Validation Error"


@pytest.mark.parametrize(
    ["fragment"],
    [
        ("user",),
        ("user_annotated",),
    ],
)
def test_flask_validate_post_data(client, fragment):
    client.set_cookie(
        key="pub", value="abcdefg", secure=True, httponly=True, samesite="Strict"
    )
    resp = client.post(
        f"/api/{fragment}/flask?order=1",
        json=dict(name="flask", limit=10),
    )
    assert resp.status_code == 200, resp.json
    assert resp.headers.get("X-Validation") is None
    assert resp.headers.get("X-API") == "OK"
    assert resp.json["name"] == "flask"
    assert resp.json["score"] == sorted(resp.json["score"], reverse=True)

    resp = client.post(
        f"/api/{fragment}/flask?order=0",
        json=dict(name="flask", limit=10),
    )
    assert resp.status_code == 200, resp.json
    assert resp.json["score"] == sorted(resp.json["score"], reverse=False)

    resp = client.post(
        f"/api/{fragment}/flask?order=0",
        data=dict(name="flask", limit=10),
        content_type="application/x-www-form-urlencoded",
    )
    assert resp.status_code == 200, resp.json
    assert resp.json["score"] == sorted(resp.json["score"], reverse=False)

    # POST without body
    resp = client.post(
        f"/api/{fragment}/flask?order=0",
    )
    assert resp.status_code == 422, resp.content


def test_flask_no_response(client):
    resp = client.get("/api/no_response")
    assert resp.status_code == 200, resp.data

    resp = client.post("/api/no_response", data={"name": "foo", "limit": 1})
    assert resp.status_code == 200, resp.data


def test_flask_list_json_request(client):
    resp = client.post("/api/list_json", json=[{"name": "foo", "limit": 1}])
    assert resp.status_code == 200, resp.data


@pytest.mark.parametrize("pre_serialize", [False, True])
def test_flask_return_list_request(client, pre_serialize: bool):
    resp = client.get(f"/api/return_list?pre_serialize={int(pre_serialize)}")
    assert resp.status_code == 200
    assert resp.json == [
        {"name": "user1", "limit": 1},
        {"name": "user2", "limit": 2},
    ]


def test_flask_make_response_post(client):
    payload = JSON(
        limit=random.randint(1, 10),
        name="user make_response name",
    )
    resp = client.post(
        "/api/return_make_response", json=payload.dict(), headers={"lang": "en-US"}
    )
    assert resp.status_code == 201
    assert resp.json == {"name": payload.name, "score": [payload.limit]}
    assert resp.headers.get("lang") == "en-US"
    cookie_result = re.match(
        r"^test_cookie=\"((\w+\s?){3})\"; Secure; HttpOnly; Path=/; SameSite=Strict$",
        resp.headers.get("Set-Cookie"),
    )
    assert cookie_result.group(1) == payload.name


def test_flask_make_response_get(client):
    payload = JSON(
        limit=random.randint(1, 10),
        name="user make_response name",
    )
    resp = client.get(
        "/api/return_make_response",
        query_string=payload.dict(),
        headers={"lang": "en-US"},
    )
    assert resp.status_code == 201, resp
    assert resp.json == {"name": payload.name, "score": [payload.limit]}
    assert resp.headers.get("lang") == "en-US"
    cookie_result = re.match(
        r"^test_cookie=\"((\w+\s?){3})\"; Secure; HttpOnly; Path=/; SameSite=Strict$",
        resp.headers.get("Set-Cookie"),
    )
    assert cookie_result.group(1) == payload.name


@pytest.mark.parametrize("pre_serialize", [False, True])
@pytest.mark.parametrize(
    "return_what", ["RootResp_JSON", "RootResp_List", "JSON", "List"]
)
def test_flask_return_root_request(client, pre_serialize: bool, return_what: str):
    resp = client.get(
        f"/api/return_root?pre_serialize={int(pre_serialize)}&return_what={return_what}"
    )
    assert resp.status_code == 200
    if return_what in ("RootResp_JSON", "JSON"):
        assert resp.json == {"name": "user1", "limit": 1}
    elif return_what in ("RootResp_List", "List"):
        assert resp.json == [1, 2, 3, 4]


def test_flask_upload_file(client):
    file_content = "abcdef"
    data = {"file": (io.BytesIO(file_content.encode("utf-8")), "test.txt")}
    resp = client.post(
        "/api/file_upload",
        data=data,
        content_type="multipart/form-data",
    )
    assert resp.status_code == 200, resp.data
    assert resp.json["content"] == file_content


def test_flask_optional_alias_response(client):
    resp = client.get("/api/return_optional_alias")
    assert resp.status_code == 200
    assert resp.json == {"schema": "test"}, resp.json


def test_flask_query_list(client):
    resp = client.get("/api/query_list?ids=1&ids=2&ids=3")
    assert resp.status_code == 200


def test_flask_custom_error(client):
    # request error
    resp = client.post("/api/custom_error", json={"foo": "bar"})
    assert resp.status_code == 422

    # response error
    resp = client.post("/api/custom_error", json={"foo": "foo"})
    assert resp.status_code == 500
