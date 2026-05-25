import pytest

from spectree.response import DEFAULT_CODE_DESC, Response
from spectree.utils import get_model_key


class NormalClass:
    pass


def test_response_rejects_invalid_configuration():
    for args, kwargs in [
        ([200], {}),
        (["HTTP_110"], {}),
        ([], {"HTTP_200": (NormalClass, 1)}),
        ([], {"HTTP_200": (NormalClass,)}),
    ]:
        with pytest.raises(AssertionError):
            Response(*args, **kwargs)


def test_response_rejects_invalid_model(model_case):
    adapter = model_case.adapter
    if adapter.is_model_type(NormalClass):
        pytest.skip(f"{model_case.name} adapter accepts arbitrary model specs")

    resp = Response(HTTP_200=NormalClass)
    with pytest.raises(AssertionError, match="invalid response model"):
        resp.bind_model_adapter(adapter)

    resp = Response(HTTP_200=(NormalClass, "custom code description"))
    with pytest.raises(AssertionError, match="invalid response model"):
        resp.bind_model_adapter(adapter)


def test_init_response(model_case):
    adapter = model_case.adapter
    simple_model = model_case.simple_model

    resp = Response("HTTP_200", HTTP_201=simple_model)
    resp.bind_model_adapter(adapter)

    assert resp.has_model()
    assert resp.find_model(201) is simple_model
    assert resp.code_descriptions.get("HTTP_200") is None
    assert resp.code_descriptions.get("HTTP_201") is None
    assert simple_model in resp.models

    list_model = model_case.list_of(simple_model)
    resp = Response(
        HTTP_200=None,
        HTTP_400=list_model,
        HTTP_401=simple_model,
        HTTP_402=(None, "custom code description"),
        HTTP_403=(simple_model, "custom code description"),
    )
    resp.bind_model_adapter(adapter)

    assert resp.has_model()
    assert resp.find_model(200) is None
    expect_400_model = adapter.make_list_model(simple_model)
    assert resp.find_model(400) is not list_model
    assert get_model_key(resp.find_model(400)) == get_model_key(expect_400_model)
    assert resp.find_model(401) is simple_model
    assert resp.find_model(402) is None
    assert resp.find_model(403) is simple_model
    assert resp.code_descriptions.get("HTTP_200") is None
    assert resp.code_descriptions.get("HTTP_401") is None
    assert resp.code_descriptions.get("HTTP_402") == "custom code description"
    assert resp.code_descriptions.get("HTTP_403") == "custom code description"
    assert simple_model in resp.models

    assert not Response().has_model()


def test_response_add_model(model_case):
    resp = Response()
    resp.bind_model_adapter(model_case.adapter)

    resp.add_model(201, model_case.simple_model)

    assert resp.find_model(201) is model_case.simple_model


def test_response_find_model_requires_bound_adapter(model_case):
    resp = Response(HTTP_200=model_case.simple_model)

    assert resp.find_model(200) is None

    resp.bind_model_adapter(model_case.adapter)

    assert resp.find_model(200) is model_case.simple_model


def test_response_add_model_builds_only_new_model(monkeypatch, model_case):
    adapter = model_case.adapter
    simple_model = model_case.simple_model
    list_model = model_case.list_of(simple_model)

    resp = Response(HTTP_200=list_model)
    resp.bind_model_adapter(adapter)

    calls = []
    original_make_list_model = adapter.make_list_model

    def tracked_make_list_model(model):
        calls.append(model)
        return original_make_list_model(model)

    monkeypatch.setattr(adapter, "make_list_model", tracked_make_list_model)

    resp.add_model(201, list_model)

    assert calls == [simple_model]
    assert resp.find_model(200) is not None
    assert resp.find_model(201) is not None


@pytest.mark.parametrize(
    "replace, expected_model_name",
    [
        pytest.param(True, "users_model", id="replace-existing-model"),
        pytest.param(False, "simple_model", id="keep-existing-model"),
    ],
)
def test_response_add_model_when_model_already_exists(
    model_case,
    replace,
    expected_model_name,
):
    resp = Response()
    resp.bind_model_adapter(model_case.adapter)

    resp.add_model(201, model_case.simple_model)
    resp.add_model(201, model_case.users_model, replace=replace)

    assert resp.find_model(201) is getattr(model_case, expected_model_name)


def test_response_add_model_when_model_already_exists_before_bind(model_case):
    resp = Response()

    resp.add_model(201, model_case.simple_model)
    resp.add_model(201, model_case.users_model, replace=False)
    resp.bind_model_adapter(model_case.adapter)

    assert resp.find_model(201) is model_case.simple_model


def test_response_spec(model_case):
    adapter = model_case.adapter
    simple_model = model_case.simple_model
    validation_error = adapter.validation_error

    resp = Response(
        "HTTP_200",
        HTTP_201=simple_model,
        HTTP_401=(simple_model, "custom code description"),
        HTTP_402=(None, "custom code description"),
    )
    resp.bind_model_adapter(adapter)
    resp.add_model(422, validation_error)

    spec = resp.generate_spec()

    assert spec["200"]["description"] == DEFAULT_CODE_DESC["HTTP_200"]
    assert spec["201"]["description"] == DEFAULT_CODE_DESC["HTTP_201"]
    assert spec["422"]["description"] == DEFAULT_CODE_DESC["HTTP_422"]
    assert spec["401"]["description"] == "custom code description"
    assert spec["402"]["description"] == "custom code description"
    assert spec["201"]["content"]["application/json"]["schema"]["$ref"].split("/")[
        -1
    ] == get_model_key(simple_model)
    assert spec["422"]["content"]["application/json"]["schema"]["$ref"].split("/")[
        -1
    ] == get_model_key(validation_error)

    assert spec.get(200) is None
    assert spec.get(404) is None


def test_list_model(model_case):
    simple_model = model_case.simple_model
    list_model = model_case.list_of(simple_model)

    resp = Response(HTTP_200=list_model)
    resp.bind_model_adapter(model_case.adapter)
    model = resp.find_model(200)

    data = [
        {"user_id": 1},
        {"user_id": 2},
    ]
    instance = model_case.validate_obj(model, data)

    assert model_case.dump_python(instance) == data
