from enum import IntEnum, Enum
from typing import List
from datetime import datetime

from pydantic import BaseModel


class Order(IntEnum):
    asce = 1
    desc = 0


class Query(BaseModel):
    order: Order


class JSON(BaseModel):
    name: str
    limit: int


class Resp(BaseModel):
    name: str
    score: List[int]


class Language(str, Enum):
    en = 'en-US'
    zh = 'zh-CN'


class Headers(BaseModel):
    Lang: Language

    class Config:
        case_sensitive = False


class UpperHeaders(BaseModel):
    LANG: Language


class LowerHeaders(BaseModel):
    lang: Language


class Cookies(BaseModel):
    pub: str


class DemoModel(BaseModel):
    uid: int
    limit: int
    name: str


def get_paths(spec):
    paths = []
    for path in spec['paths']:
        if spec['paths'][path]:
            paths.append(path)

    paths.sort()
    return paths
