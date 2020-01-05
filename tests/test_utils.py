import pytest
from pydantic import BaseModel

from spectree.utils import (
    parse_comments, parse_request, parse_params, parse_resp,
    has_model, parse_code, parse_name, pop_keywords
)
from spectree.spec import SpecTree
from spectree.response import Response


api = SpecTree()


class DemoModel(BaseModel):
    name: str
    limit: int


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


def test_pop_kw():
    kwargs = {
        'func': demo_func,
        'json': DemoModel,
        'query': None,
        'headers': None,
        'cookies': None,
        'resp': None,
    }
    func, query, json, headers, cookies, resp = pop_keywords(kwargs)
    assert json == DemoModel
    assert func == demo_func
    assert not all([query, headers, cookies, resp])
    assert not kwargs


def test_has_model():
    assert not has_model(undecorated_func)
    assert has_model(demo_func)
    assert has_model(demo_class.demo_method)


def test_parse_resp():
    assert parse_resp(undecorated_func) == {}
    assert parse_resp(demo_class.demo_method) == {
        '422': {
            'description': 'Validation Error'
        }
    }
    resp_spec = parse_resp(demo_func)
    assert resp_spec['422']['description'] == 'Validation Error'
    assert resp_spec['200']['content']['application/json']['schema']['$ref'] \
        == '#/components/schemas/DemoModel'


def test_parse_request():
    assert parse_request(demo_func)['content']['application/json']['schema']['$ref'] \
        == '#/components/schemas/DemoModel'
    assert parse_request(demo_class.demo_method)['content']['application/json']['schema']['$ref'] \
        == ''


def test_parse_params():
    assert parse_params(demo_func, []) == []
    params = parse_params(demo_class.demo_method, [])
    assert len(params) == 1
    assert params[0] == {
        'name': 'DemoModel',
        'in': 'query',
        'required': True,
        'schema': {
            '$ref': '#/components/schemas/DemoModel',
        }
    }
