from .common import get_paths
from .test_plugin_flask import api as flask_api


def test_plugin_spec():
    api = flask_api
    assert api.spec["tags"] == [{"name": tag} for tag in ("test", "health", "api")]

    assert get_paths(api.spec) == ["/api/group/{name}", "/api/user/{name}", "/ping"]

    ping = api.spec["paths"]["/ping"]["get"]
    assert ping["tags"] == ["test", "health"]
    assert ping["parameters"][0]["in"] == "header"
    assert ping["summary"] == "summary"
    assert ping["description"] == "description"

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
