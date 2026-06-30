import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import cast

from spectree import ExternalDocs, SecurityScheme, SecuritySchemeData, Tag
from spectree.model_adapter import get_pydantic_model_adapter
from spectree.utils import hash_module_path

__all__ = [
    "SECURITY_SCHEMAS",
    "WRONG_SECURITY_SCHEMAS_DATA",
    "UserXmlData",
    "api_after_handler",
    "api_tag",
    "get_model_path_key",
    "get_paths",
    "instance_name_after_handler",
    "validation_error_handler",
    "validation_pass_handler",
]

ADAPTER = get_pydantic_model_adapter()

api_tag = Tag(
    name="API", description="🐱", externalDocs=ExternalDocs(url="https://pypi.org")
)


def get_paths(spec):
    paths = []
    for path in spec["paths"]:
        if spec["paths"][path]:
            paths.append(path)

    paths.sort()
    return paths


def _set_response_header(resp, name: str, value: str) -> None:
    if hasattr(resp, "set_header"):
        resp.set_header(name, value)
    else:
        resp.headers[name] = value


def validation_error_handler(req, resp, err, instance, model_adapter):
    if err:
        _set_response_header(resp, "X-Error", "Validation Error")


def validation_pass_handler(req, resp, err, instance, model_adapter):
    _set_response_header(resp, "X-Validation", "Pass")


def api_after_handler(req, resp, err, instance, model_adapter):
    _set_response_header(resp, "X-API", "OK")


def instance_name_after_handler(req, resp, err, instance, model_adapter):
    if hasattr(instance, "name"):
        _set_response_header(resp, "X-Name", instance.name)


# data from example - https://swagger.io/docs/specification/authentication/
SECURITY_SCHEMAS = [
    SecurityScheme(
        name="auth_apiKey",
        data=SecuritySchemeData.model_validate(
            {"type": "apiKey", "name": "Authorization", "in": "header"},
            model_adapter=ADAPTER,
        ),
    ),
    SecurityScheme(
        name="auth_apiKey_backup",
        data=SecuritySchemeData.model_validate(
            {"type": "apiKey", "name": "Authorization", "in": "header"},
            model_adapter=ADAPTER,
        ),
    ),
    SecurityScheme(
        name="auth_BasicAuth",
        data=SecuritySchemeData.model_validate(
            {"type": "http", "scheme": "basic"},
            model_adapter=ADAPTER,
        ),
    ),
    SecurityScheme(
        name="auth_BearerAuth",
        data=SecuritySchemeData.model_validate(
            {"type": "http", "scheme": "bearer"},
            model_adapter=ADAPTER,
        ),
    ),
    SecurityScheme(
        name="auth_openID",
        data=SecuritySchemeData.model_validate(
            {
                "type": "openIdConnect",
                "openIdConnectUrl": "https://example.com/.well-known/openid-cfg",
            },
            model_adapter=ADAPTER,
        ),
    ),
    SecurityScheme(
        name="auth_oauth2",
        data=SecuritySchemeData.model_validate(
            {
                "type": "oauth2",
                "flows": {
                    "authorizationCode": {
                        "authorizationUrl": "https://example.com/oauth/authorize",
                        "tokenUrl": "https://example.com/oauth/token",
                        "scopes": {
                            "read": "Grants read access",
                            "write": "Grants write access",
                            "admin": "Grants access to admin operations",
                        },
                    },
                },
            },
            model_adapter=ADAPTER,
        ),
    ),
]
WRONG_SECURITY_SCHEMAS_DATA = [
    {
        "name": "auth_apiKey_name",
        "data": {"type": "apiKey", "name": "Authorization"},
    },
    {
        "name": "auth_apiKey_in",
        "data": {"type": "apiKey", "in": "header"},
    },
    {
        "name": "auth_BasicAuth_scheme",
        "data": {"type": "http"},
    },
    {
        "name": "auth_openID_openIdConnectUrl",
        "data": {"type": "openIdConnect"},
    },
    {"name": "auth_oauth2_flows", "data": {"type": "oauth2"}},
    {"name": "empty_Data", "data": {}},
    {"name": "wrong_Data", "data": {"x": "y"}},
]


def get_model_path_key(model_path: str) -> str:
    """
    generate short hashed prefix for module path (instead of its path to avoid
    code-structure leaking)

    :param model_path: `str` model path in string
    """

    model_path, _, model_name = model_path.rpartition(".")
    if not model_path:
        return model_name

    return f"{model_name}.{hash_module_path(module_path=model_path)}"


@dataclass(frozen=True)
class UserXmlData:
    name: str
    score: list[int]

    @staticmethod
    def parse_xml(data: str) -> "UserXmlData":
        root = ET.fromstring(data)
        assert root.tag == "user"
        children = [node for node in root]
        assert len(children) == 2
        assert children[0].tag == "name"
        assert children[1].tag == "x_score"
        return UserXmlData(
            name=cast(str, children[0].text),
            score=[int(entry) for entry in cast(str, children[1].text).split(",")],
        )

    def dump_xml(self) -> str:
        return f"""
            <user>
              <name>{self.name}</name>
              <x_score>{",".join(str(entry) for entry in self.score)}</x_score>
            </user>
            """
