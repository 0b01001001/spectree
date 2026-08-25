from dataclasses import dataclass

import pytest
from falcon import App as FalconApp
from flask import Flask
from starlette.applications import Starlette

from spectree import Response
from spectree.config import Configuration
from spectree.metadata import get_function_metadata
from spectree.models import Server
from spectree.plugins.flask_plugin import FlaskPlugin
from spectree.spec import SpecTree
from spectree.utils import get_model_key
from tests.common import get_paths
from tests.common_dataclass import Child, Cookies, Form, Headers, Payload, Query, Resp


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
        get_function_metadata(foo).resp.find_model(422)
        is api.model_adapter.validation_error
    )
    assert get_function_metadata(bar).resp.find_model(422) is custom_validation_error


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

    assert get_function_metadata(foo).resp.find_model(422) is global_validation_error
    assert get_function_metadata(bar).resp.find_model(422) is route_validation_error


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
