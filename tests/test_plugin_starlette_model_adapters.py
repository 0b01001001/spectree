from dataclasses import dataclass
from http import HTTPStatus
from typing import Any

import pytest
from starlette.applications import Starlette
from starlette.endpoints import HTTPEndpoint
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from spectree import Response, SpecTree
from spectree.utils import get_model_key
from tests.common_dataclass import Item, LimitQuery, NamePayload


@dataclass(frozen=True)
class StarletteAdapterApp:
    client: TestClient
    spec: SpecTree
    create_item: Any
    endpoint_post: Any


def build_starlette_adapter_app(model_case):
    spec = SpecTree(
        "starlette",
        annotations=True,
        model_adapter=model_case.adapter,
    )

    @spec.validate(
        resp=Response(HTTP_200=model_case.list_of(model_case.get_model(Item)))
    )
    async def create_item(
        request,
        query: model_case.get_model(LimitQuery),
        json: model_case.get_model(NamePayload),
    ):
        return JSONResponse(
            [
                {
                    "name": json.name,
                    "limit": query.limit,
                }
            ]
        )

    class ItemsEndpoint(HTTPEndpoint):
        @spec.validate(
            resp=Response(HTTP_200=model_case.list_of(model_case.get_model(Item)))
        )
        async def post(
            self,
            request,
            query: model_case.get_model(LimitQuery),
            json: model_case.get_model(NamePayload),
        ):
            return JSONResponse(
                [
                    {
                        "name": json.name,
                        "limit": query.limit,
                    }
                ]
            )

    app = Starlette(
        routes=[
            Route("/items", create_item, methods=["POST"]),
            Route("/view-items", ItemsEndpoint),
        ]
    )
    spec.register(app)

    return StarletteAdapterApp(
        client=TestClient(app),
        spec=spec,
        create_item=create_item,
        endpoint_post=ItemsEndpoint.post,
    )


@pytest.fixture
def starlette_adapter_app(model_case):
    adapter_app = build_starlette_adapter_app(model_case)
    with adapter_app.client:
        yield adapter_app


@pytest.mark.parametrize("path", ["/items", "/view-items"])
def test_starlette_model_adapter_validation_flow(starlette_adapter_app, path):
    response = starlette_adapter_app.client.post(
        f"{path}?limit=3",
        json={"name": "demo"},
    )

    assert response.status_code == HTTPStatus.OK
    assert response.json() == [{"name": "demo", "limit": 3}]


@pytest.mark.parametrize("path", ["/items", "/view-items"])
def test_starlette_model_adapter_validation_error(starlette_adapter_app, path):
    response = starlette_adapter_app.client.post(
        f"{path}?limit=bad",
        json={"name": "demo"},
    )

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    errors = response.json()
    assert isinstance(errors, list)
    assert errors[0]["loc"] == ["limit"]
    assert errors[0]["msg"]
    assert errors[0]["type"]


def test_starlette_model_adapter_response_models_and_spec(
    model_case,
    starlette_adapter_app,
):
    expected_list_model = model_case.get_model(list[Item])

    for handler in (
        starlette_adapter_app.create_item,
        starlette_adapter_app.endpoint_post,
    ):
        assert (
            handler.resp.find_model(HTTPStatus.UNPROCESSABLE_ENTITY)
            is starlette_adapter_app.spec.model_adapter.validation_error
        )

        response_model = handler.resp.find_model(HTTPStatus.OK)
        assert get_model_key(response_model) == get_model_key(expected_list_model)

    spec = starlette_adapter_app.spec.spec
    expected_response_ref = f"#/components/schemas/{get_model_key(expected_list_model)}"
    validation_error = starlette_adapter_app.spec.model_adapter.validation_error
    validation_ref = f"#/components/schemas/{get_model_key(validation_error)}"

    for path in ("/items", "/view-items"):
        responses = spec["paths"][path]["post"]["responses"]
        ok_schema = responses[str(HTTPStatus.OK.value)]["content"]["application/json"][
            "schema"
        ]
        validation_schema = responses[str(HTTPStatus.UNPROCESSABLE_ENTITY.value)][
            "content"
        ]["application/json"]["schema"]

        assert ok_schema["$ref"] == expected_response_ref
        assert validation_schema["$ref"] == validation_ref
