import asyncio

import pytest

from tests.common import UserXmlData


@pytest.mark.parametrize("response_format", ["json", "xml"])
def test_quart_skip_validation(client, response_format: str):
    client.set_cookie("quart", "pub", "abcdefg")

    resp = asyncio.run(
        client.post(
            f"/api/user_skip/quart?order=1&response_format={response_format}",
            json=dict(name="quart", limit=10),
            headers={"Content-Type": "application/json"},
        )
    )
    resp_json = asyncio.run(resp.json)
    assert resp.status_code == 200, resp_json
    assert resp.headers.get("X-Validation") is None
    assert resp.headers.get("X-API") == "OK"
    if response_format == "json":
        assert resp.content_type == "application/json"
        assert resp.json["name"] == "quart"
        assert resp.json["x_score"] == sorted(resp.json["x_score"], reverse=True)
    else:
        assert resp.content_type == "text/xml"
        user_xml_data = UserXmlData.parse_xml(resp.text)
        assert user_xml_data.name == "quart"
        assert user_xml_data.score == sorted(user_xml_data.score, reverse=True)


def test_quart_return_model(client):
    client.set_cookie("quart", "pub", "abcdefg")

    resp = asyncio.run(
        client.post(
            "/api/user_model/quart?order=1",
            json=dict(name="quart", limit=10),
            headers={"Content-Type": "application/json"},
        )
    )
    resp_json = asyncio.run(resp.json)
    assert resp.status_code == 200, resp_json
    assert resp.headers.get("X-Validation") is None
    assert resp.headers.get("X-API") == "OK"
    assert resp_json["name"] == "quart"
    assert resp_json["score"] == sorted(resp_json["score"], reverse=True)


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
def test_quart_validation_error_response_status_code(
    test_client_and_api, expected_status_code
):
    app_client, _ = test_client_and_api

    resp = asyncio.run(app_client.get("/ping"))

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
def test_quart_doc(test_client_and_api, expected_doc_pages):
    client, api = test_client_and_api

    resp = asyncio.run(client.get("/apidoc/openapi.json"))
    assert asyncio.run(resp.json) == api.spec

    for doc_page in expected_doc_pages:
        resp = asyncio.run(client.get(f"/apidoc/{doc_page}/"))
        assert resp.status_code == 200

        resp = asyncio.run(client.get(f"/apidoc/{doc_page}"))
        assert resp.status_code == 308


def test_quart_validate(client):
    resp = asyncio.run(client.get("/ping"))
    assert resp.status_code == 422
    assert resp.headers.get("X-Error") == "Validation Error"

    resp = asyncio.run(client.get("/ping", headers={"lang": "en-US"}))
    resp_json = asyncio.run(resp.json)
    assert resp_json == {"msg": "pong"}
    assert resp.headers.get("X-Error") is None
    assert resp.headers.get("X-Validation") == "Pass"

    resp = asyncio.run(client.post("api/user/quart"))
    assert resp.status_code == 422
    assert resp.headers.get("X-Error") == "Validation Error"

    client.set_cookie("quart", "pub", "abcdefg")
    for fragment in ("user", "user_annotated"):
        resp = asyncio.run(
            client.post(
                f"/api/{fragment}/quart?order=1",
                json=dict(name="quart", limit=10),
                headers={"Content-Type": "application/json"},
            )
        )
        resp_json = asyncio.run(resp.json)
        assert resp.status_code == 200, resp_json
        assert resp.headers.get("X-Validation") is None
        assert resp.headers.get("X-API") == "OK"
        assert resp_json["name"] == "quart"
        assert resp_json["score"] == sorted(resp_json["score"], reverse=True)

        resp = asyncio.run(
            client.post(
                f"/api/{fragment}/quart?order=0",
                json=dict(name="quart", limit=10),
                headers={"Content-Type": "application/json"},
            )
        )
        resp_json = asyncio.run(resp.json)
        assert resp.status_code == 200, resp_json
        assert resp_json["score"] == sorted(resp_json["score"], reverse=False)


def test_quart_no_response(client):
    resp = asyncio.run(client.get("/api/no_response"))
    assert resp.status_code == 200

    resp = asyncio.run(
        client.post("/api/no_response", json={"name": "foo", "limit": 1})
    )
    assert resp.status_code == 200


def test_quart_list_json_request(client):
    resp = asyncio.run(
        client.post("/api/list_json", json=[{"name": "foo", "limit": 1}])
    )
    assert resp.status_code == 200


@pytest.mark.parametrize("pre_serialize", [False, True])
def test_quart_return_list_request(client, pre_serialize: bool):
    resp = asyncio.run(
        client.get(f"/api/return_list?pre_serialize={int(pre_serialize)}")
    )
    assert resp.status_code == 200
    assert resp.json == [
        {"name": "user1", "limit": 1},
        {"name": "user2", "limit": 2},
    ]
