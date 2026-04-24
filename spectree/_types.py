from typing import (
    Any,
    Callable,
    Iterator,
    Mapping,
    Optional,
    Protocol,
    Sequence,
    Union,
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
    def get(self, key: str) -> Optional[str]:
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


class FunctionDecorator(Protocol):
    resp: Any
    tags: Sequence[Any]
    security: Union[None, dict, list[Any]]
    deprecated: bool
    path_parameter_descriptions: Optional[Mapping[str, str]]
    _decorator: Any


JsonType = Union[None, int, str, bool, list["JsonType"], dict[str, "JsonType"]]
