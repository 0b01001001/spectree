import importlib
from dataclasses import dataclass
from http import HTTPStatus
from typing import Any, Union

from flask import Blueprint, Flask, current_app, jsonify, make_response, request
from flask.testing import FlaskClient
from flask.views import MethodView
from quart import Quart, jsonify as quart_jsonify

from spectree import Response, SpecTree
from tests.common import (
    UserXmlData,
    api_after_handler,
    api_tag,
    build_security_schemes,
    validation_error_handler as before_handler,
    validation_pass_handler as after_handler,
)
from tests.common_dataclass import (
    Cookies,
    Form,
    FormPayload,
    Item,
    Payload,
    Query,
    QueryList,
    RequiredLimitQuery,
    Resp,
    RespObject,
    ReturnCase,
)

FLASK_BACKEND = "flask"
QUART_BACKEND = "quart"
WERKZEUG_BACKENDS = (FLASK_BACKEND, QUART_BACKEND)
FLASK_USER = "flask"


@dataclass(frozen=True)
class FlaskAdapterApp:
    client: FlaskClient
    spec: SpecTree
    create_item: Any | None = None
    blueprint_create_item: Any | None = None
    view_post: Any | None = None


@dataclass(frozen=True)
class WerkzeugAdapterApp:
    backend: str
    app: Any
    client: Any
    spec: SpecTree


def _dump_headers(model_case, headers: Any) -> dict[str, str]:
    if headers is None:
        return {"lang": request.headers.get("lang", "")}
    return model_case.dump_python(headers)


def _response_score(limit: int, order: int) -> list[int]:
    return sorted([limit, order], reverse=bool(order))


def backend_app(backend: str) -> Any:
    app = Quart(__name__) if backend == QUART_BACKEND else Flask(__name__)
    app.config["TESTING"] = True
    return app


def backend_jsonify(backend: str):
    if backend == QUART_BACKEND:
        return quart_jsonify
    return jsonify


def _register_function_routes(route_app, spec: SpecTree, model_case):  # noqa: PLR0915
    pydantic_only = model_case.name == "pydantic"
    headers_model = None
    if pydantic_only:
        headers_model = importlib.import_module("tests.common_pydantic").Headers

    @route_app.route("/ping")
    @spec.validate(
        headers=headers_model,
        resp=Response(HTTP_202=model_case.get_model(dict[str, str], name="StrDict")),
        tags=["test", "health"],
    )
    def ping():
        """summary

        description"""
        return (
            jsonify(msg="pong"),
            HTTPStatus.ACCEPTED,
            _dump_headers(model_case, request.context.headers),
        )

    @route_app.route("/api/file_upload", methods=["POST"])
    @spec.validate(form=model_case.get_model(FormPayload))
    def file_upload():
        form = request.context.form
        upload = form.file
        assert upload
        return {
            "content": upload.stream.read().decode("utf-8"),
            "other": form.other,
        }

    @route_app.route("/api/user/<name>", methods=["GET"])
    @spec.validate(
        resp=Response(HTTP_200=model_case.get_model(dict[str, str], name="StrDict"))
    )
    def get_user(name):
        return {"name": name}

    @route_app.route("/api/user/<name>", methods=["POST"])
    @spec.validate(
        query=model_case.get_model(Query),
        json=model_case.get_model(Payload),
        cookies=model_case.get_model(Cookies),
        form=model_case.get_model(Form),
        resp=Response(HTTP_200=model_case.get_model(Resp), HTTP_401=None),
        tags=[api_tag, "test"],
        after=api_after_handler,
    )
    def user_score(name):
        data_src = request.context.json or request.context.form
        order = request.context.query.order
        assert request.context.cookies.pub == request.cookies["pub"] == "abcdefg"
        return jsonify(
            name=data_src.name,
            score=_response_score(int(data_src.limit), int(order)),
        )

    @route_app.route("/api/user_annotated/<name>", methods=["POST"])
    @spec.validate(
        resp=Response(HTTP_200=model_case.get_model(Resp), HTTP_401=None),
        tags=[api_tag, "test"],
        after=api_after_handler,
    )
    def user_score_annotated(
        name,
        query: model_case.get_model(Query),
        json: model_case.get_model(Payload),
        form: model_case.get_model(Form),
        cookies: model_case.get_model(Cookies),
    ):
        data_src = json or form
        assert cookies.pub == request.cookies["pub"] == "abcdefg"
        return jsonify(
            name=data_src.name,
            score=_response_score(int(data_src.limit), int(query.order)),
        )

    @route_app.route("/api/user_skip/<name>", methods=["POST"])
    @spec.validate(
        query=model_case.get_model(Query),
        json=model_case.get_model(Payload),
        cookies=model_case.get_model(Cookies),
        resp=Response(HTTP_200=model_case.get_model(Resp), HTTP_401=None),
        tags=[api_tag, "test"],
        after=api_after_handler,
        skip_validation=True,
    )
    def user_score_skip_validation(name):
        response_format = request.args.get("response_format")
        payload = request.get_json()
        score = _response_score(payload.get("limit"), int(request.args.get("order")))
        assert request.cookies["pub"] == "abcdefg"
        if response_format == "json":
            return jsonify(name=payload.get("name"), x_score=score)
        return current_app.response_class(
            UserXmlData(name=payload.get("name"), score=score).dump_xml(),
            content_type="text/xml",
        )

    @route_app.route("/api/user_model/<name>", methods=["POST"])
    @spec.validate(
        query=model_case.get_model(Query),
        json=model_case.get_model(Payload),
        cookies=model_case.get_model(Cookies),
        resp=Response(HTTP_200=model_case.get_model(Resp), HTTP_401=None),
        tags=[api_tag, "test"],
        after=api_after_handler,
    )
    def user_score_model(name):
        assert request.context.cookies.pub == request.cookies["pub"] == "abcdefg"
        return (
            model_case.validate_obj(
                model_case.get_model(Resp),
                {
                    "name": request.context.json.name,
                    "score": _response_score(
                        request.context.json.limit,
                        int(request.context.query.order),
                    ),
                },
            ),
            HTTPStatus.OK,
        )

    @route_app.route("/api/user/<name>/address/<address_id>", methods=["GET"])
    @spec.validate(
        query=model_case.get_model(Query),
        path_parameter_descriptions={
            "name": "The name that uniquely identifies the user.",
            "non-existent-param": "description",
        },
    )
    def user_address(name, address_id):
        return None

    @route_app.route("/api/no_response", methods=["GET"])
    @spec.validate(resp=Response(HTTP_200=None))
    def no_response_get():
        return {}

    @route_app.route("/api/no_response", methods=["POST"])
    @spec.validate(json=model_case.get_model(dict[str, str], name="StrDict"))
    def no_response_post(json: model_case.get_model(dict[str, str], name="StrDict")):
        return {}

    @route_app.route("/api/list_json", methods=["POST"])
    @spec.validate(json=model_case.get_model(list[Payload]))
    def list_json(json: model_case.get_model(list[Payload])):
        return {}

    @route_app.route("/api/set_cookies", methods=["GET"])
    @spec.validate(
        resp=Response(HTTP_200=model_case.get_model(dict[str, str], name="StrDict"))
    )
    def set_cookies():
        response = make_response(jsonify(msg="ping"))
        response.set_cookie("foo", "hello")
        response.set_cookie("bar", "world")
        return response

    @route_app.route("/api/query_list", methods=["GET"])
    @spec.validate(query=model_case.get_model(QueryList))
    def query_list():
        assert request.context.query.ids == [1, 2, 3]
        return {}

    @route_app.route("/api/return_list", methods=["GET"])
    @spec.validate(
        resp=Response(HTTP_200=model_case.list_of(model_case.get_model(Payload)))
    )
    def return_list():
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
        if bool(int(request.args.get("pre_serialize", default=0))):
            return [model_case.dump_python(entry) for entry in data]
        return data

    @route_app.route("/api/return_make_response", methods=["POST"])
    @spec.validate(
        json=model_case.get_model(Payload),
        headers=headers_model,
        resp=Response(HTTP_201=model_case.get_model(Resp)),
    )
    def return_make_response_post():
        model_data = request.context.json
        response = make_response(
            model_case.dump_python(
                model_case.validate_obj(
                    model_case.get_model(Resp),
                    {"name": model_data.name, "score": [model_data.limit]},
                )
            ),
            HTTPStatus.CREATED,
            _dump_headers(model_case, request.context.headers),
        )
        response.set_cookie(
            key="test_cookie",
            value=model_data.name,
            secure=True,
            httponly=True,
            samesite="Strict",
        )
        return response

    @route_app.route("/api/return_make_response", methods=["GET"])
    @spec.validate(
        query=model_case.get_model(Payload),
        headers=headers_model,
        resp=Response(HTTP_201=model_case.get_model(Resp)),
    )
    def return_make_response_get():
        model_data = request.context.query
        response = make_response(
            model_case.dump_python(
                model_case.validate_obj(
                    model_case.get_model(Resp),
                    {"name": model_data.name, "score": [model_data.limit]},
                )
            ),
            HTTPStatus.CREATED,
            _dump_headers(model_case, request.context.headers),
        )
        response.set_cookie(
            key="test_cookie",
            value=model_data.name,
            secure=True,
            httponly=True,
            samesite="Strict",
        )
        return response

    @route_app.route("/api/return_root", methods=["GET"])
    @spec.validate(
        resp=Response(
            HTTP_200=model_case.get_model(Union[Payload, list[int]], name="RootPayload")
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
                model_case.get_model(Union[Payload, list[int]], name="RootPayload"),
                payload_data,
            ),
            ReturnCase.RAW_LIST.value: [1, 2, 3, 4],
            ReturnCase.ROOT_LIST.value: model_case.validate_obj(
                model_case.get_model(Union[Payload, list[int]], name="RootPayload"),
                [1, 2, 3, 4],
            ),
        }
        if bool(int(request.args.get("pre_serialize", default=0))):
            return model_case.dump_python(response_cases[return_case])
        return response_cases[return_case]

    @route_app.route("/api/return_model", methods=["GET"])
    @spec.validate()
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

    @route_app.route("/api/return_string_status", methods=["GET"])
    @spec.validate()
    def return_string_status():
        return "Response text string", HTTPStatus.OK

    @route_app.route("/api/invalid_response", methods=["GET"])
    @spec.validate(resp=Response(HTTP_200=model_case.get_model(Resp)))
    def invalid_response():
        return {}

    @route_app.route("/api/items", methods=["POST"])
    @spec.validate(
        resp=Response(HTTP_200=model_case.list_of(model_case.get_model(Item)))
    )
    def create_item(
        query: model_case.get_model(RequiredLimitQuery),
        json: model_case.get_model(Payload),
    ):
        return [{"name": json.name, "limit": query.limit}]

    if pydantic_only:
        common_pydantic = importlib.import_module("tests.common_pydantic")
        CustomError = common_pydantic.CustomError
        OptionalAliasResp = common_pydantic.OptionalAliasResp
        RespFromAttrs = common_pydantic.RespFromAttrs

        @route_app.route("/api/return_optional_alias", methods=["GET"])
        @spec.validate(resp=Response(HTTP_200=OptionalAliasResp))
        def return_optional_alias():
            return {"schema": "test"}

        @route_app.route("/api/custom_error", methods=["POST"])
        @spec.validate(resp=Response(HTTP_200=CustomError))
        def custom_error(json: CustomError):
            return {"foo": "bar"}

        @route_app.route("/api/force_serialize", methods=["GET"])
        @spec.validate(resp=Response(HTTP_200=RespFromAttrs), force_resp_serialize=True)
        def force_serialize():
            return RespObject(name=FLASK_USER, score=[1, 2, 3], comment="hello")

    return create_item


def _register_blueprint_item_routes(app: Flask, spec: SpecTree, model_case):
    blueprint = Blueprint("adapter_blueprint", __name__)

    @blueprint.route("/items", methods=["POST"])
    @spec.validate(
        resp=Response(HTTP_200=model_case.list_of(model_case.get_model(Item)))
    )
    def create_blueprint_item(
        query: model_case.get_model(RequiredLimitQuery),
        json: model_case.get_model(Payload),
    ):
        return [{"name": json.name, "limit": query.limit}]

    app.register_blueprint(blueprint, url_prefix="/bp")
    return create_blueprint_item


def _register_view_item_routes(app: Flask, spec: SpecTree, model_case):
    class ItemsView(MethodView):
        @spec.validate(
            resp=Response(HTTP_200=model_case.list_of(model_case.get_model(Item)))
        )
        def post(
            self,
            query: model_case.get_model(RequiredLimitQuery),
            json: model_case.get_model(Payload),
        ):
            return [{"name": json.name, "limit": query.limit}]

    app.add_url_rule(
        "/api/view-items",
        view_func=ItemsView.as_view("items_view"),
        methods=["POST"],
    )
    return ItemsView.post


def build_flask_adapter_app(model_case) -> FlaskAdapterApp:
    spec = SpecTree(
        "flask",
        before=before_handler,
        after=after_handler,
        annotations=True,
        model_adapter=model_case.adapter,
    )
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.config["DEBUG"] = True

    create_item = _register_function_routes(app, spec, model_case)
    blueprint_create_item = _register_blueprint_item_routes(app, spec, model_case)
    view_post = _register_view_item_routes(app, spec, model_case)

    with app.app_context():
        _ = spec.spec
    spec.register(app)

    return FlaskAdapterApp(
        client=app.test_client(),
        spec=spec,
        create_item=create_item,
        blueprint_create_item=blueprint_create_item,
        view_post=view_post,
    )


def build_flask_blueprint_adapter_app(
    model_case,
    *,
    url_prefix: str | None = None,
) -> FlaskAdapterApp:
    spec = SpecTree(
        "flask",
        before=before_handler,
        after=after_handler,
        annotations=True,
        model_adapter=model_case.adapter,
    )
    blueprint = Blueprint("test_blueprint_adapter", __name__)
    create_item = _register_function_routes(blueprint, spec, model_case)
    spec.register(blueprint)

    app = Flask(__name__)
    app.config["TESTING"] = True
    app.config["DEBUG"] = True
    app.register_blueprint(blueprint, url_prefix=url_prefix)

    with app.app_context():
        _ = spec.spec

    return FlaskAdapterApp(client=app.test_client(), spec=spec, create_item=create_item)


def build_flask_view_adapter_app(model_case) -> FlaskAdapterApp:
    pydantic_only = model_case.name == "pydantic"
    headers_model = None
    if pydantic_only:
        headers_model = importlib.import_module("tests.common_pydantic").Headers

    spec = SpecTree(
        "flask",
        before=before_handler,
        after=after_handler,
        annotations=True,
        model_adapter=model_case.adapter,
    )
    app = Flask(__name__)
    app.config["TESTING"] = True

    class Ping(MethodView):
        @spec.validate(
            headers=headers_model,
            resp=Response(
                HTTP_202=model_case.get_model(dict[str, str], name="StrDict")
            ),
            tags=["test", "health"],
        )
        def get(self):
            """summary

            description"""
            return (
                jsonify(msg="pong"),
                HTTPStatus.ACCEPTED,
                _dump_headers(model_case, request.context.headers),
            )

    class User(MethodView):
        @spec.validate(
            query=model_case.get_model(Query),
            json=model_case.get_model(Payload),
            form=model_case.get_model(Form),
            cookies=model_case.get_model(Cookies),
            resp=Response(HTTP_200=model_case.get_model(Resp), HTTP_401=None),
            tags=[api_tag, "test"],
            after=api_after_handler,
        )
        def post(self, name):
            data_src = request.context.json or request.context.form
            assert request.context.cookies.pub == request.cookies["pub"] == "abcdefg"
            return jsonify(
                name=data_src.name,
                score=_response_score(
                    int(data_src.limit),
                    int(request.context.query.order),
                ),
            )

    class UserAnnotated(MethodView):
        @spec.validate(
            resp=Response(HTTP_200=model_case.get_model(Resp), HTTP_401=None),
            tags=[api_tag, "test"],
            after=api_after_handler,
        )
        def post(
            self,
            name,
            query: model_case.get_model(Query),
            json: model_case.get_model(Payload),
            form: model_case.get_model(Form),
            cookies: model_case.get_model(Cookies),
        ):
            data_src = json or form
            assert cookies.pub == request.cookies["pub"] == "abcdefg"
            return jsonify(
                name=data_src.name,
                score=_response_score(int(data_src.limit), int(query.order)),
            )

    class UserModel(MethodView):
        @spec.validate(
            query=model_case.get_model(Query),
            json=model_case.get_model(Payload),
            cookies=model_case.get_model(Cookies),
            resp=Response(HTTP_200=model_case.get_model(Resp), HTTP_401=None),
            tags=[api_tag, "test"],
            after=api_after_handler,
        )
        def post(
            self,
            name,
            query: model_case.get_model(Query),
            json: model_case.get_model(Payload),
            cookies: model_case.get_model(Cookies),
        ):
            assert cookies.pub == request.cookies["pub"] == "abcdefg"
            return model_case.validate_obj(
                model_case.get_model(Resp),
                {
                    "name": json.name,
                    "score": _response_score(json.limit, int(query.order)),
                },
            )

    class ItemsView(MethodView):
        @spec.validate(
            resp=Response(HTTP_200=model_case.list_of(model_case.get_model(Item)))
        )
        def post(
            self,
            query: model_case.get_model(RequiredLimitQuery),
            json: model_case.get_model(Payload),
        ):
            return [{"name": json.name, "limit": query.limit}]

    app.add_url_rule("/ping", view_func=Ping.as_view("ping"))
    app.add_url_rule(
        "/api/user/<name>", view_func=User.as_view("user"), methods=["POST"]
    )
    app.add_url_rule(
        "/api/user_annotated/<name>",
        view_func=UserAnnotated.as_view("user_annotated"),
        methods=["POST"],
    )
    app.add_url_rule(
        "/api/user_model/<name>",
        view_func=UserModel.as_view("user_model"),
        methods=["POST"],
    )
    app.add_url_rule(
        "/api/view-items",
        view_func=ItemsView.as_view("items_view"),
        methods=["POST"],
    )

    with app.app_context():
        _ = spec.spec
    spec.register(app)

    return FlaskAdapterApp(
        client=app.test_client(), spec=spec, view_post=ItemsView.post
    )


def build_werkzeug_secure_adapter_app(
    model_case,
    backend: str = FLASK_BACKEND,
) -> WerkzeugAdapterApp:
    spec = SpecTree(
        backend,
        security_schemes=build_security_schemes(model_case),
        model_adapter=model_case.adapter,
    )
    app = backend_app(backend)
    json_response = backend_jsonify(backend)

    @app.route("/no-secure-ping", methods=["GET"])
    @spec.validate(
        resp=Response(HTTP_200=model_case.get_model(dict[str, str], name="StrDict"))
    )
    def no_secure_ping():
        return json_response(msg="pong")

    @app.route("/apiKey-ping", methods=["GET"])
    @spec.validate(
        resp=Response(HTTP_200=model_case.get_model(dict[str, str], name="StrDict")),
        security={"auth_apiKey": []},
    )
    def api_key_ping():
        return json_response(msg="pong")

    @app.route("/apiKey-BasicAuth-ping", methods=["GET"])
    @spec.validate(
        resp=Response(HTTP_200=model_case.get_model(dict[str, str], name="StrDict")),
        security={"auth_apiKey": [], "auth_BasicAuth": []},
    )
    def api_key_basic_auth_ping():
        return json_response(msg="pong")

    @app.route("/BasicAuth-ping", methods=["GET"])
    @spec.validate(
        resp=Response(HTTP_200=model_case.get_model(dict[str, str], name="StrDict")),
        security={"auth_BasicAuth": []},
    )
    def basic_auth_ping():
        return json_response(msg="pong")

    @app.route("/oauth2-flows-ping", methods=["GET"])
    @spec.validate(
        resp=Response(HTTP_200=model_case.get_model(dict[str, str], name="StrDict")),
        security={"auth_oauth2": ["admin", "read"]},
    )
    def oauth_two_ping():
        return json_response(msg="pong")

    spec.register(app)
    return WerkzeugAdapterApp(
        backend=backend,
        app=app,
        client=app.test_client(),
        spec=spec,
    )


def build_flask_secure_adapter_api(model_case) -> SpecTree:
    adapter_app = build_werkzeug_secure_adapter_app(model_case, FLASK_BACKEND)
    with adapter_app.app.app_context():
        _ = adapter_app.spec.spec
    return adapter_app.spec


def build_werkzeug_global_secure_adapter_app(
    model_case,
    backend: str = FLASK_BACKEND,
) -> WerkzeugAdapterApp:
    spec = SpecTree(
        backend,
        security_schemes=build_security_schemes(model_case),
        security={"auth_apiKey": []},
        model_adapter=model_case.adapter,
    )
    app = backend_app(backend)
    json_response = backend_jsonify(backend)

    @app.route("/global-secure-ping", methods=["GET"])
    @spec.validate(
        resp=Response(HTTP_200=model_case.get_model(dict[str, str], name="StrDict"))
    )
    def global_auth_ping():
        return json_response(msg="pong")

    @app.route("/no-secure-override-ping", methods=["GET"])
    @spec.validate(
        security={},
        resp=Response(HTTP_200=model_case.get_model(dict[str, str], name="StrDict")),
    )
    def global_no_secure_ping():
        return json_response(msg="pong")

    @app.route("/oauth2-flows-override-ping", methods=["GET"])
    @spec.validate(
        security={"auth_oauth2": ["admin", "read"]},
        resp=Response(HTTP_200=model_case.get_model(dict[str, str], name="StrDict")),
    )
    def global_oauth_two_ping():
        return json_response(msg="pong")

    @app.route("/security_and", methods=["GET"])
    @spec.validate(
        security={"auth_apiKey": [], "auth_apiKey_backup": []},
        resp=Response(HTTP_200=model_case.get_model(dict[str, str], name="StrDict")),
    )
    def global_security_and():
        return json_response(msg="pong")

    @app.route("/security_or", methods=["GET"])
    @spec.validate(
        security=[{"auth_apiKey": []}, {"auth_apiKey_backup": []}],
        resp=Response(HTTP_200=model_case.get_model(dict[str, str], name="StrDict")),
    )
    def global_security_or():
        return json_response(msg="pong")

    spec.register(app)
    return WerkzeugAdapterApp(
        backend=backend,
        app=app,
        client=app.test_client(),
        spec=spec,
    )


def build_flask_global_secure_adapter_api(model_case) -> SpecTree:
    adapter_app = build_werkzeug_global_secure_adapter_app(model_case, FLASK_BACKEND)
    with adapter_app.app.app_context():
        _ = adapter_app.spec.spec
    return adapter_app.spec


def build_werkzeug_ping_adapter_app(
    backend: str,
    model_case,
    *,
    api_kwargs: dict[str, Any] | None = None,
    endpoint_kwargs: dict[str, Any] | None = None,
) -> WerkzeugAdapterApp:
    spec = SpecTree(
        backend,
        model_adapter=model_case.adapter,
        **(api_kwargs or {}),
    )
    app = backend_app(backend)
    json_response = backend_jsonify(backend)

    @app.route("/ping")
    @spec.validate(**(endpoint_kwargs or {}))
    def ping():
        return json_response(msg="pong")

    spec.register(app)
    return WerkzeugAdapterApp(
        backend=backend,
        app=app,
        client=app.test_client(),
        spec=spec,
    )
