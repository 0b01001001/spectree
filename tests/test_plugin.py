from importlib import import_module

import pytest

from spectree.utils import get_model_key
from tests.common import build_security_schemes
from tests.common_dataclass import Cookies, Payload, Query, Resp
from tests.model_cases import build_model_case
from tests.plugin_falcon.apps import (
    FALCON_BACKEND,
    build_falcon_adapter_app,
)
from tests.plugin_flask.apps import (
    build_flask_adapter_app,
    build_flask_blueprint_adapter_app,
    build_flask_global_secure_adapter_api,
    build_flask_secure_adapter_api,
    build_flask_view_adapter_app,
)
from tests.plugin_starlette.apps import build_starlette_adapter_app

PLUGIN_API_BUILDERS = [
    pytest.param(build_flask_adapter_app, id="flask"),
    pytest.param(build_flask_blueprint_adapter_app, id="flask_blueprint"),
    pytest.param(build_flask_view_adapter_app, id="flask_view"),
    pytest.param(build_starlette_adapter_app, id="starlette"),
    pytest.param(
        lambda model_case: build_falcon_adapter_app(FALCON_BACKEND, model_case),
        id="falcon",
    ),
]


def _schema_models(model_case):
    models = [
        model_case.get_model(Query),
        model_case.get_model(Payload),
        model_case.get_model(Resp),
        model_case.get_model(Cookies),
    ]
    if model_case.name == "pydantic":
        models.append(import_module("tests.common_pydantic").Headers)
    return models


def _assert_schema_models(api, model_case):
    model_adapter = api.model_adapter
    models = {
        get_model_key(model=m): model_adapter.json_schema(
            model=m,
            ref_template=f"#/components/schemas/{get_model_key(model=m)}.{{model}}",
        )
        for m in _schema_models(model_case)
    }
    for name, schema in models.items():
        schema.pop("definitions", None)
        schema.pop("$defs", None)
        assert api.spec["components"]["schemas"][name] == schema


@pytest.mark.pydantic
@pytest.mark.parametrize("api_builder", PLUGIN_API_BUILDERS)
def test_plugin_spec(api_builder, snapshot_json):
    pytest.importorskip("pydantic")
    pydantic_case = build_model_case("pydantic")
    api = api_builder(pydantic_case).spec

    _assert_schema_models(api, pydantic_case)

    assert api.spec == snapshot_json(name="full_spec")


@pytest.mark.parametrize("api_builder", PLUGIN_API_BUILDERS)
def test_plugin_spec_model_adapters(model_case, api_builder):
    adapter_app = api_builder(model_case)

    _assert_schema_models(adapter_app.spec, model_case)


def test_secure_spec(model_case):
    security_schemes = build_security_schemes(model_case)
    flask_api_secure = build_flask_secure_adapter_api(model_case)

    assert [*flask_api_secure.spec["components"]["securitySchemes"].keys()] == [
        scheme.name for scheme in security_schemes
    ]

    paths = flask_api_secure.spec["paths"]
    # iter paths
    for path, path_data in paths.items():
        security = path_data["get"].get("security")
        # check empty-secure path
        if path == "/no-secure-ping":
            assert security is None
        else:
            # iter secure names and params
            for secure_key, secure_value in security[0].items():
                # check secure names valid
                assert secure_key in [scheme.name for scheme in security_schemes]

                # check if flow exist
                if secure_value:
                    scopes = [
                        scheme.data.flows["authorizationCode"]["scopes"]
                        for scheme in security_schemes
                        if scheme.name == secure_key
                    ]

                    assert set(secure_value).issubset(*scopes)


def test_secure_global_spec(model_case):
    security_schemes = build_security_schemes(model_case)
    flask_api_global_secure = build_flask_global_secure_adapter_api(model_case)

    assert [*flask_api_global_secure.spec["components"]["securitySchemes"].keys()] == [
        scheme.name for scheme in security_schemes
    ]

    paths = flask_api_global_secure.spec["paths"]
    global_security = flask_api_global_secure.spec["security"]

    assert global_security == [{"auth_apiKey": []}]

    # iter paths
    for path, path_data in paths.items():
        security = path_data["get"].get("security")
        # check empty-secure path
        if path == "/no-secure-override-ping":
            # check if it is defined overridden no auth specification
            assert security == []
        elif path == "/oauth2-flows-override-ping":
            # check if it is defined overridden security specification
            assert security == [{"auth_oauth2": ["admin", "read"]}]
        elif path == "/global-secure-ping":
            # check if local security specification is missing,
            # when was not specified explicitly
            assert security is None
        elif path == "/security_and":
            # check if AND operation is supported
            assert security == [{"auth_apiKey": [], "auth_apiKey_backup": []}]
        elif path == "/security_or":
            # check if OR operation is supported
            assert security == [{"auth_apiKey": []}, {"auth_apiKey_backup": []}]
