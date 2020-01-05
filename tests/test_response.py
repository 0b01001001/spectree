import pytest

from spectree.response import Response, DEFAULT_CODE_DESC

from .common import DemoModel


class NormalClass:
    pass


def test_init_response():
    for args, kwargs in [
        ([200], {}),
        (['HTTP_110'], {}),
        ([], {'HTTP_200': NormalClass}),
    ]:
        with pytest.raises(AssertionError):
            Response(*args, **kwargs)

    resp = Response('HTTP_200', HTTP_201=DemoModel)
    assert resp.has_model()
    assert resp.find_model(201) == DemoModel
    assert DemoModel in resp.models

    assert not Response().has_model()


def test_response_spec():
    resp = Response('HTTP_200', HTTP_201=DemoModel)
    spec = resp.generate_spec()
    assert spec['200']['description'] == DEFAULT_CODE_DESC['HTTP_200']
    assert spec['201']['description'] == DEFAULT_CODE_DESC['HTTP_201']
    assert spec['201']['content']['application/json']['schema']['$ref'].split(
        '/')[-1] == 'DemoModel'

    assert spec.get(200) is None
    assert spec.get(404) is None
