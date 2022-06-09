import pytest


def test_flask_skip_validation(client):
    client.set_cookie("flask", "pub", "abcdefg")

    resp = client.post(
        "/api/user_skip/flask?order=1",
        json=dict(name="flask", limit=10),
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
        json=dict(name="flask", limit=10),
        content_type="application/json",
    )
    assert resp.status_code == 200, resp.json
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
            json=dict(name="flask", limit=10),
            content_type="application/json",
        )
        assert resp.status_code == 200, resp.json
        assert resp.headers.get("X-Validation") is None
        assert resp.headers.get("X-API") == "OK"
        assert resp.json["name"] == "flask"
        assert resp.json["score"] == sorted(resp.json["score"], reverse=True)

        resp = client.post(
            f"/api/{fragment}/flask?order=0",
            json=dict(name="flask", limit=10),
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


def test_flask_no_response(client):
    resp = client.get("/api/no_response")
    assert resp.status_code == 200, resp.data

    resp = client.post("/api/no_response", data={"name": "foo", "limit": 1})
    assert resp.status_code == 200, resp.data
