from dataclasses import dataclass
from http import HTTPStatus
from typing import Any

import pytest
from flask import Blueprint, Flask
from flask.testing import FlaskClient
from flask.views import MethodView

from spectree import Response, SpecTree
from spectree.utils import get_model_key


@dataclass(frozen=True)
class FlaskAdapterApp:
    client: FlaskClient
    spec: SpecTree
    route_handlers: tuple[Any, ...]
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
def flask_adapter_app(model_case):
    query_model = model_case.get_model(Query)
    payload_model = model_case.get_model(Payload)
    item_model = model_case.get_model(Item)
    raw_list_model = model_case.list_of(item_model)

    spec = SpecTree(
        "flask",
        annotations=True,
        model_adapter=model_case.adapter,
    )
    app = Flask(__name__)
    app.config["TESTING"] = True

    def create_item(query: query_model, json: payload_model):
        return [{"name": json.name, "limit": query.limit}]

    create_item = spec.validate(resp=Response(HTTP_200=raw_list_model))(create_item)
    app.add_url_rule("/items", view_func=create_item, methods=["POST"])

    blueprint = Blueprint("adapter_blueprint", __name__)

    def create_blueprint_item(query: query_model, json: payload_model):
        return [{"name": json.name, "limit": query.limit}]

    create_blueprint_item = spec.validate(resp=Response(HTTP_200=raw_list_model))(
        create_blueprint_item
    )
    blueprint.add_url_rule(
        "/items",
        view_func=create_blueprint_item,
        methods=["POST"],
    )
    app.register_blueprint(blueprint, url_prefix="/bp")

    class ItemsView(MethodView):
        def post(self, query: query_model, json: payload_model):
            return [{"name": json.name, "limit": query.limit}]

    ItemsView.post = spec.validate(resp=Response(HTTP_200=raw_list_model))(
        ItemsView.post
    )
    app.add_url_rule(
        "/view-items",
        view_func=ItemsView.as_view("items_view"),
        methods=["POST"],
    )

    with app.app_context():
        _ = spec.spec
    spec.register(app)

    with app.test_client() as client:
        yield FlaskAdapterApp(
            client=client,
            spec=spec,
            route_handlers=(create_item, create_blueprint_item, ItemsView.post),
            item_model=item_model,
            raw_list_model=raw_list_model,
        )


@pytest.mark.parametrize("path", ["/items", "/bp/items", "/view-items"])
def test_flask_model_adapter_validation_flow(flask_adapter_app, path):
    response = flask_adapter_app.client.post(
        f"{path}?limit=3",
        json={"name": "demo"},
    )

    assert response.status_code == HTTPStatus.OK
    assert response.get_json() == [{"name": "demo", "limit": 3}]


@pytest.mark.parametrize("path", ["/items", "/bp/items", "/view-items"])
def test_flask_model_adapter_validation_error(flask_adapter_app, path):
    response = flask_adapter_app.client.post(
        f"{path}?limit=bad",
        json={"name": "demo"},
    )

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    errors = response.get_json()
    assert isinstance(errors, list)
    assert errors[0]["loc"] == ["limit"]
    assert errors[0]["msg"]
    assert errors[0]["type"]


def test_flask_model_adapter_response_models_and_spec(flask_adapter_app):
    expected_list_model = flask_adapter_app.spec.model_adapter.make_list_model(
        flask_adapter_app.item_model
    )

    for handler in flask_adapter_app.route_handlers:
        assert (
            handler.resp.find_model(HTTPStatus.UNPROCESSABLE_ENTITY)
            is flask_adapter_app.spec.model_adapter.validation_error
        )

        response_model = handler.resp.find_model(HTTPStatus.OK)
        assert response_model is not flask_adapter_app.raw_list_model
        assert get_model_key(response_model) == get_model_key(expected_list_model)

    spec = flask_adapter_app.spec.spec
    expected_response_ref = f"#/components/schemas/{get_model_key(expected_list_model)}"
    validation_error = flask_adapter_app.spec.model_adapter.validation_error
    validation_ref = f"#/components/schemas/{get_model_key(validation_error)}"

    for path in ("/items", "/bp/items", "/view-items"):
        responses = spec["paths"][path]["post"]["responses"]
        ok_schema = responses[str(HTTPStatus.OK.value)]["content"]["application/json"][
            "schema"
        ]
        validation_schema = responses[str(HTTPStatus.UNPROCESSABLE_ENTITY.value)][
            "content"
        ]["application/json"]["schema"]

        assert ok_schema["$ref"] == expected_response_ref
        assert validation_schema["$ref"] == validation_ref
