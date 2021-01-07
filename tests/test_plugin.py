import pytest

from .common import JSON, Cookies, Headers, Query, Resp, get_paths
from .test_plugin_falcon import api as falcon_api
from .test_plugin_flask import api as flask_api
from .test_plugin_starlette import api as starlette_api


@pytest.mark.parametrize("api", [flask_api, falcon_api, starlette_api])
def test_plugin_spec(api):
    models = {
        m.__name__: m.schema(ref_template="#/components/schemas/{model}")
        for m in (Query, JSON, Resp, Cookies, Headers)
    }
    for name, schema in models.items():
        assert api.spec["components"]["schemas"][name] == schema

    assert api.spec["tags"] == [{"name": tag} for tag in ("test", "health", "api")]

    assert get_paths(api.spec) == [
        "/api/user/{name}",
        "/api/user_annotated/{name}",
        "/ping",
    ]

    ping = api.spec["paths"]["/ping"]["get"]
    assert ping["tags"] == ["test", "health"]
    assert ping["parameters"][0]["in"] == "header"
    assert ping["summary"] == "summary"
    assert ping["description"] == "description"
    assert ping["operationId"] == "get_/ping"

    user = api.spec["paths"]["/api/user/{name}"]["post"]
    assert user["tags"] == ["api", "test"]
    assert (
        user["requestBody"]["content"]["application/json"]["schema"]["$ref"]
        == "#/components/schemas/JSON"
    )
    assert len(user["responses"]) == 3

    params = user["parameters"]
    for param in params:
        if param["in"] == "path":
            assert param["name"] == "name"
        elif param["in"] == "query":
            assert param["name"] == "order"
