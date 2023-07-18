from enum import Enum, IntEnum
from typing import Dict, List

from spectree import BaseFile, ExternalDocs, SecurityScheme, SecuritySchemeData, Tag
from spectree._pydantic import BaseModel, Field, root_validator
from spectree.utils import hash_module_path

api_tag = Tag(
    name="API", description="🐱", externalDocs=ExternalDocs(url="https://pypi.org")
)


class Order(IntEnum):
    asce = 0
    desc = 1


class Query(BaseModel):
    order: Order


class FormFileUpload(BaseModel):
    file: BaseFile


class Form(BaseModel):
    name: str
    limit: str


class JSON(BaseModel):
    name: str
    limit: int


class ListJSON(BaseModel):
    __root__: List[JSON]


class StrDict(BaseModel):
    __root__: Dict[str, str]


class Resp(BaseModel):
    name: str
    score: List[int]


class Language(str, Enum):
    en = "en-US"
    zh = "zh-CN"


class Headers(BaseModel):
    lang: Language

    @root_validator(pre=True)
    def lower_keys(cls, values):
        return {key.lower(): value for key, value in values.items()}


class Cookies(BaseModel):
    pub: str


class DemoModel(BaseModel):
    uid: int
    limit: int
    name: str = Field(..., description="user name")


class DemoQuery(BaseModel):
    names1: List[str] = Field(...)
    names2: List[str] = Field(..., style="matrix", explode=True, non_keyword="dummy")


def get_paths(spec):
    paths = []
    for path in spec["paths"]:
        if spec["paths"][path]:
            paths.append(path)

    paths.sort()
    return paths


# data from example - https://swagger.io/docs/specification/authentication/
SECURITY_SCHEMAS = [
    SecurityScheme(
        name="auth_apiKey",
        data=SecuritySchemeData.parse_obj(
            {"type": "apiKey", "name": "Authorization", "in": "header"}
        ),
    ),
    SecurityScheme(
        name="auth_apiKey_backup",
        data=SecuritySchemeData.parse_obj(
            {"type": "apiKey", "name": "Authorization", "in": "header"}
        ),
    ),
    SecurityScheme(
        name="auth_BasicAuth",
        data=SecuritySchemeData.parse_obj({"type": "http", "scheme": "basic"}),
    ),
    SecurityScheme(
        name="auth_BearerAuth",
        data=SecuritySchemeData.parse_obj({"type": "http", "scheme": "bearer"}),
    ),
    SecurityScheme(
        name="auth_openID",
        data=SecuritySchemeData.parse_obj(
            {
                "type": "openIdConnect",
                "openIdConnectUrl": "https://example.com/.well-known/openid-cfg",
            }
        ),
    ),
    SecurityScheme(
        name="auth_oauth2",
        data=SecuritySchemeData.parse_obj(
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
            }
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
    {
        "name": "auth_oauth2_flows",
        "data": {"type": "oauth2"},
    },
    {
        "name": "empty_Data",
        "data": {},
    },
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
