import importlib
from dataclasses import dataclass
from random import randint
from typing import Any, Union

import pytest
from quart import Quart, jsonify, request

from spectree import Response, SpecTree
from tests.common import (
    UserXmlData,
    api_after_handler,
    api_tag,
    validation_error_handler as before_handler,
    validation_pass_handler as after_handler,
)
from tests.common_dataclass import (
    Cookies,
    Order,
    Payload,
    Query,
    Resp,
    RespObject,
    ReturnCase,
)
from tests.model_cases import PYDANTIC_MODEL_CASE_PARAMS

pytestmark = pytest.mark.anyio
QUART_USER = "quart"


@dataclass(frozen=True)
class QuartAdapterApp:
    client: Any
    spec: SpecTree


def _score(limit: int, order: Order | int) -> list[int]:
    score = [randint(0, limit) for _ in range(5)]
    score.sort(reverse=(order == Order.desc or order == int(Order.desc)))
    return score


def build_quart_adapter_app(model_case) -> QuartAdapterApp:
    pydantic_only = model_case.name == "pydantic"
    headers_model = None
    if pydantic_only:
        headers_model = importlib.import_module("tests.common_pydantic").Headers

    api = SpecTree(
        "quart",
        before=before_handler,
        after=after_handler,
        annotations=True,
        model_adapter=model_case.adapter,
    )
    app = Quart(__name__)
    app.config["TESTING"] = True

    @app.route("/ping")
    @api.validate(
        headers=headers_model,
        resp=Response(HTTP_200=model_case.get_model(dict[str, str], name="StrDict")),
        tags=["test", "health"],
    )
    async def ping():
        """summary

        description"""
        return jsonify(msg="pong"), 202

    @app.route("/api/user/<name>", methods=["POST"])
    @api.validate(
        query=model_case.get_model(Query),
        json=model_case.get_model(Payload),
        cookies=model_case.get_model(Cookies),
        resp=Response(HTTP_200=model_case.get_model(Resp), HTTP_401=None),
        tags=[api_tag, "test"],
        after=api_after_handler,
    )
    async def user_score(name):
        assert request.context.cookies.pub == "abcdefg"
        assert request.cookies["pub"] == "abcdefg"
        return jsonify(
            name=request.context.json.name,
            score=_score(request.context.json.limit, request.context.query.order),
        )

    @app.route("/api/user_annotated/<name>", methods=["POST"])
    @api.validate(
        resp=Response(HTTP_200=model_case.get_model(Resp), HTTP_401=None),
        tags=[api_tag, "test"],
        after=api_after_handler,
    )
    async def user_score_annotated(
        name,
        query: model_case.get_model(Query),
        json: model_case.get_model(Payload),
        cookies: model_case.get_model(Cookies),
    ):
        assert cookies.pub == "abcdefg"
        assert request.cookies["pub"] == "abcdefg"
        return jsonify(name=json.name, score=_score(json.limit, query.order))

    @app.route("/api/user_skip/<name>", methods=["POST"])
    @api.validate(
        query=model_case.get_model(Query),
        json=model_case.get_model(Payload),
        cookies=model_case.get_model(Cookies),
        resp=Response(HTTP_200=model_case.get_model(Resp), HTTP_401=None),
        tags=[api_tag, "test"],
        after=api_after_handler,
        skip_validation=True,
    )
    async def user_score_skip_validation(name):
        response_format = request.args.get("response_format")
        assert response_format in ("json", "xml")
        payload = await request.get_json()
        score = _score(payload.get("limit"), int(request.args.get("order")))
        assert request.cookies["pub"] == "abcdefg"
        if response_format == "json":
            return jsonify(name=payload.get("name"), x_score=score)
        return app.response_class(
            response=UserXmlData(name=payload.get("name"), score=score).dump_xml(),
            content_type="text/xml",
        )

    @app.route("/api/user_model/<name>", methods=["POST"])
    @api.validate(
        query=model_case.get_model(Query),
        json=model_case.get_model(Payload),
        cookies=model_case.get_model(Cookies),
        resp=Response(HTTP_200=model_case.get_model(Resp), HTTP_401=None),
        tags=[api_tag, "test"],
        after=api_after_handler,
    )
    async def user_score_model(name):
        assert request.context.cookies.pub == "abcdefg"
        assert request.cookies["pub"] == "abcdefg"
        return (
            model_case.validate_obj(
                model_case.get_model(Resp),
                {
                    "name": request.context.json.name,
                    "score": _score(
                        request.context.json.limit,
                        request.context.query.order,
                    ),
                },
            ),
            200,
        )

    @app.route("/api/user/<name>/address/<address_id>", methods=["GET"])
    @api.validate(
        query=model_case.get_model(Query),
        path_parameter_descriptions={
            "name": "The name that uniquely identifies the user.",
            "non-existent-param": "description",
        },
    )
    async def user_address(name, address_id):
        return None

    @app.route("/api/no_response", methods=["GET", "POST"])
    @api.validate(json=model_case.get_model(Payload))
    async def no_response():
        return {}

    @app.route("/api/list_json", methods=["POST"])
    @api.validate(json=model_case.get_model(list[Payload], name="ListPayload"))
    async def list_json():
        return {}

    @app.route("/api/return_list")
    @api.validate(
        resp=Response(HTTP_200=model_case.list_of(model_case.get_model(Payload)))
    )
    def return_list():
        pre_serialize = bool(int(request.args.get("pre_serialize", default=0)))
        data = [
            model_case.validate_obj(
                model_case.get_model(Payload),
                {"name": "user1", "limit": 1},
            ),
            model_case.validate_obj(
                model_case.get_model(Payload),
                {"name": "user2", "limit": 2},
            ),
        ]
        return [
            model_case.dump_python(entry) if pre_serialize else entry for entry in data
        ]

    @app.route("/api/return_root", methods=["GET"])
    @api.validate(
        resp=Response(
            HTTP_200=model_case.get_model(Union[Payload, list[int]], name="RootResp")
        )
    )
    def return_root():
        return_case = request.args.get("return_case", ReturnCase.ROOT_MODEL.value)
        payload_data = {"name": "user1", "limit": 1}
        response_cases = {
            ReturnCase.PAYLOAD.value: payload_data,
            ReturnCase.MODEL.value: model_case.validate_obj(
                model_case.get_model(Payload),
                payload_data,
            ),
            ReturnCase.ROOT_MODEL.value: model_case.validate_obj(
                model_case.get_model(Union[Payload, list[int]], name="RootResp"),
                payload_data,
            ),
            ReturnCase.RAW_LIST.value: [1, 2, 3, 4],
            ReturnCase.ROOT_LIST.value: model_case.validate_obj(
                model_case.get_model(Union[Payload, list[int]], name="RootResp"),
                [1, 2, 3, 4],
            ),
        }
        response = response_cases[return_case]
        if bool(int(request.args.get("pre_serialize", default=0))):
            return model_case.dump_python(response)
        return response

    @app.route("/api/return_model", methods=["GET"])
    @api.validate()
    def return_model():
        return_case = request.args.get("return_case", ReturnCase.MODEL.value)
        payload_data = {"name": "user1", "limit": 1}
        response_cases = {
            ReturnCase.PAYLOAD.value: payload_data,
            ReturnCase.MODEL.value: model_case.validate_obj(
                model_case.get_model(Payload),
                payload_data,
            ),
            ReturnCase.RAW_LIST.value: [1, 2, 3, 4],
            ReturnCase.MODEL_LIST.value: [
                model_case.validate_obj(model_case.get_model(Payload), payload_data)
            ],
        }
        return response_cases[return_case]

    @app.route("/api/return_string_status", methods=["GET"])
    @api.validate()
    def return_string_status():
        return "Response text string", 200

    if pydantic_only:
        common_pydantic = importlib.import_module("tests.common_pydantic")
        CustomError = common_pydantic.CustomError
        RespFromAttrs = common_pydantic.RespFromAttrs

        @app.route("/api/custom_error", methods=["POST"])
        @api.validate(resp=Response(HTTP_200=CustomError))
        def custom_error(json: CustomError):
            return jsonify(foo="bar")

        @app.route("/api/force_serialize", methods=["GET"])
        @api.validate(resp=Response(HTTP_200=RespFromAttrs), force_resp_serialize=True)
        def force_serialize():
            return RespObject(name="flask", score=[1, 2, 3], comment="hello")

    api.register(app)
    return QuartAdapterApp(client=app.test_client(), spec=api)


@pytest.fixture
def quart_adapter_app(model_case):
    return build_quart_adapter_app(model_case)


@pytest.fixture
def client(quart_adapter_app):
    return quart_adapter_app.client


@pytest.mark.parametrize("model_case", PYDANTIC_MODEL_CASE_PARAMS, indirect=True)
async def test_quart_pydantic_header_validation_preserves_existing_behavior(client):
    resp = await client.get("/ping")
    assert resp.status_code == 422
    assert resp.headers.get("X-Error") == "Validation Error"

    resp = await client.get("/ping", headers={"lang": "en-US"})
    resp_json = await resp.json
    assert resp_json == {"msg": "pong"}
    assert resp.headers.get("X-Error") is None
    assert resp.headers.get("X-Validation") == "Pass"


@pytest.mark.parametrize("response_format", ["json", "xml"])
async def test_quart_model_adapter_skip_validation(client, response_format: str):
    client.set_cookie(
        "quart", "pub", "abcdefg", secure=True, httponly=True, samesite="Strict"
    )

    resp = await client.post(
        f"/api/user_skip/{QUART_USER}?order=1&response_format={response_format}",
        json={"name": QUART_USER, "limit": 10},
        headers={"Content-Type": "application/json"},
    )
    assert resp.status_code == 200
    assert resp.headers.get("X-Validation") is None
    assert resp.headers.get("X-API") == "OK"
    if response_format == "json":
        resp_json = await resp.json
        assert resp.content_type == "application/json"
        assert resp_json["name"] == QUART_USER
        assert resp_json["x_score"] == sorted(resp_json["x_score"], reverse=True)
    else:
        assert resp.content_type == "text/xml"
        user_xml_data = UserXmlData.parse_xml(await resp.get_data(as_text=True))
        assert user_xml_data.name == QUART_USER
        assert user_xml_data.score == sorted(user_xml_data.score, reverse=True)


async def test_quart_model_adapter_model_instance_response(client):
    client.set_cookie(
        "quart", "pub", "abcdefg", secure=True, httponly=True, samesite="Strict"
    )

    resp = await client.post(
        f"/api/user_model/{QUART_USER}?order=1",
        json={"name": QUART_USER, "limit": 10},
        headers={"Content-Type": "application/json"},
    )
    resp_json = await resp.json
    assert resp.status_code == 200, resp_json
    assert resp.headers.get("X-Validation") is None
    assert resp.headers.get("X-API") == "OK"
    assert resp_json["name"] == QUART_USER
    assert resp_json["score"] == sorted(resp_json["score"], reverse=True)


async def test_quart_model_adapter_return_string_status(client):
    resp = await client.get("/api/return_string_status")
    assert resp.status_code == 200
    text = await resp.get_data(as_text=True)
    assert text == "Response text string"


async def test_quart_model_adapter_rejects_invalid_payload(client):
    resp = await client.post(f"api/user/{QUART_USER}")
    assert resp.status_code == 422
    assert resp.headers.get("X-Error") == "Validation Error"


@pytest.mark.parametrize("fragment", ["user", "user_annotated"])
async def test_quart_model_adapter_validation_flow(client, fragment):
    client.set_cookie(
        "quart", "pub", "abcdefg", secure=True, httponly=True, samesite="Strict"
    )

    resp = await client.post(
        f"/api/{fragment}/{QUART_USER}?order=1",
        json={"name": QUART_USER, "limit": 10},
        headers={"Content-Type": "application/json"},
    )
    resp_json = await resp.json
    assert resp.status_code == 200, resp_json
    assert resp.headers.get("X-Validation") is None
    assert resp.headers.get("X-API") == "OK"
    assert resp_json["name"] == QUART_USER
    assert resp_json["score"] == sorted(resp_json["score"], reverse=True)

    resp = await client.post(
        f"/api/{fragment}/{QUART_USER}?order=0",
        json={"name": QUART_USER, "limit": 10},
        headers={"Content-Type": "application/json"},
    )
    resp_json = await resp.json
    assert resp.status_code == 200, resp_json
    assert resp_json["score"] == sorted(resp_json["score"], reverse=False)


async def test_quart_model_adapter_no_response(client):
    resp = await client.get("/api/no_response")
    assert resp.status_code == 200

    resp = await client.post("/api/no_response", json={"name": "foo", "limit": 1})
    assert resp.status_code == 200


async def test_quart_model_adapter_list_json_request(client):
    resp = await client.post("/api/list_json", json=[{"name": "foo", "limit": 1}])
    assert resp.status_code == 200


@pytest.mark.parametrize("pre_serialize", [False, True])
async def test_quart_model_adapter_return_list(client, pre_serialize: bool):
    resp = await client.get(f"/api/return_list?pre_serialize={int(pre_serialize)}")
    assert resp.status_code == 200
    json_data = await resp.json
    assert json_data == [
        {"name": "user1", "limit": 1},
        {"name": "user2", "limit": 2},
    ]


@pytest.mark.parametrize(
    "return_case, expected_payload",
    [
        pytest.param(ReturnCase.PAYLOAD, {"name": "user1", "limit": 1}, id="payload"),
        pytest.param(ReturnCase.MODEL, {"name": "user1", "limit": 1}, id="model"),
        pytest.param(
            ReturnCase.ROOT_MODEL,
            {"name": "user1", "limit": 1},
            id="root-model",
        ),
        pytest.param(ReturnCase.RAW_LIST, [1, 2, 3, 4], id="raw-list"),
        pytest.param(ReturnCase.ROOT_LIST, [1, 2, 3, 4], id="root-list"),
    ],
)
@pytest.mark.parametrize("pre_serialize", [False, True])
async def test_quart_model_adapter_return_root(
    client,
    return_case,
    expected_payload,
    pre_serialize,
):
    resp = await client.get(
        "/api/return_root"
        f"?return_case={return_case.value}&pre_serialize={int(pre_serialize)}"
    )
    assert resp.status_code == 200
    assert await resp.json == expected_payload


@pytest.mark.parametrize(
    "return_case, expected_payload",
    [
        pytest.param(ReturnCase.PAYLOAD, {"name": "user1", "limit": 1}, id="payload"),
        pytest.param(ReturnCase.MODEL, {"name": "user1", "limit": 1}, id="model"),
        pytest.param(ReturnCase.RAW_LIST, [1, 2, 3, 4], id="raw-list"),
        pytest.param(
            ReturnCase.MODEL_LIST,
            [{"name": "user1", "limit": 1}],
            id="model-list",
        ),
    ],
)
async def test_quart_model_adapter_return_model_without_response_model(
    client,
    return_case,
    expected_payload,
):
    resp = await client.get(f"/api/return_model?return_case={return_case.value}")
    assert resp.status_code == 200
    assert await resp.json == expected_payload


@pytest.mark.parametrize("model_case", PYDANTIC_MODEL_CASE_PARAMS, indirect=True)
async def test_quart_pydantic_custom_error(client):
    resp = await client.post("/api/custom_error", json={"foo": "bar"})
    assert resp.status_code == 422

    resp = await client.post("/api/custom_error", json={"foo": "foo"})
    assert resp.status_code == 500


@pytest.mark.parametrize("model_case", PYDANTIC_MODEL_CASE_PARAMS, indirect=True)
async def test_quart_pydantic_force_serializer(client):
    resp = await client.get("/api/force_serialize")
    assert resp.status_code == 200
    json_data = await resp.json
    assert json_data["name"] == "flask"
    assert json_data["score"] == [1, 2, 3]
    assert "comment" not in json_data
