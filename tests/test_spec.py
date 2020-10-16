import pytest
from flask import Flask
from typing import List
import falcon
from starlette.applications import Starlette
from openapi_spec_validator import validate_v3_spec
from pydantic import BaseModel, StrictFloat, Field

from spectree import Response
from spectree.response import FileResponse
from spectree.spec import SpecTree
from spectree.config import Config
from spectree.plugins import FlaskPlugin

from .common import get_paths


class ExampleModel(BaseModel):
    name: str = Field(strip_whitespace=True)
    age: int
    height: StrictFloat


class ExampleNestedList(BaseModel):
    __root__: List[ExampleModel]


class ExampleNestedModel(BaseModel):
    example: ExampleModel


class ExampleDeepNestedModel(BaseModel):
    data: List['ExampleModel']


def backend_app():
    return [
        ('flask', Flask(__name__)),
        ('falcon', falcon.API()),
        ('starlette', Starlette()),
    ]


def test_spectree_init():
    spec = SpecTree(path='docs')
    conf = Config()

    assert spec.config.TITLE == conf.TITLE
    assert spec.config.PATH == 'docs'

    with pytest.raises(NotImplementedError):
        SpecTree(app=conf)


@pytest.mark.parametrize('name, app', backend_app())
def test_register(name, app):
    api = SpecTree(name)
    api.register(app)


@pytest.mark.parametrize('name, app', backend_app())
def test_spec_generate(name, app):
    api = SpecTree(
        name,
        app=app,
        title=f'{name}',
        info={'title': 'override', 'description': 'api level description'},
        tags=[{'name': 'lone', 'description': 'a lone api'}],
    )
    spec = api.spec

    assert spec['info']['title'] == name
    assert spec['info']['description'] == 'api level description'
    assert spec['paths'] == {}
    assert spec['tags'] == []


api = SpecTree(
    'flask',
    tags=[{'name': 'lone', 'description': 'a lone api'}],
    validation_error_code=400,
)
api_strict = SpecTree('flask', mode='strict')
api_greedy = SpecTree('flask', mode='greedy')
api_customize_backend = SpecTree(backend=FlaskPlugin)


def create_app():
    app = Flask(__name__)

    @app.route('/foo')
    @api.validate()
    def foo():
        pass

    @app.route('/bar')
    @api_strict.validate()
    def bar():
        pass

    @app.route('/lone', methods=['GET'])
    def lone_get():
        pass

    @app.route('/lone', methods=['POST'])
    @api.validate(json=ExampleModel, resp=Response(
        HTTP_200=ExampleNestedList, HTTP_400=ExampleNestedModel
    ), tags=['lone'], deprecated=True)
    def lone_post():
        pass

    @app.route('/file')
    @api.validate(resp=FileResponse())
    def get_file():
        pass

    return app


def test_spec_bypass_mode():
    app = create_app()
    api.register(app)
    assert get_paths(api.spec) == ['/file', '/foo', '/lone']

    app = create_app()
    api_customize_backend.register(app)
    assert get_paths(api.spec) == ['/file', '/foo', '/lone']

    app = create_app()
    api_greedy.register(app)
    assert get_paths(api_greedy.spec) == ['/bar', '/file', '/foo', '/lone']

    app = create_app()
    api_strict.register(app)
    assert get_paths(api_strict.spec) == ['/bar']


def test_two_endpoints_with_the_same_path():
    app = create_app()
    api.register(app)
    spec = api.spec

    http_methods = list(spec['paths']['/lone'].keys())
    http_methods.sort()
    assert http_methods == ['get', 'post']


def test_valid_openapi_spec():
    app = create_app()
    api.register(app)
    spec = api.spec
    validate_v3_spec(spec)


def test_openapi_tags():
    app = create_app()
    api.register(app)
    spec = api.spec

    assert spec['tags'][0]['name'] == 'lone'
    assert spec['tags'][0]['description'] == 'a lone api'


def test_openapi_deprecated():
    app = create_app()
    api.register(app)
    spec = api.spec

    assert spec['paths']['/lone']['post']['deprecated'] == True
    assert 'deprecated' not in spec['paths']['/lone']['get']
