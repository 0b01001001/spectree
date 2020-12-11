from enum import Enum, IntEnum
from typing import Dict, List

from pydantic import BaseModel, Field, root_validator


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


def get_paths(spec):
    paths = []
    for path in spec["paths"]:
        if spec["paths"][path]:
            paths.append(path)

    paths.sort()
    return paths
