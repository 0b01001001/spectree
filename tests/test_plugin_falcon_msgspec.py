from typing import Any

import pytest

falcon = pytest.importorskip("falcon")
msgspec = pytest.importorskip("msgspec")
falcon_testing = pytest.importorskip("falcon.testing")
MsgspecStruct: Any = msgspec.Struct

from spectree import Response, SpecTree  # noqa: E402
from spectree.model_adapter import get_msgspec_model_adapter  # noqa: E402
from spectree.models import ValidationError  # noqa: E402


class Query(MsgspecStruct):
    limit: int


class Payload(MsgspecStruct):
    name: str


class Item(MsgspecStruct):
    name: str
    limit: int


@pytest.fixture
def app_and_api():
    api = SpecTree(
        "falcon",
        annotations=True,
        model_adapter=get_msgspec_model_adapter(),
    )

    class Items:
        @api.validate(
            query=Query,
            json=Payload,
            resp=Response(HTTP_200=list[Item]),
        )
        def on_post(self, req, resp, query: Query, json: Payload):
            resp.media = [{"name": json.name, "limit": query.limit}]

    app = falcon.App()
    app.add_route("/items", Items())
    api.register(app)
    return falcon_testing.TestClient(app), api, Items


def test_falcon_msgspec_validation_flow(app_and_api):
    client, _, _ = app_and_api

    response = client.simulate_post("/items?limit=3", json={"name": "demo"})

    assert response.status_code == 200
    assert response.json == [{"name": "demo", "limit": 3}]


def test_falcon_msgspec_validation_error(app_and_api):
    client, _, _ = app_and_api

    response = client.simulate_post("/items?limit=bad", json={"name": "demo"})

    assert response.status_code == 422
    assert response.json == [
        {
            "loc": ["limit"],
            "msg": "Expected `int`, got `str`",
            "type": "validation_error",
        }
    ]


def test_falcon_msgspec_response_models_and_spec(app_and_api):
    _, api, resource = app_and_api

    assert resource.on_post.resp.find_model(422) is ValidationError
    assert resource.on_post.resp.find_model(200).__name__ == "ItemList"

    spec = api.spec
    responses = spec["paths"]["/items"]["post"]["responses"]

    assert responses["200"]["content"]["application/json"]["schema"]["$ref"].startswith(
        "#/components/schemas/ItemList."
    )
    assert responses["422"]["content"]["application/json"]["schema"]["$ref"].startswith(
        "#/components/schemas/ValidationError."
    )
