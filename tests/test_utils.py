import pytest

from spectree.utils import (
    parse_comments, parse_request, parse_params, parse_resp,
    has_model, parse_code, parse_name
)
from spectree.spec import SpecTree
from spectree.response import Response

from .common import DemoModel


api = SpecTree()


def undecorated_func():
    """summary
    description"""
    pass


@api.validate(json=DemoModel, resp=Response(HTTP_200=DemoModel))
def demo_func():
    """
    summary

    description"""
    pass


class DemoClass:
    @api.validate(query=DemoModel)
    def demo_method(self):
        """summary
        description
        """
        pass


demo_class = DemoClass()


def test_comments():
    assert parse_comments(lambda x: x) == (None, None)
    assert parse_comments(undecorated_func) == ('summary', 'description')
    assert parse_comments(demo_func) == ('summary', 'description')
    assert parse_comments(demo_class.demo_method) == (
        'summary', 'description'
    )


def test_parse_code():
    with pytest.raises(TypeError):
        assert parse_code(200) == 200

    assert parse_code('200') is None
    assert parse_code('HTTP_404') == '404'


def test_parse_name():
    assert parse_name(lambda x: x) == '<lambda>'
    assert parse_name(undecorated_func) == 'undecorated_func'
    assert parse_name(demo_func) == 'demo_func'
    assert parse_name(demo_class.demo_method) == 'demo_method'


def test_has_model():
    assert not has_model(undecorated_func)
    assert has_model(demo_func)
    assert has_model(demo_class.demo_method)


def test_parse_resp():
    assert parse_resp(undecorated_func) == {}
    resp_spec = parse_resp(demo_func)

    assert resp_spec['422']['description'] == 'Unprocessable Entity'
    assert resp_spec['422']['content']['application/json']['schema']['$ref'] \
        == '#/components/schemas/UnprocessableEntityElement'
    assert resp_spec['200']['content']['application/json']['schema']['$ref'] \
        == '#/components/schemas/DemoModel'


def test_parse_request():
    assert parse_request(demo_func)['content']['application/json']['schema']['$ref'] \
        == '#/components/schemas/DemoModel'
    assert parse_request(demo_class.demo_method) == {}


def test_parse_params():
    models = {'DemoModel': DemoModel.schema()}
    assert parse_params(demo_func, [], models) == []
    params = parse_params(demo_class.demo_method, [], models)
    assert len(params) == 3
    assert params[0] == {
        'name': 'uid',
        'in': 'query',
        'required': True,
        'description': '',
        'schema': {
            'title': 'Uid',
            'type': 'integer',
        }
    }
    assert params[2]['description'] == 'user name'
