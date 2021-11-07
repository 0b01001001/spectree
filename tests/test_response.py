import pytest

from spectree.models import ValidationError
from spectree.response import DEFAULT_CODE_DESC, Response
from spectree.utils import get_model_path_key

from .common import JSON, DemoModel


class NormalClass:
    pass


def test_init_response():
    for args, kwargs in [
        ([200], {}),
        (["HTTP_110"], {}),
        ([], {"HTTP_200": NormalClass}),
        ([], {"HTTP_200": (NormalClass, "custom code description")}),
        ([], {"HTTP_200": (DemoModel, 1)}),
        ([], {"HTTP_200": (DemoModel,)}),
    ]:
        with pytest.raises(AssertionError):
            Response(*args, **kwargs)

    resp = Response("HTTP_200", HTTP_201=DemoModel)
    assert resp.has_model()
    assert resp.find_model(201) == DemoModel
    assert resp.code_descriptions.get("HTTP_200") is None
    assert resp.code_descriptions.get("HTTP_201") is None
    assert DemoModel in resp.models

    resp = Response(
        HTTP_200=None,
        HTTP_401=DemoModel,
        HTTP_402=(None, "custom code description"),
        HTTP_403=(DemoModel, "custom code description"),
    )
    assert resp.has_model()
    assert resp.find_model(200) is None
    assert resp.find_model(401) == DemoModel
    assert resp.find_model(402) is None
    assert resp.find_model(403) == DemoModel
    assert resp.code_descriptions.get("HTTP_200") is None
    assert resp.code_descriptions.get("HTTP_401") is None
    assert resp.code_descriptions.get("HTTP_402") == "custom code description"
    assert resp.code_descriptions.get("HTTP_403") == "custom code description"
    assert DemoModel in resp.models

    assert not Response().has_model()


def test_response_add_model():
    resp = Response()

    resp.add_model(201, DemoModel)

    assert resp.find_model(201) == DemoModel


@pytest.mark.parametrize(
    "replace, expected_model",
    [
        pytest.param(True, JSON, id="replace-existing-model"),
        pytest.param(False, DemoModel, id="keep-existing-model"),
    ],
)
def test_response_add_model_when_model_already_exists(replace, expected_model):
    resp = Response()

    resp.add_model(201, DemoModel)
    resp.add_model(201, JSON, replace=replace)

    assert resp.find_model(201) is expected_model


def test_response_spec():
    resp = Response(
        "HTTP_200",
        HTTP_201=DemoModel,
        HTTP_401=(DemoModel, "custom code description"),
        HTTP_402=(None, "custom code description"),
    )
    resp.add_model(422, ValidationError)
    spec = resp.generate_spec()
    assert spec["200"]["description"] == DEFAULT_CODE_DESC["HTTP_200"]
    assert spec["201"]["description"] == DEFAULT_CODE_DESC["HTTP_201"]
    assert spec["422"]["description"] == DEFAULT_CODE_DESC["HTTP_422"]
    assert spec["401"]["description"] == "custom code description"
    assert spec["402"]["description"] == "custom code description"
    assert spec["201"]["content"]["application/json"]["schema"]["$ref"].split("/")[
        -1
    ] == get_model_path_key("tests.common.DemoModel")
    assert spec["422"]["content"]["application/json"]["schema"]["$ref"].split("/")[
        -1
    ] == get_model_path_key("spectree.models.ValidationError")

    assert spec.get(200) is None
    assert spec.get(404) is None
