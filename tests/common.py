from enum import Enum
from typing import List
from datetime import datetime

from pydantic import BaseModel


class Order(Enum):
    asce = True
    desc = False


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


class Cookies(BaseModel):
    domain: str
    path: str
    value: str
    expires: datetime


class DemoModel(BaseModel):
    uid: int
    limit: int
    name: str
