import pytest

from spectree.models import ValidationError
from spectree.response import DEFAULT_CODE_DESC, Response
from spectree.spec import SpecTree
from spectree.utils import (
    has_model,
    parse_code,
    parse_comments,
    parse_name,
    parse_params,
    parse_request,
    parse_resp,
)

from .common import DemoModel, DemoQuery, get_model_path_key

api = SpecTree()


def undecorated_func():
    """summary

    description"""


@api.validate(json=DemoModel, resp=Response(HTTP_200=DemoModel))
def demo_func():
    """
    summary

    description"""


@api.validate(query=DemoQuery)
def demo_func_with_query():
    """
    a summary

    a description
    """


class DemoClass:
    @api.validate(query=DemoModel)
    def demo_method(self):
        """summary

        description
        """


demo_class = DemoClass()


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
        pytest.param(demo_func, "summary", "description", id="decorated-function"),
        pytest.param(
            demo_class.demo_method, "summary", "description", id="class-method"
        ),
    ],
)
def test_parse_comments_with_different_callable_types(
    func, expected_summary, expected_description
):
    assert parse_comments(func) == (expected_summary, expected_description)


def test_parse_code():
    with pytest.raises(TypeError):
        assert parse_code(200) == 200

    assert parse_code("200") == ""
    assert parse_code("HTTP_404") == "404"


def test_parse_name():
    assert parse_name(lambda x: x) == "<lambda>"
    assert parse_name(undecorated_func) == "undecorated_func"
    assert parse_name(demo_func) == "demo_func"
    assert parse_name(demo_class.demo_method) == "demo_method"


def test_has_model():
    assert not has_model(undecorated_func)
    assert has_model(demo_func)
    assert has_model(demo_class.demo_method)


def test_parse_resp():
    assert parse_resp(undecorated_func) == {}
    resp_spec = parse_resp(demo_func)

    assert resp_spec["422"]["description"] == DEFAULT_CODE_DESC["HTTP_422"]
    model_path_key = get_model_path_key(
        f"{ValidationError.__module__}.{ValidationError.__name__}"
    )
    assert (
        resp_spec["422"]["content"]["application/json"]["schema"]["$ref"]
        == f"#/components/schemas/{model_path_key}"
    )
    model_path_key = get_model_path_key(f"{DemoModel.__module__}.{DemoModel.__name__}")
    assert (
        resp_spec["200"]["content"]["application/json"]["schema"]["$ref"]
        == f"#/components/schemas/{model_path_key}"
    )


def test_parse_request():
    model_path_key = get_model_path_key(f"{DemoModel.__module__}.{DemoModel.__name__}")
    assert (
        parse_request(demo_func)["content"]["application/json"]["schema"]["$ref"]
        == f"#/components/schemas/{model_path_key}"
    )
    assert parse_request(demo_class.demo_method) == {}


def test_parse_params():
    models = {
        get_model_path_key(
            f"{DemoModel.__module__}.{DemoModel.__name__}"
        ): DemoModel.schema(ref_template="#/components/schemas/{model}")
    }
    assert parse_params(demo_func, [], models) == []
    params = parse_params(demo_class.demo_method, [], models)
    assert len(params) == 3
    assert params[0] == {
        "name": "uid",
        "in": "query",
        "required": True,
        "description": "",
        "schema": {"title": "Uid", "type": "integer"},
    }
    assert params[2]["description"] == "user name"


def test_parse_params_with_route_param_keywords():
    models = {
        get_model_path_key("tests.common.DemoQuery"): DemoQuery.schema(
            ref_template="#/components/schemas/{model}"
        )
    }
    params = parse_params(demo_func_with_query, [], models)
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
