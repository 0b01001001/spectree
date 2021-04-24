from enum import Enum, IntEnum
from typing import Dict, List

from pydantic import BaseModel, Field, root_validator

from spectree import Tag

api_tag = Tag(name="API", description="🐱", externalDocs={"url": "https://pypi.org"})


class Order(IntEnum):
    asce = 1
    desc = 0


class Query(BaseModel):
    order: Order


class JSON(BaseModel):
    name: str
    limit: int


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
