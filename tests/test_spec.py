import gc
import sys
import warnings
import weakref
from dataclasses import dataclass
from decimal import Decimal
from functools import wraps
from importlib import import_module
from typing import Annotated

import pytest
from falcon import App as FalconApp
from flask import Flask, request as flask_request
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.testclient import TestClient as StarletteTestClient

from spectree import Response
from spectree.config import Configuration
from spectree.model_adapter import get_msgspec_model_adapter, get_pydantic_model_adapter
from spectree.models import Server
from spectree.plugins.base import BasePlugin
from spectree.plugins.flask_plugin import FlaskPlugin
from spectree.spec import SpecTree
from spectree.utils import get_model_key
from tests.common import assert_component_refs_resolve, get_paths
from tests.common_dataclass import (
    Child,
    Cookies,
    DemoModel,
    Form,
    Headers,
    Parent,
    Payload,
    Query,
    Resp,
)
from tests.type_checking_annotation_case import type_checking_view_func


def backend_app():
    return [
        ("flask", lambda: Flask(__name__)),
        ("falcon", FalconApp),
        ("starlette", Starlette),
    ]


def _get_spec(name, app, model_case, **kwargs):
    api = SpecTree(
        name,
        app=app,
        title=f"{name}",
        model_adapter=model_case.adapter,
        **kwargs,
    )
    if name == "flask":
        with app.app_context():
            spec = api.spec
    else:
        spec = api.spec

    return spec


def test_spectree_init(model_case):
    spec = SpecTree(path="docs", model_adapter=model_case.adapter)
    conf = Configuration()

    assert spec.config.title == conf.title
    assert spec.config.path == "docs"

    with pytest.raises(NotImplementedError):
        SpecTree(app=conf, model_adapter=model_case.adapter)


@pytest.mark.parametrize("name, app_factory", backend_app())
def test_register(name, app_factory, model_case):
    app = app_factory()
    api = SpecTree(name, model_adapter=model_case.adapter)
    api.register(app)


@pytest.mark.parametrize("name, app_factory", backend_app())
def test_spec_generate(name, app_factory, model_case):
    app = app_factory()
    spec = _get_spec(name, app, model_case)

    assert spec["info"]["title"] == name
    assert spec["paths"] == {}


@pytest.mark.pydantic
def test_annotations_ignore_unresolvable_return_annotation():
    app = Flask(__name__)
    api = SpecTree(
        "flask",
        model_adapter=get_pydantic_model_adapter(),
    )

    decorated = api.validate()(type_checking_view_func)
    app.add_url_rule(
        "/type-checking",
        view_func=decorated,
        methods=["POST"],
    )

    api.register(app)

    with app.app_context():
        spec = api.spec

    operation = spec["paths"]["/type-checking"]["post"]
    assert operation["requestBody"]["content"]["application/json"]["schema"] == {
        "$ref": f"#/components/schemas/{get_model_key(DemoModel)}"
    }


@pytest.mark.pydantic
def test_skip_validation_only_warns_for_request_annotations():
    api = SpecTree(
        "flask",
        model_adapter=get_pydantic_model_adapter(),
    )

    with pytest.warns(UserWarning, match="skip_validation"):

        @api.validate(skip_validation=True)
        def annotated(query: Query):
            return query

    with warnings.catch_warnings(record=True) as captured:
        warnings.simplefilter("always")

        @api.validate(query=Query, skip_validation=True)
        def explicit_model():
            return None

    assert not captured
    assert annotated
    assert explicit_model


@pytest.mark.parametrize("name, app_factory", backend_app())
def test_spec_servers_empty(name, app_factory, model_case):
    app = app_factory()
    spec = _get_spec(name, app, model_case)

    assert "servers" not in spec


@pytest.mark.parametrize("name, app_factory", backend_app())
def test_spec_servers_only(name, app_factory, model_case):
    app = app_factory()
    server1_url = "http://example.com/bar"
    server2_url = "https://example.com/foo/bar"
    spec = _get_spec(
        name,
        app,
        model_case,
        servers=[Server(url=server1_url), Server(url=server2_url)],
    )

    assert spec["servers"] == [
        {"url": server1_url},
        {"url": server2_url},
    ]


@pytest.mark.parametrize("name, app_factory", backend_app())
def test_spec_servers_full(name, app_factory, model_case):
    app = app_factory()
    server1 = {"url": "http://foo/bar", "description": "Foo Bar"}
    server2 = {"url": "http://bar/foo/{lang}", "variables": {"lang": "en"}}
    spec = _get_spec(
        name,
        app,
        model_case,
        servers=[
            Server(**server1),
            Server(**server2),
        ],
    )

    expected = []
    for server in [server1, server2]:
        expected_item = {
            "url": server.get("url"),
        }
        description = server.get("description", None)
        if description:
            expected_item["description"] = description
        variables = server.get("variables", None)
        if variables:
            expected_item["variables"] = variables
        expected.append(expected_item)

    assert spec["servers"] == expected


def create_app(model_case):
    api = SpecTree("flask", model_adapter=model_case.adapter)
    api_strict = SpecTree(
        "flask",
        mode="strict",
        model_adapter=model_case.adapter,
    )
    api_greedy = SpecTree(
        "flask",
        mode="greedy",
        model_adapter=model_case.adapter,
    )
    api_customize_backend = SpecTree(
        backend=FlaskPlugin,
        model_adapter=model_case.adapter,
    )
    app = Flask(__name__)

    @app.route("/foo")
    @api.validate()
    def foo():
        pass

    @app.route("/bar")
    @api_strict.validate()
    def bar():
        pass

    @app.route("/lone", methods=["GET"])
    def lone_get():
        pass

    @app.route("/lone", methods=["POST"])
    def lone_post():
        pass

    return app, api, api_strict, api_greedy, api_customize_backend


def test_spec_bypass_mode(model_case):
    app, api, api_strict, api_greedy, api_customize_backend = create_app(model_case)
    api.register(app)
    with app.app_context():
        assert get_paths(api.spec) == ["/foo", "/lone"]

    app, api, api_strict, api_greedy, api_customize_backend = create_app(model_case)
    api_customize_backend.register(app)
    with app.app_context():
        assert get_paths(api.spec) == ["/foo", "/lone"]

    app, api, api_strict, api_greedy, api_customize_backend = create_app(model_case)
    api_greedy.register(app)
    with app.app_context():
        assert get_paths(api_greedy.spec) == ["/bar", "/foo", "/lone"]

    app, api, api_strict, api_greedy, api_customize_backend = create_app(model_case)
    api_strict.register(app)
    with app.app_context():
        assert get_paths(api_strict.spec) == ["/bar"]


def test_function_metadata_does_not_retain_spectree(model_case):
    def create_registered_api():
        app = Flask(__name__)
        api = SpecTree("flask", model_adapter=model_case.adapter)

        @app.route("/foo")
        @api.validate()
        def foo():
            pass

        api.register(app)
        assert api.get_function_metadata(foo) is not None
        return weakref.ref(api), weakref.ref(foo)

    api_ref, func_ref = create_registered_api()
    gc.collect()

    assert api_ref() is None
    assert func_ref() is None


def test_function_metadata_handles_wrapped_and_non_weakrefable_callables(model_case):
    api = SpecTree(model_adapter=model_case.adapter)

    @api.validate()
    def endpoint():
        pass

    @wraps(endpoint)
    def wrapped_endpoint():
        return endpoint()

    assert api.get_function_metadata(wrapped_endpoint) is not None
    assert not api.bypass(wrapped_endpoint)
    assert not api.bypass(len)

    strict_api = SpecTree(mode="strict", model_adapter=model_case.adapter)
    assert strict_api.bypass(wrapped_endpoint)
    assert strict_api.bypass(len)


def test_two_endpoints_with_the_same_path(model_case):
    app, api, _, _, _ = create_app(model_case)
    api.register(app)
    with app.app_context():
        spec = api.spec

    http_methods = list(spec["paths"]["/lone"].keys())
    http_methods.sort()
    assert http_methods == ["get", "post"]


def test_model_for_validation_errors_specified(model_case):
    @dataclass
    class CustomValidationError:
        user_id: int

    api = SpecTree("flask", model_adapter=model_case.adapter)
    app = Flask(__name__)
    custom_validation_error = model_case.get_model(CustomValidationError)

    @app.route("/foo")
    @api.validate(resp=Response(HTTP_200=None))
    def foo():
        pass

    @app.route("/bar")
    @api.validate(resp=Response(HTTP_200=None, HTTP_422=custom_validation_error))
    def bar():
        pass

    api.register(app)

    assert (
        api.get_function_metadata(foo).resp.find_model(422)
        is api.model_adapter.validation_error
    )
    assert (
        api.get_function_metadata(bar).resp.find_model(422) is custom_validation_error
    )


def test_global_model_for_validation_errors_specified(model_case):
    @dataclass
    class GlobalValidationError:
        user_id: int

    @dataclass
    class RouteValidationError:
        user_id: int

    global_validation_error = model_case.get_model(GlobalValidationError)
    route_validation_error = model_case.get_model(RouteValidationError)

    api = SpecTree(
        "flask",
        validation_error_model=global_validation_error,
        model_adapter=model_case.adapter,
    )
    app = Flask(__name__)

    @app.route("/foo")
    @api.validate(resp=Response(HTTP_200=None))
    def foo():
        pass

    @app.route("/bar")
    @api.validate(resp=Response(HTTP_200=None, HTTP_422=route_validation_error))
    def bar():
        pass

    api.register(app)

    assert (
        api.get_function_metadata(foo).resp.find_model(422) is global_validation_error
    )
    assert api.get_function_metadata(bar).resp.find_model(422) is route_validation_error


def test_plain_dataclass_models_are_supported_for_all_api_parts(model_case):
    api = SpecTree("flask", model_adapter=model_case.adapter)
    app = Flask(__name__)

    @app.route("/items", methods=["POST"])
    @api.validate(
        query=Query,
        json=Payload,
        form=Form,
        headers=Headers,
        cookies=Cookies,
        resp=Response(HTTP_200=Resp),
    )
    def create_item():
        pass

    api.register(app)
    with app.app_context():
        operation = api.spec["paths"]["/items"]["post"]

    assert operation["requestBody"]["content"]["application/json"]["schema"] == {
        "$ref": f"#/components/schemas/{get_model_key(Payload)}"
    }
    assert operation["requestBody"]["content"]["multipart/form-data"]["schema"] == {
        "$ref": f"#/components/schemas/{get_model_key(Form)}"
    }
    assert operation["responses"]["200"]["content"]["application/json"]["schema"] == {
        "$ref": f"#/components/schemas/{get_model_key(Resp)}"
    }
    assert {parameter["in"] for parameter in operation["parameters"]} == {
        "query",
        "header",
        "cookie",
    }


def test_annotations_preserve_named_root_model_metadata(model_case):
    api = SpecTree("flask", annotations=True, model_adapter=model_case.adapter)
    app = Flask(__name__)

    @app.route("/annotated", methods=["POST"])
    @api.validate(resp=Response(HTTP_200=None))
    def annotated(json: model_case.get_model(dict[str, str], name="NamedDict")):
        return {}

    api.register(app)
    with app.app_context():
        spec = api.spec

    named_model = model_case.get_model(dict[str, str], name="NamedDict")
    schema = spec["paths"]["/annotated"]["post"]["requestBody"]["content"][
        "application/json"
    ]["schema"]
    assert schema["$ref"] == f"#/components/schemas/{get_model_key(named_model)}"


@pytest.mark.parametrize(
    ["override_operation_id", "expected_operation_id"],
    [(None, "get__foo"), ("getFoo", "getFoo")],
)
def test_operation_id_override(
    override_operation_id, expected_operation_id, model_case
):
    api = SpecTree("flask", model_adapter=model_case.adapter)
    app = Flask(__name__)

    @app.route("/foo")
    @api.validate(operation_id=override_operation_id)
    def foo():
        pass

    api.register(app)

    with app.app_context():
        operation_id = api.spec["paths"]["/foo"]["get"]["operationId"]
        assert operation_id == expected_operation_id


def test_custom_model_naming_strategies_are_used_in_refs_and_components(model_case):
    @dataclass
    class Payload:
        child: Child

    @dataclass
    class Result:
        child: Child

    api = SpecTree(
        "flask",
        naming_strategy=lambda model: model.__name__.lower(),
        nested_naming_strategy=lambda _parent, child: child.lower(),
        model_adapter=model_case.adapter,
    )
    app = Flask(__name__)

    @app.route("/items", methods=["POST"])
    @api.validate(
        json=model_case.get_model(Payload),
        resp=Response(HTTP_200=model_case.get_model(Result)),
    )
    def create_item():
        pass

    api.register(app)

    with app.app_context():
        spec = api.spec

    operation = spec["paths"]["/items"]["post"]
    schemas = spec["components"]["schemas"]

    assert operation["requestBody"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/payload"
    }
    assert operation["responses"]["200"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/result"
    }
    assert schemas["payload"]["properties"]["child"] == {
        "$ref": "#/components/schemas/child"
    }
    assert schemas["result"]["properties"]["child"] == {
        "$ref": "#/components/schemas/child"
    }
    assert schemas["validationerror"]["items"] == {
        "$ref": "#/components/schemas/validationerrorelement"
    }
    assert "Child" not in schemas
    assert "child" in schemas


def _json_schema_ref(operation):
    return operation["requestBody"]["content"]["application/json"]["schema"]["$ref"]


def _response_schema_ref(operation, code="200"):
    return operation["responses"][code]["content"]["application/json"]["schema"]["$ref"]


def _component_name(ref):
    return ref.removeprefix("#/components/schemas/")


@dataclass
class FirstBody:
    a: int


@dataclass
class SecondBody:
    b: str


def test_reused_validate_decorator_resolves_models_per_function(model_case):
    api = SpecTree("flask", model_adapter=model_case.adapter)
    app = Flask(__name__)
    first_model = model_case.get_model(FirstBody)
    second_model = model_case.get_model(SecondBody)
    decorator = api.validate()

    @app.post("/first")
    @decorator
    def first(json: first_model):
        return {"a": json.a}

    @app.post("/untyped")
    @decorator
    def untyped():
        return {"ok": True}

    @app.post("/second")
    @decorator
    def second(json: second_model):
        return {"b": json.b}

    api.register(app)
    client = app.test_client()

    assert client.post("/first", json={"a": 1}).json == {"a": 1}
    assert client.post("/first", json={"b": "x"}).status_code == 422
    assert client.post("/untyped").json == {"ok": True}
    assert client.post("/second", json={"b": "x"}).json == {"b": "x"}

    with app.app_context():
        paths = api.spec["paths"]
    assert "requestBody" not in paths["/untyped"]["post"]
    assert _component_name(_json_schema_ref(paths["/first"]["post"])) == (
        get_model_key(first_model)
    )
    assert _component_name(_json_schema_ref(paths["/second"]["post"])) == (
        get_model_key(second_model)
    )


def test_spec_is_regenerated_for_endpoints_decorated_after_first_access(model_case):
    api = SpecTree("flask", model_adapter=model_case.adapter)
    app = Flask(__name__)
    parent = model_case.get_model(Parent)

    @app.post("/early")
    @api.validate(json=parent)
    def early():
        return {}

    api.register(app)
    with app.app_context():
        first = api.spec
        assert api.spec is first

        @app.post("/late")
        @api.validate(json=parent)
        def late():
            return {}

        second = api.spec

    assert get_paths(first) == ["/early"]
    assert get_paths(second) == ["/early", "/late"]
    # nested components survive any number of generations
    assert len(second["components"]["schemas"]) > 1
    assert second["components"]["schemas"] == first["components"]["schemas"]
    assert_component_refs_resolve(second)


def test_response_declaration_is_shared_without_being_modified(model_case):
    resp_model = model_case.get_model(Resp)
    shared = Response("HTTP_201", HTTP_200=resp_model)
    first = SpecTree("flask", model_adapter=model_case.adapter)
    second = SpecTree(
        "flask", model_adapter=model_case.adapter, validation_error_status=400
    )

    first_endpoint = first.validate(resp=shared)(lambda: None)
    second_endpoint = second.validate(resp=shared)(lambda: None)

    assert shared.model_adapter is None
    assert shared.codes == ["HTTP_201"]
    assert shared.code_models == {}
    assert first.get_function_metadata(first_endpoint).resp.find_model(400) is None
    assert set(first.get_function_metadata(first_endpoint).resp.code_models) == {
        "HTTP_200",
        "HTTP_422",
    }
    assert set(second.get_function_metadata(second_endpoint).resp.code_models) == {
        "HTTP_200",
        "HTTP_400",
    }


@pytest.mark.pydantic
@pytest.mark.msgspec
def test_response_declaration_can_be_shared_by_different_model_adapters():
    pytest.importorskip("pydantic")
    pytest.importorskip("msgspec")
    shared = Response(HTTP_200=Resp)

    for adapter in (get_pydantic_model_adapter(), get_msgspec_model_adapter()):
        api = SpecTree("flask", model_adapter=adapter)
        app = Flask(__name__)

        @app.get("/resp")
        @api.validate(resp=shared)
        def resp():
            return {"name": "spectree", "score": [1]}

        api.register(app)
        with app.app_context():
            spec = api.spec
        assert app.test_client().get("/resp").status_code == 200
        assert_component_refs_resolve(spec)


@pytest.mark.pydantic
@pytest.mark.parametrize("response_first", [False, True])
def test_request_and_response_schemas_of_one_model_are_documented_separately(
    response_first,
):
    pydantic = pytest.importorskip("pydantic")

    class Item(pydantic.BaseModel):
        name: str

        @pydantic.computed_field
        @property
        def upper(self) -> str:
            return self.name.upper()

    api = SpecTree("flask")
    app = Flask(__name__)

    def add_request_endpoint():
        @app.post("/items")
        @api.validate(json=Item)
        def create():
            return {}

    def add_response_endpoint():
        @app.get("/items")
        @api.validate(resp=Response(HTTP_200=Item))
        def read():
            return Item(name="spectree")

    for add_endpoint in (
        (add_response_endpoint, add_request_endpoint)
        if response_first
        else (add_request_endpoint, add_response_endpoint)
    ):
        add_endpoint()
    api.register(app)

    with app.app_context():
        spec = api.spec
    schemas = spec["components"]["schemas"]
    key = get_model_key(Item)
    request_ref = _json_schema_ref(spec["paths"]["/items"]["post"])
    response_ref = _response_schema_ref(spec["paths"]["/items"]["get"])

    assert _component_name(request_ref) == key
    assert _component_name(response_ref) == f"{key}.serialization"
    assert set(schemas[key]["properties"]) == {"name"}
    assert set(schemas[f"{key}.serialization"]["properties"]) == {"name", "upper"}
    assert app.test_client().get("/items").json == {
        "name": "spectree",
        "upper": "SPECTREE",
    }
    assert_component_refs_resolve(spec)


def test_identical_request_and_response_schemas_share_one_component(model_case):
    api = SpecTree("flask", model_adapter=model_case.adapter)
    app = Flask(__name__)
    payload = model_case.get_model(Payload)

    @app.post("/items")
    @api.validate(json=payload, resp=Response(HTTP_200=payload))
    def create():
        return {}

    api.register(app)
    with app.app_context():
        spec = api.spec
    operation = spec["paths"]["/items"]["post"]
    key = get_model_key(payload)

    assert _component_name(_json_schema_ref(operation)) == key
    assert _component_name(_response_schema_ref(operation)) == key
    assert f"{key}.serialization" not in spec["components"]["schemas"]


def _titled(model_case, model, title):
    if model_case.name == "pydantic":
        return Annotated[model, import_module("pydantic").Field(title=title)]
    return Annotated[model, import_module("msgspec").Meta(title=title)]


def test_type_expressions_are_supported_as_request_and_response_models(model_case):
    api = SpecTree("flask", model_adapter=model_case.adapter)
    app = Flask(__name__)
    item = model_case.get_model(Child)

    @app.post("/list")
    @api.validate(json=list[item], resp=Response(HTTP_200=dict[str, item]))
    def from_list():
        return {"first": {"value": 1}}

    @app.post("/optional")
    @api.validate(
        json=item | None, resp=Response(HTTP_200=_titled(model_case, item, "Titled"))
    )
    def optional():
        return {"value": 2}

    api.register(app)
    client = app.test_client()
    with app.app_context():
        spec = api.spec

    assert_component_refs_resolve(spec)
    assert client.post("/list", json=[{"value": 1}]).json == {"first": {"value": 1}}
    assert client.post("/list", json=[{"value": "x"}]).status_code == 422
    assert client.post("/optional", json={"value": 2}).json == {"value": 2}
    operation = spec["paths"]["/list"]["post"]
    assert _component_name(_json_schema_ref(operation)) == get_model_key(list[item])
    assert _component_name(_response_schema_ref(operation)) == get_model_key(
        dict[str, item]
    )


def test_list_models_can_be_reused_by_several_endpoints(model_case):
    api = SpecTree("flask", model_adapter=model_case.adapter)
    app = Flask(__name__)
    item = model_case.get_model(Child)

    for path in ("/a", "/b"):

        @app.post(path, endpoint=path)
        @api.validate(json=list[item], resp=Response(HTTP_200=list[item]))
        def view():
            return [{"value": 1}]

    api.register(app)
    with app.app_context():
        spec = api.spec
    first, second = (spec["paths"][path]["post"] for path in ("/a", "/b"))

    assert _json_schema_ref(first) == _json_schema_ref(second)
    assert _response_schema_ref(first) == _response_schema_ref(second)
    assert_component_refs_resolve(spec)
    assert app.test_client().post("/b", json=[{"value": 1}]).json == [{"value": 1}]


def test_one_handler_decorated_twice_is_documented_per_route(model_case):
    api = SpecTree("flask", model_adapter=model_case.adapter)
    app = Flask(__name__)
    first_model = model_case.get_model(FirstBody)
    second_model = model_case.get_model(SecondBody)

    def handler():
        return {}

    app.add_url_rule(
        "/first", "first", api.validate(json=first_model)(handler), methods=["POST"]
    )
    app.add_url_rule(
        "/second", "second", api.validate(json=second_model)(handler), methods=["POST"]
    )
    api.register(app)
    with app.app_context():
        paths = api.spec["paths"]

    assert _component_name(_json_schema_ref(paths["/first"]["post"])) == (
        get_model_key(first_model)
    )
    assert _component_name(_json_schema_ref(paths["/second"]["post"])) == (
        get_model_key(second_model)
    )


def test_custom_backend_receives_the_v3_validate_arguments(model_case):
    calls = []

    class RecordingPlugin(BasePlugin):
        def validate(
            self,
            func,
            query,
            json,
            form,
            headers,
            cookies,
            resp,
            before,
            after,
            validation_error_status,
            skip_validation,
            force_resp_serialize,
            *args,
            **kwargs,
        ):
            calls.append((json, resp, validation_error_status, skip_validation))
            return func(*args, **kwargs)

    api = SpecTree(backend=RecordingPlugin, model_adapter=model_case.adapter)
    payload = model_case.get_model(Payload)
    declaration = Response(HTTP_200=None)
    view = api.validate(json=payload, resp=declaration, validation_error_status=400)(
        lambda: "ok"
    )

    assert view() == "ok"
    ((json_model, resp, status, skip_validation),) = calls
    assert json_model is payload
    assert resp is not declaration
    assert resp.find_model(400) is api.model_adapter.validation_error
    assert (status, skip_validation) == (400, False)


@dataclass
class Filters:
    ids: list[int]
    name: str = "all"


@pytest.mark.parametrize(
    "query_model",
    [Filters | None, Annotated[Filters, "filters"]],
    ids=["optional", "annotated"],
)
def test_type_expressions_as_query_models(model_case, query_model):
    flask_app = Flask(__name__)
    flask_api = SpecTree("flask", model_adapter=model_case.adapter)

    @flask_app.get("/items")
    @flask_api.validate(query=query_model)
    def flask_items():
        return {"ids": flask_request.context.query.ids}

    starlette_api = SpecTree("starlette", model_adapter=model_case.adapter)

    @starlette_api.validate(query=query_model)
    async def starlette_items(request):
        return JSONResponse({"ids": request.context.query.ids})

    starlette_app = Starlette(routes=[Route("/items", starlette_items)])
    flask_api.register(flask_app)
    with flask_app.app_context():
        parameters = flask_api.spec["paths"]["/items"]["get"]["parameters"]

    flask_client = flask_app.test_client()
    starlette_client = StarletteTestClient(starlette_app)
    for query, ids in (("ids=1", [1]), ("ids=1&ids=2", [1, 2])):
        assert flask_client.get(f"/items?{query}").json == {"ids": ids}
        assert starlette_client.get(f"/items?{query}").json() == {"ids": ids}
    assert [(p["name"], p["required"]) for p in parameters] == [
        ("ids", True),
        ("name", False),
    ]


@pytest.mark.pydantic
def test_query_parameters_come_from_the_request_model_when_names_are_shared():
    pydantic = pytest.importorskip("pydantic")

    class Priced(pydantic.BaseModel):
        price: Decimal

    api = SpecTree(
        "flask",
        naming_strategy=lambda model: model.__name__,
        nested_naming_strategy=lambda _parent, child: child,
    )
    app = Flask(__name__)

    @app.get("/items")
    @api.validate(query=Priced, resp=Response(HTTP_200=list[Priced]))
    def items():
        return []

    api.register(app)
    with app.app_context():
        (parameter,) = api.spec["paths"]["/items"]["get"]["parameters"]

    assert parameter["schema"] == Priced.model_json_schema()["properties"]["price"]


@pytest.mark.pydantic
@pytest.mark.parametrize("response_first", [False, True])
def test_shared_nested_names_document_response_schemas(response_first):
    """The documented recipe `nested_naming_strategy=lambda _parent, child: child`
    with a nested model that is serialized differently than it is validated."""
    pydantic = pytest.importorskip("pydantic")

    class Line(pydantic.BaseModel):
        qty: int

        @pydantic.computed_field
        @property
        def double(self) -> int:
            return self.qty * 2

    class Order(pydantic.BaseModel):
        line: Line

    api = SpecTree(
        "flask",
        naming_strategy=lambda model: model.__name__.lower(),
        nested_naming_strategy=lambda _parent, child: child,
    )
    app = Flask(__name__)

    def add_request_endpoint():
        @app.post("/orders")
        @api.validate(json=Order)
        def create():
            return {}

    def add_response_endpoint():
        @app.get("/orders")
        @api.validate(resp=Response(HTTP_200=Order))
        def read():
            return Order(line=Line(qty=1))

    for add_endpoint in (
        (add_response_endpoint, add_request_endpoint)
        if response_first
        else (add_request_endpoint, add_response_endpoint)
    ):
        add_endpoint()
    api.register(app)
    with app.app_context():
        spec = api.spec
    schemas = spec["components"]["schemas"]

    def line_properties(ref):
        order = schemas[_component_name(ref)]
        return set(
            schemas[_component_name(order["properties"]["line"]["$ref"])]["properties"]
        )

    assert line_properties(_json_schema_ref(spec["paths"]["/orders"]["post"])) == {
        "qty"
    }
    assert line_properties(_response_schema_ref(spec["paths"]["/orders"]["get"])) == {
        "qty",
        "double",
    }
    assert_component_refs_resolve(spec)


def test_nested_naming_strategy_can_be_changed_after_construction(model_case):
    api = SpecTree("flask", model_adapter=model_case.adapter)
    api.nested_naming_strategy = lambda _parent, child: f"shared_{child}"
    app = Flask(__name__)

    @app.post("/parent")
    @api.validate(json=model_case.get_model(Parent))
    def create():
        return {}

    api.register(app)
    with app.app_context():
        spec = api.spec

    assert "shared_Child" in spec["components"]["schemas"]
    assert_component_refs_resolve(spec)


def test_list_of_optional_models_as_response_model(model_case):
    api = SpecTree("flask", model_adapter=model_case.adapter)
    app = Flask(__name__)
    item = model_case.get_model(Child)

    @app.get("/items")
    @api.validate(resp=Response(HTTP_200=list[item | None]))
    def items():
        return [{"value": 1}, None]

    api.register(app)
    with app.app_context():
        assert_component_refs_resolve(api.spec)
    assert app.test_client().get("/items").json == [{"value": 1}, None]


@pytest.mark.skipif(
    sys.version_info < (3, 14), reason="annotations are evaluated lazily from 3.14"
)
def test_lazily_evaluated_type_checking_annotations(model_case):
    case = import_module("tests.lazy_annotation_case")
    api = SpecTree("flask", model_adapter=model_case.adapter)
    app = Flask(__name__)
    app.add_url_rule("/view", view_func=api.validate()(case.view), methods=["POST"])
    api.register(app)

    response = app.test_client().post(
        "/view", json={"uid": 1, "limit": 2, "name": "spectree"}
    )

    assert response.json == {"name": "spectree"}
    with app.app_context():
        assert "requestBody" in api.spec["paths"]["/view"]["post"]
