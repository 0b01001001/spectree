import json

import flask
import msgspec
import pytest

import spectree.model_adapter as model_adapter_module
from spectree.config import Configuration
from spectree.model_adapter import get_msgspec_model_adapter
from spectree.model_adapter.msgspec_adapter import MsgspecModelAdapter
from spectree.models import SecurityScheme
from spectree.spec import SpecTree

ADAPTER = get_msgspec_model_adapter()


class SimpleModel(msgspec.Struct):
    user_id: int


DummyRootModel = ADAPTER.make_root_model(list[int], name="DummyRootModel")
NestedRootModel = ADAPTER.make_root_model(DummyRootModel, name="NestedRootModel")
Users = ADAPTER.make_root_model(list[SimpleModel], name="Users")


@pytest.mark.parametrize(
    "value, expected",
    [
        (SimpleModel(user_id=1), True),
        ([0, SimpleModel(user_id=1)], True),
        ([1, 2, 3], False),
        ((0, SimpleModel(user_id=1)), True),
        ((0, 1), False),
        ({"test": SimpleModel(user_id=1)}, True),
        ({"test": [SimpleModel(user_id=1)]}, True),
        ([0, [1, SimpleModel(user_id=1)]], True),
    ],
)
def test_is_partial_model_instance(value, expected):
    assert ADAPTER.is_partial_model_instance(value) is expected


@pytest.mark.parametrize(
    "value, expected",
    [
        (SimpleModel(user_id=1), {"user_id": 1}),
        (ADAPTER.validate_obj(DummyRootModel, [1, 2, 3]), [1, 2, 3]),
        (
            ADAPTER.validate_obj(
                NestedRootModel,
                ADAPTER.validate_obj(DummyRootModel, [1, 2, 3]),
            ),
            [1, 2, 3],
        ),
        (
            ADAPTER.validate_obj(
                Users,
                [
                    {"user_id": 1},
                    {"user_id": 2},
                ],
            ),
            [{"user_id": 1}, {"user_id": 2}],
        ),
    ],
)
def test_dump_json(value, expected):
    assert json.loads(ADAPTER.dump_json(value)) == expected


def test_validate_json_list_model():
    model = ADAPTER.make_list_model(SimpleModel)
    instance = ADAPTER.validate_json(model, b'[{"user_id": 1}, {"user_id": 2}]')

    assert json.loads(ADAPTER.dump_json(instance)) == [
        {"user_id": 1},
        {"user_id": 2},
    ]


def test_validation_error_schema_uses_placeholder_name():
    schema = ADAPTER.json_schema(
        msgspec.ValidationError,
        ref_template="#/components/schemas/{model}",
    )

    assert schema["title"] == "ValidationError"
    assert schema["type"] == "array"
    assert schema["items"]["$ref"] == "#/components/schemas/ValidationErrorElement"


def test_validation_errors_shape():
    with pytest.raises(msgspec.ValidationError) as exc_info:
        ADAPTER.validate_obj(SimpleModel, {"user_id": "bad"})

    assert ADAPTER.validation_errors(exc_info.value) == [
        {
            "loc": ["user_id"],
            "msg": "Expected `int`, got `str`",
            "type": "validation_error",
        }
    ]


def test_get_msgspec_model_adapter_is_lazy(monkeypatch):
    model_adapter_module.get_msgspec_model_adapter.cache_clear()
    model_adapter_module.get_pydantic_model_adapter.cache_clear()

    imported_modules = []
    original_import_module = model_adapter_module.import_module

    def tracked_import_module(name):
        imported_modules.append(name)
        return original_import_module(name)

    monkeypatch.setattr(model_adapter_module, "import_module", tracked_import_module)

    adapter = get_msgspec_model_adapter()

    assert isinstance(adapter, MsgspecModelAdapter)
    assert "spectree.model_adapter.msgspec_adapter" in imported_modules
    assert "spectree.model_adapter.pydantic_adapter" not in imported_modules


def test_msgspec_adapter_validates_internal_configuration_models():
    config = Configuration.model_validate(
        {
            "title": "Msgspec API",
            "termsOfService": "https://example.com/terms",
            "servers": [{"url": "https://example.com"}],
            "securitySchemes": [
                SecurityScheme.model_validate(
                    {
                        "name": "auth_apiKey",
                        "data": {
                            "type": "apiKey",
                            "in": "header",
                            "name": "Authorization",
                        },
                    },
                    model_adapter=ADAPTER,
                )
            ],
        },
        model_adapter=ADAPTER,
    )

    assert config.terms_of_service == "https://example.com/terms"
    assert config.servers[0].url == "https://example.com"
    assert config.security_schemes is not None
    assert len(config.security_schemes) == 1
    assert config.security_schemes[0].name == "auth_apiKey"
    assert config.security_schemes[0].data.type.value == "apiKey"
    assert config.security_schemes[0].data.field_in.value == "header"
    assert config.security_schemes[0].data.name == "Authorization"


def test_msgspec_adapter_dump_python_supports_alias_and_exclude_none():
    config = Configuration.model_validate(
        {
            "title": "Msgspec API",
            "termsOfService": "https://example.com/terms",
        },
        model_adapter=ADAPTER,
    )

    assert config.to_dict(exclude_none=True) == {
        "title": "Msgspec API",
        "version": "0.1.0",
        "termsOfService": "https://example.com/terms",
        "path": "apidoc",
        "filename": "openapi.json",
        "openapi_version": "3.1.0",
        "mode": "normal",
        "page_templates": config.page_templates,
        "annotations": True,
        "servers": [],
        "security": {},
        "client_id": "",
        "client_secret": "",
        "realm": "",
        "app_name": "spectree_app",
        "scope_separator": " ",
        "scopes": [],
        "additional_query_string_params": {},
        "use_basic_authentication_with_access_code_grant": False,
        "use_pkce_with_authorization_code_grant": False,
    }


def test_spectree_uses_msgspec_adapter_for_internal_configuration():
    api = SpecTree(
        "flask",
        app=flask.Flask(__name__),
        model_adapter=ADAPTER,
        title="Msgspec API",
        termsOfService="https://example.com/terms",
        servers=[{"url": "https://example.com"}],
    )

    with api.app.app_context():
        assert api.spec["info"]["termsOfService"] == "https://example.com/terms"
        assert api.spec["servers"] == [{"url": "https://example.com"}]
