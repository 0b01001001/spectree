from dataclasses import dataclass
from http import HTTPStatus
from typing import Any

import falcon
import pytest
from falcon import testing as falcon_testing

from spectree import Response, SpecTree
from spectree.utils import get_model_key


@dataclass(frozen=True)
class FalconAdapterApp:
    client: falcon_testing.TestClient
    spec: SpecTree
    resource: Any
    item_model: Any
    raw_list_model: Any


@dataclass
class Query:
    limit: int


@dataclass
class Payload:
    name: str


@dataclass
class Item:
    name: str
    limit: int


@pytest.fixture
def falcon_adapter_app(model_case):
    query_model = model_case.convert_dataclass(Query)
    payload_model = model_case.convert_dataclass(Payload)
    item_model = model_case.convert_dataclass(Item)
    raw_list_model = model_case.list_of(item_model)

    spec = SpecTree(
        "falcon",
        annotations=True,
        model_adapter=model_case.adapter,
    )

    class Items:
        def on_post(self, req, resp, query, json):
            resp.media = [
                {
                    "name": json.name,
                    "limit": query.limit,
                }
            ]

    Items.on_post.__annotations__ = {
        "query": query_model,
        "json": payload_model,
    }
    Items.on_post = spec.validate(resp=Response(HTTP_200=raw_list_model))(Items.on_post)

    app = falcon.App()
    app.add_route("/items", Items())
    spec.register(app)

    return FalconAdapterApp(
        client=falcon_testing.TestClient(app),
        spec=spec,
        resource=Items,
        item_model=item_model,
        raw_list_model=raw_list_model,
    )


def test_falcon_model_adapter_validation_flow(falcon_adapter_app):
    response = falcon_adapter_app.client.simulate_post(
        "/items?limit=3",
        json={"name": "demo"},
    )

    assert response.status_code == HTTPStatus.OK
    assert response.json == [{"name": "demo", "limit": 3}]


def test_falcon_model_adapter_validation_error(falcon_adapter_app):
    response = falcon_adapter_app.client.simulate_post(
        "/items?limit=bad",
        json={"name": "demo"},
    )

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert isinstance(response.json, list)
    assert response.json[0]["loc"] == ["limit"]
    assert response.json[0]["msg"]
    assert response.json[0]["type"]


def test_falcon_model_adapter_response_models_and_spec(falcon_adapter_app):
    resource = falcon_adapter_app.resource

    assert (
        resource.on_post.resp.find_model(HTTPStatus.UNPROCESSABLE_ENTITY)
        is falcon_adapter_app.spec.model_adapter.validation_error
    )

    response_model = resource.on_post.resp.find_model(HTTPStatus.OK)
    expected_list_model = falcon_adapter_app.spec.model_adapter.make_list_model(
        falcon_adapter_app.item_model
    )

    assert response_model is not falcon_adapter_app.raw_list_model
    assert get_model_key(response_model) == get_model_key(expected_list_model)

    spec = falcon_adapter_app.spec.spec
    responses = spec["paths"]["/items"]["post"]["responses"]
    assert responses[str(HTTPStatus.OK.value)]["content"]["application/json"]["schema"][
        "$ref"
    ] == (f"#/components/schemas/{get_model_key(response_model)}")
    validation_error = falcon_adapter_app.spec.model_adapter.validation_error
    assert responses[str(HTTPStatus.UNPROCESSABLE_ENTITY.value)]["content"][
        "application/json"
    ]["schema"]["$ref"] == (f"#/components/schemas/{get_model_key(validation_error)}")
