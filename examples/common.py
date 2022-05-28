from pydantic import BaseModel, Field

from spectree import BaseFile


class File(BaseModel):
    uid: str
    file: BaseFile


class FileResp(BaseModel):
    filename: str
    type: str


class Query(BaseModel):
    text: str = Field(
        ...,
        max_length=100,
    )
