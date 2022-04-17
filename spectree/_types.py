from typing import Iterator, List, Optional, Type

from pydantic import BaseModel
from typing_extensions import Protocol

ModelType = Type[BaseModel]
OptionalModelType = Optional[ModelType]


class MultiDict(Protocol):
    def get(self, key: str) -> Optional[str]:
        ...

    def getlist(self, key: str) -> List[str]:
        ...

    def __iter__(self) -> Iterator[str]:
        ...
