from typing import Iterator, List, Optional, Protocol, Type

from pydantic import BaseModel

OptionalModelType = Optional[Type[BaseModel]]


class MultiDict(Protocol):
    def get(self, key: str) -> Optional[str]:
        ...

    def getlist(self, key: str) -> List[str]:
        ...

    def __iter__(self) -> Iterator[str]:
        ...
