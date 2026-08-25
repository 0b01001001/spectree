from collections.abc import Callable, Iterator
from typing import (
    Any,
    Protocol,
)

from spectree.model_adapter.protocol import ModelAdapter, ModelClass

NamingStrategy = Callable[[ModelClass], str]
NestedNamingStrategy = Callable[[str, str], str]
ModelAdapterType = ModelAdapter[Any, Exception, Any]
HookHandler = Callable[
    [Any, Any, Exception | None, Any, ModelAdapterType],
    Any,
]


class MultiDict(Protocol):
    def get(self, key: str) -> str | None:
        pass

    def getlist(self, key: str) -> list[str]:
        pass

    def __iter__(self) -> Iterator[str]:
        pass


class MultiDictStarlette(Protocol):
    def __iter__(self) -> Iterator[str]:
        pass

    def getlist(self, key: Any) -> list[Any]:
        pass

    def __getitem__(self, key: Any) -> Any:
        pass


JsonType = int | str | bool | list["JsonType"] | dict[str, "JsonType"] | None
