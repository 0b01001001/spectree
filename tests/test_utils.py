import json
from dataclasses import dataclass
from importlib import import_module
from typing import Annotated, Any, TypeVar, get_args, get_type_hints

import pytest

from spectree.metadata import FunctionDecorator
from spectree.model_adapter import get_pydantic_model_adapter
from spectree.response import DEFAULT_CODE_DESC, Response
from spectree.spec import SpecTree
from spectree.utils import (
    get_request_model_hints,
    has_model,
    is_list_item,
    json_compatible_deepcopy,
    parse_code,
    parse_comments,
    parse_name,
    parse_params,
    parse_request,
    parse_resp,
)
from tests.common import (
    get_model_path_key,
)
from tests.common_dataclass import (
    DemoModel,
    DemoModel as DemoModelDef,
    DemoQuery,
    DemoQuery as DemoQueryDef,
    OptionalListQuery,
)
from tests.type_checking_annotation_case import type_checking_view_func


def undecorated_func():
    """summary

    description"""


@dataclass(frozen=True)
class UtilsModels:
    spec: SpecTree
    adapter: Any
    demo_model: Any
    demo_query: Any
    optional_list_query: Any
    demo_func: Any
    demo_func_with_query: Any
    demo_class: Any


@pytest.fixture
def utils_models(model_case):
    api = SpecTree(model_adapter=model_case.adapter)
    demo_model = model_case.get_model(DemoModelDef)
    demo_query = model_case.get_model(DemoQueryDef)
    optional_list_query = model_case.get_model(OptionalListQuery)

    @api.validate(json=demo_model, resp=Response(HTTP_200=demo_model))
    def demo_func():
        """
        summary

        description"""

    @api.validate(query=demo_query)
    def demo_func_with_query():
        """
        a summary

        a description
        """

    class DemoClass:
        @api.validate(query=demo_model)
        def demo_method(self):
            """summary

            description
            """

    return UtilsModels(
        spec=api,
        adapter=model_case.adapter,
        demo_model=demo_model,
        demo_query=demo_query,
        optional_list_query=optional_list_query,
        demo_func=demo_func,
        demo_func_with_query=demo_func_with_query,
        demo_class=DemoClass(),
    )


@pytest.mark.parametrize(
    "docstring, expected_summary, expected_description",
    [
        pytest.param(None, None, None, id="no-docstring"),
        pytest.param("", "", None, id="empty-docstring"),
        pytest.param("   ", "", None, id="all-whitespace-docstring"),
        pytest.param("summary", "summary", None, id="single-line-docstring"),
        pytest.param(
            "   summary   ", "summary", None, id="single-line-docstring-with-whitespace"
        ),
        pytest.param(
            "summary first line\nsummary second line",
            "summary first line summary second line",
            None,
            id="multi-line-docstring-without-empty-line",
        ),
        pytest.param(
            "  summary first line \n summary second line  ",
            "summary first line  summary second line",
            None,
            id="multi-line-docstring-without-empty-line-whitespace",
        ),
        pytest.param(
            "summary\n\ndescription",
            "summary",
            "description",
            id="multi-line-docstring-with-empty-line",
        ),
        pytest.param(
            "   summary   \n\n   description  ",
            "summary",
            "description",
            id="multi-line-docstring-with-empty-line-whitespace",
        ),
        pytest.param(
            "summary\n\t   \ndescription",
            "summary",
            "description",
            id="multi-line-docstring-with-whitespace-line",
        ),
        pytest.param(
            "summary\n  \n  \n  \n  \n  \ndescription",
            "summary",
            "description",
            id="multi-line-docstring-with-multiple-whitespace-lines",
        ),
        pytest.param(
            "summary first line\nsummary second line\nsummary third line"
            "\n\t   \n"
            "description first line\ndescription second line\ndescription third line",
            "summary first line summary second line summary third line",
            "description first line description second line description third line",
            id="large-multi-line-docstring-with-whitespace-line",
        ),
        pytest.param(
            "summary first line\nsummary second line\ftruncated part",
            "summary first line summary second line",
            None,
            id="multi-line-docstring-without-empty-line-and-truncation-char",
        ),
        pytest.param(
            "summary first line\nsummary second line\nsummary third line"
            "\n\t   \n"
            "description first line\ndescription second line\ndescription third line"
            "\ftruncated part",
            "summary first line summary second line summary third line",
            "description first line description second line description third line",
            id="large-multi-line-docstring-with-whitespace-line-and-truncation-char",
        ),
        pytest.param(
            "summary first line\nsummary second line\n"
            "\t   \n"
            "description first line   \ndescription second line\n"
            "\t   \n"
            "description second paragraph   \n"
            "\n \n \n"
            "description third paragraph\ndescription third paragraph second line",
            "summary first line summary second line",
            "description first line    description second line"
            "\n\n"
            "description second paragraph"
            "\n\n"
            "description third paragraph description third paragraph second line",
            id="large-multi-line-docstring-with-multiple-paragraphs",
        ),
        pytest.param(
            "\tcode block while indented\n"
            "\t\n"
            "\tdescription first paragraph\n"
            "\t\n"
            "\t\tcode block\n"
            "\t\n"
            "\tdescription third paragraph\n",
            "code block while indented",
            "description first paragraph"
            "\n\n"
            "        code block"
            "\n\n"
            "description third paragraph",
            id="multi-line-docstring-with-code-block",
        ),
    ],
)
def test_parse_comments(docstring, expected_summary, expected_description):
    def func():
        pass

    func.__doc__ = docstring

    assert parse_comments(func) == (expected_summary, expected_description)


@pytest.mark.parametrize(
    "func, expected_summary, expected_description",
    [
        pytest.param(lambda x: x, None, None, id="lambda"),
        pytest.param(
            undecorated_func, "summary", "description", id="undecorated-function"
        ),
        pytest.param("demo_func", "summary", "description", id="decorated-function"),
        pytest.param("demo_method", "summary", "description", id="class-method"),
    ],
)
def test_parse_comments_with_different_callable_types(
    utils_models, func, expected_summary, expected_description
):
    if func == "demo_func":
        func = utils_models.demo_func
    elif func == "demo_method":
        func = utils_models.demo_class.demo_method

    assert parse_comments(func) == (expected_summary, expected_description)


def test_parse_code():
    with pytest.raises(TypeError):
        assert parse_code(200) == 200

    assert parse_code("200") == ""
    assert parse_code("HTTP_404") == "404"


def test_parse_name(utils_models):
    assert parse_name(lambda x: x) == "<lambda>"
    assert parse_name(undecorated_func) == "undecorated_func"
    assert parse_name(utils_models.demo_func) == "demo_func"
    assert parse_name(utils_models.demo_class.demo_method) == "demo_method"


def test_has_model(utils_models):
    assert not has_model(FunctionDecorator())
    assert has_model(utils_models.spec.get_function_metadata(utils_models.demo_func))
    assert has_model(
        utils_models.spec.get_function_metadata(utils_models.demo_class.demo_method)
    )


def test_parse_resp(utils_models):
    assert parse_resp(FunctionDecorator()) == {}
    resp_spec = parse_resp(
        utils_models.spec.get_function_metadata(utils_models.demo_func)
    )

    assert resp_spec["422"]["description"] == DEFAULT_CODE_DESC["HTTP_422"]
    model_path_key = get_model_path_key(
        f"{utils_models.adapter.validation_error.__module__}."
        f"{utils_models.adapter.validation_error.__name__}"
    )
    assert (
        resp_spec["422"]["content"]["application/json"]["schema"]["$ref"]
        == f"#/components/schemas/{model_path_key}"
    )
    model_path_key = get_model_path_key(
        f"{utils_models.demo_model.__module__}.{utils_models.demo_model.__name__}"
    )
    assert (
        resp_spec["200"]["content"]["application/json"]["schema"]["$ref"]
        == f"#/components/schemas/{model_path_key}"
    )


def test_parse_request(utils_models):
    model_path_key = get_model_path_key(
        f"{utils_models.demo_model.__module__}.{utils_models.demo_model.__name__}"
    )
    assert (
        parse_request(utils_models.spec.get_function_metadata(utils_models.demo_func))[
            "content"
        ]["application/json"]["schema"]["$ref"]
        == f"#/components/schemas/{model_path_key}"
    )
    assert (
        parse_request(
            utils_models.spec.get_function_metadata(utils_models.demo_class.demo_method)
        )
        == {}
    )


def test_parse_params(utils_models):
    models = {
        get_model_path_key(
            f"{utils_models.demo_model.__module__}.{utils_models.demo_model.__name__}"
        ): utils_models.adapter.json_schema(
            utils_models.demo_model,
            ref_template="#/components/schemas/{model}",
        )
    }
    assert (
        parse_params(
            utils_models.spec.get_function_metadata(utils_models.demo_func), [], models
        )
        == []
    )
    params = parse_params(
        utils_models.spec.get_function_metadata(utils_models.demo_class.demo_method),
        [],
        models,
    )
    assert len(params) == 3
    assert params[0]["name"] == "uid"
    assert params[0]["in"] == "query"
    assert params[0]["required"] is True
    assert params[0]["description"] == ""
    assert params[0]["schema"]["type"] == "integer"
    assert params[2]["name"] == "name"
    assert params[2]["schema"]["type"] == "string"


@pytest.mark.pydantic
def test_parse_params_preserves_pydantic_field_description():
    DemoModel = import_module("tests.common_pydantic").DemoModel
    api = SpecTree()

    @api.validate(query=DemoModel)
    def demo_method():
        pass

    models = {
        get_model_path_key(
            f"{DemoModel.__module__}.{DemoModel.__name__}"
        ): DemoModel.model_json_schema(ref_template="#/components/schemas/{model}")
    }
    params = parse_params(api.get_function_metadata(demo_method), [], models)
    assert params[0] == {
        "name": "uid",
        "in": "query",
        "required": True,
        "description": "",
        "schema": {"title": "Uid", "type": "integer"},
    }
    assert params[2]["description"] == "user name"


@pytest.mark.pydantic
def test_parse_params_with_route_param_keywords():
    DemoQuery = import_module("tests.common_pydantic").DemoQuery
    api = SpecTree()

    @api.validate(query=DemoQuery)
    def demo_func_with_query():
        pass

    models = {
        get_model_path_key(
            "tests.common_pydantic.DemoQuery"
        ): DemoQuery.model_json_schema(ref_template="#/components/schemas/{model}")
    }
    params = parse_params(api.get_function_metadata(demo_func_with_query), [], models)
    assert params == [
        {
            "name": "names1",
            "in": "query",
            "required": True,
            "description": "",
            "schema": {"title": "Names1", "type": "array", "items": {"type": "string"}},
        },
        {
            "name": "names2",
            "in": "query",
            "required": True,
            "description": "",
            "schema": {
                "title": "Names2",
                "type": "array",
                "items": {"type": "string"},
                "non_keyword": "dummy",
            },
            "style": "matrix",
            "explode": True,
        },
    ]
    query_schema = models[get_model_path_key("tests.common_pydantic.DemoQuery")]
    assert query_schema["properties"]["names2"]["style"] == "matrix"
    assert query_schema["properties"]["names2"]["explode"] is True

    repeated_params = parse_params(
        api.get_function_metadata(demo_func_with_query), [], models
    )
    assert repeated_params == params


def test_get_request_model_hints():
    def func(
        query: DemoQuery,
        json: Annotated[DemoModel, "metadata"],
        form: DemoModel,
        headers: DemoModel,
        cookies: DemoModel,
    ) -> int:
        return 0

    hints = get_request_model_hints(func)

    assert hints["query"] is DemoQuery
    assert get_args(hints["json"]) == (DemoModel, "metadata")
    assert hints["form"] is DemoModel
    assert hints["headers"] is DemoModel
    assert hints["cookies"] is DemoModel
    assert "return" not in hints


def test_get_request_model_hints_unresolvable_return_annotation():
    original_annotations = dict(type_checking_view_func.__annotations__)

    with pytest.raises(NameError):
        get_type_hints(type_checking_view_func)

    assert get_request_model_hints(type_checking_view_func) == {"json": DemoModel}
    assert type_checking_view_func.__annotations__ == original_annotations


def test_get_request_model_hints_ignores_unrelated_parameter_without_return():
    def func(json: DemoModel, unrelated):
        raise NotImplementedError

    func.__annotations__["unrelated"] = "CompletelyNonExistentType"

    with pytest.raises(NameError):
        get_type_hints(func)

    assert get_request_model_hints(func) == {"json": DemoModel}


def test_get_request_model_hints_unresolvable_parameter_annotation():
    def func(json: DemoModel) -> int:
        raise NotImplementedError

    func.__annotations__["json"] = "CompletelyNonExistentType"

    with pytest.raises(NameError):
        get_request_model_hints(func)


def test_get_request_model_hints_preserves_annotated():
    def func(json: Annotated[DemoModel, "metadata"]):
        raise NotImplementedError

    hints = get_request_model_hints(func)

    assert get_args(hints["json"]) == (DemoModel, "metadata")


def test_get_request_model_hints_without_annotations():
    def func():
        return None

    assert get_request_model_hints(func) == {}


def test_get_request_model_hints_generic_function():
    T = TypeVar("T")

    def func(json: T) -> T:
        raise NotImplementedError

    assert get_request_model_hints(func) == {"json": T}


@pytest.mark.skipif(
    not hasattr(lambda: None, "__type_params__"),
    reason="PEP 695 requires Python 3.12+",
)
def test_get_request_model_hints_pep_695_generic_function():
    T = TypeVar("T")

    def func(json):
        raise NotImplementedError

    func.__annotations__ = {
        "json": "T",
        "return": "CompletelyNonExistentType",
    }
    func.__type_params__ = (T,)

    assert get_request_model_hints(func) == {"json": T}


def test_is_list_item(utils_models):
    assert is_list_item("names1", utils_models.demo_query)
    assert is_list_item("names2", utils_models.demo_query)
    assert is_list_item("names", utils_models.optional_list_query)
    assert not is_list_item("uid", utils_models.demo_model)
    assert not is_list_item("title", utils_models.optional_list_query)
    assert not is_list_item("missing", utils_models.demo_query)
    assert not is_list_item("names", None)


@pytest.mark.pydantic
def test_json_compatible_schema():
    common_pydantic = import_module("tests.common_pydantic")
    model_adapter = get_pydantic_model_adapter()
    schema = model_adapter.json_schema(
        common_pydantic.Numeric, ref_template="#/components/schemas/{model}"
    )

    with pytest.raises(ValueError):
        json.dumps(schema, allow_nan=False)

    json_schema = json_compatible_deepcopy(schema)
    assert json.dumps(json_schema, allow_nan=False)

    schema = model_adapter.json_schema(
        common_pydantic.DefaultEnumValue,
        ref_template="#/components/schemas/{model}",
    )
    json_schema = json_compatible_deepcopy(schema)
    assert json.dumps(json_schema)


@pytest.mark.pydantic
def test_get_model_schema_mode_parameter():
    """Test get_model_schema mode parameter for Pydantic v2"""
    pydantic = import_module("pydantic")
    BaseModel = pydantic.BaseModel
    computed_field = pydantic.computed_field
    model_adapter = get_pydantic_model_adapter()

    class TestModel(BaseModel):
        """Model with computed field"""

        name: str
        value: int

        @computed_field
        @property
        def computed_name(self) -> str:
            """Computed field - only in serialization"""
            return f"computed_{self.name}"

    # Test validation mode - computed fields excluded
    validation_schema = model_adapter.json_schema(
        TestModel,
        ref_template="#/components/schemas/{model}",
        mode="validation",
    )
    assert "name" in validation_schema["properties"]
    assert "value" in validation_schema["properties"]
    assert "computed_name" not in validation_schema["properties"], (
        "Computed field should NOT be in validation mode"
    )

    # Test serialization mode - computed fields included
    serialization_schema = model_adapter.json_schema(
        TestModel,
        ref_template="#/components/schemas/{model}",
        mode="serialization",
    )
    assert "name" in serialization_schema["properties"]
    assert "value" in serialization_schema["properties"]
    assert "computed_name" in serialization_schema["properties"], (
        "Computed field SHOULD be in serialization mode"
    )

    # Verify computed field is marked as readOnly and required
    assert serialization_schema["properties"]["computed_name"].get("readOnly") is True
    assert "computed_name" in serialization_schema["required"]
