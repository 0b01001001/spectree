import pytest
from falcon import App as FalconApp
from flask import Flask
from pydantic import BaseModel
from starlette.applications import Starlette

from spectree import Response
from spectree.config import Configuration
from spectree.models import Server, ValidationError
from spectree.plugins.flask_plugin import FlaskPlugin
from spectree.spec import SpecTree

from .common import get_paths


def backend_app():
    return [
        ("flask", Flask(__name__)),
        ("falcon", FalconApp()),
        ("starlette", Starlette()),
    ]


def _get_spec(name, app, **kwargs):
    api = SpecTree(name, app=app, title=f"{name}", **kwargs)
    if name == "flask":
        with app.app_context():
            spec = api.spec
    else:
        spec = api.spec

    return spec


def test_spectree_init():
    spec = SpecTree(path="docs")
    conf = Configuration()

    assert spec.config.title == conf.title
    assert spec.config.path == "docs"

    with pytest.raises(NotImplementedError):
        SpecTree(app=conf)


@pytest.mark.parametrize("name, app", backend_app())
def test_register(name, app):
    api = SpecTree(name)
    api.register(app)


@pytest.mark.parametrize("name, app", backend_app())
def test_spec_generate(name, app):
    spec = _get_spec(name, app)

    assert spec["info"]["title"] == name
    assert spec["paths"] == {}


@pytest.mark.parametrize("name, app", backend_app())
def test_spec_servers_empty(name, app):
    spec = _get_spec(name, app)

    assert "servers" not in spec


@pytest.mark.parametrize("name, app", backend_app())
def test_spec_servers_only(name, app):
    server1_url = "http://foo/bar"
    server2_url = "/foo/bar/"
    spec = _get_spec(
        name, app, servers=[Server(url=server1_url), Server(url=server2_url)]
    )

    assert spec["servers"] == [
        {"url": server1_url},
        {"url": server2_url},
    ]


@pytest.mark.parametrize("name, app", backend_app())
def test_spec_servers_full(name, app):
    server1 = {"url": "http://foo/bar", "description": "Foo Bar"}
    server2 = {"url": "http://bar/foo/{lang}", "variables": {"lang": "en"}}
    spec = _get_spec(
        name,
        app,
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


api = SpecTree("flask")
api_strict = SpecTree("flask", mode="strict")
api_greedy = SpecTree("flask", mode="greedy")
api_customize_backend = SpecTree(backend=FlaskPlugin)


def create_app():
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

    return app


def test_spec_bypass_mode():
    app = create_app()
    api.register(app)
    with app.app_context():
        assert get_paths(api.spec) == ["/foo", "/lone"]

    app = create_app()
    api_customize_backend.register(app)
    with app.app_context():
        assert get_paths(api.spec) == ["/foo", "/lone"]

    app = create_app()
    api_greedy.register(app)
    with app.app_context():
        assert get_paths(api_greedy.spec) == ["/bar", "/foo", "/lone"]

    app = create_app()
    api_strict.register(app)
    with app.app_context():
        assert get_paths(api_strict.spec) == ["/bar"]


def test_two_endpoints_with_the_same_path():
    app = create_app()
    api.register(app)
    spec = api.spec

    http_methods = list(spec["paths"]["/lone"].keys())
    http_methods.sort()
    assert http_methods == ["get", "post"]


def test_model_for_validation_errors_specified():
    api = SpecTree("flask")
    app = Flask(__name__)

    class CustomValidationError(BaseModel):
        pass

    @app.route("/foo")
    @api.validate(resp=Response(HTTP_200=None))
    def foo():
        pass

    @app.route("/bar")
    @api.validate(resp=Response(HTTP_200=None, HTTP_422=CustomValidationError))
    def bar():
        pass

    api.register(app)

    assert foo.resp.find_model(422) is ValidationError
    assert bar.resp.find_model(422) is CustomValidationError
