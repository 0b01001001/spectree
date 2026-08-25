import uuid
from dataclasses import dataclass
from datetime import datetime
from enum import Enum, IntEnum
from typing import Any


class Order(IntEnum):
    """Order enum"""

    asce = 0
    desc = 1


class ReturnCase(str, Enum):
    PAYLOAD = "Payload"
    MODEL = "Model"
    ROOT_MODEL = "RootModel"
    RAW_LIST = "RawList"
    ROOT_LIST = "RootList"
    MODEL_LIST = "ModelList"


@dataclass
class LimitQuery:
    limit: int


@dataclass
class NamePayload:
    name: str


@dataclass
class Item:
    name: str
    limit: int


@dataclass
class Query:
    order: Order = Order.asce


@dataclass
class QueryList:
    ids: list[int]


@dataclass
class Payload:
    name: str
    limit: int


@dataclass
class OptionalPayload:
    name: str | None = None
    limit: int | None = None


@dataclass
class Cookies:
    pub: str


@dataclass
class Headers:
    token: str


@dataclass
class Form:
    name: str
    limit: str


@dataclass
class FormPayload:
    other: Any
    file: Any = None


@dataclass
class Score:
    name: str
    score: list[int]


@dataclass
class Resp:
    name: str
    score: list[int]


@dataclass
class RespObject:
    name: str
    score: list[int]
    comment: str


@dataclass
class ComplexResp:
    date: datetime
    uuid: uuid.UUID


@dataclass
class RequiredLimitQuery:
    limit: int


@dataclass
class SimpleModel:
    user_id: int


@dataclass
class RootModelLookalike:
    __root__: list[str]


@dataclass
class DemoModel:
    uid: int
    limit: int
    name: str


@dataclass
class DemoQuery:
    names1: list[str]
    names2: list[str]


@dataclass
class OptionalListQuery:
    names: list[str] | None = None
    title: str | None = None


@dataclass
class Child:
    value: int
