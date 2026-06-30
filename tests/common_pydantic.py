from enum import Enum
from typing import Any, Optional, Union, cast

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from spectree.model_adapter.pydantic_adapter import BaseFile
from tests.common_dataclass import Payload
from tests.model_cases import build_model_case

pydantic_case = build_model_case("pydantic")


def _pydantic_model(model_def: Any, *, name: str | None = None) -> type[Any]:
    return cast(type[Any], pydantic_case.get_model(model_def, name=name))


class FormFileUpload(BaseModel):
    file: Optional[BaseFile] = None
    other: str


PayloadModel = _pydantic_model(Payload)
ListPayload = _pydantic_model(list[Payload], name="ListPayload")
StrDict = _pydantic_model(dict[str, str], name="StrDict")


class OptionalAliasResp(BaseModel):
    alias_schema: str = Field(alias="schema")
    name: Optional[str] = None
    limit: Optional[int] = None


class RespFromAttrs(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    name: str
    score: list[int]


RootResp = _pydantic_model(Union[Payload, list[int]], name="RootResp")


class Language(str, Enum):
    """Language enum"""

    en = "en-US"
    zh = "zh-CN"


class Headers(BaseModel):
    lang: Language

    @model_validator(mode="before")
    @classmethod
    def lower_keys(cls, data: Any):
        return {key.lower(): value for key, value in data.items()}


class DemoModel(BaseModel):
    uid: int
    limit: int
    name: str = Field(..., description="user name")


class DemoQuery(BaseModel):
    names1: list[str] = Field(...)
    names2: list[str] = Field(
        ..., json_schema_extra=dict(style="matrix", explode=True, non_keyword="dummy")
    )  # type: ignore


class CustomError(BaseModel):
    foo: str

    @field_validator("foo")
    @classmethod
    def value_must_be_foo(cls, value):
        if value != "foo":
            # this is not JSON serializable if included in the error context
            raise ValueError("value must be foo")
        return value


class Numeric(BaseModel):
    normal: float = 0.0
    large: float = Field(default=float("inf"))
    small: float = Field(default=float("-inf"))
    unknown: float = Field(default=float("nan"))


class DefaultEnumValue(BaseModel):
    langs: frozenset[Language] = frozenset((Language.en,))


def get_root_resp_data(pre_serialize: bool, return_what: str):
    assert return_what in (
        "RootResp_Payload",
        "RootResp_List",
        "Payload",
        "List",
        "ModelList",
    )
    data: Any
    if return_what == "RootResp_Payload":
        data = RootResp.model_validate(PayloadModel(name="user1", limit=1))
    elif return_what == "RootResp_List":
        data = RootResp.model_validate([1, 2, 3, 4])
    elif return_what == "Payload":
        data = PayloadModel(name="user1", limit=1)
    elif return_what == "List":
        data = [1, 2, 3, 4]
        pre_serialize = False
    elif return_what == "ModelList":
        data = [PayloadModel(name="user1", limit=1)]
        pre_serialize = False
    else:
        raise AssertionError()
    if pre_serialize:
        if isinstance(data, BaseModel):
            data = data.model_dump()
            if isinstance(data, dict) and "__root__" in data:
                data = data["__root__"]
        elif isinstance(data, list):
            data = [
                item.model_dump() if isinstance(item, BaseModel) else item
                for item in data
            ]
    return data
