from typing import (
    Any,
    Callable,
    Dict,
    Iterator,
    List,
    Mapping,
    Optional,
    Sequence,
    Type,
    TypeVar,
    Union,
)

from typing_extensions import Protocol

from ._pydantic import BaseModel

BaseModelSubclassType = TypeVar("BaseModelSubclassType", bound=BaseModel)
ModelType = Type[BaseModelSubclassType]
OptionalModelType = Optional[ModelType]
NamingStrategy = Callable[[ModelType], str]
NestedNamingStrategy = Callable[[str, str], str]


class MultiDict(Protocol):
    def get(self, key: str) -> Optional[str]:
        pass

    def getlist(self, key: str) -> List[str]:
        pass

    def __iter__(self) -> Iterator[str]:
        pass


class MultiDictStarlette(Protocol):
    def __iter__(self) -> Iterator[str]:
        pass

    def getlist(self, key: Any) -> List[Any]:
        pass

    def __getitem__(self, key: Any) -> Any:
        pass


class FunctionDecorator(Protocol):
    resp: Any
    tags: Sequence[Any]
    security: Union[None, Dict, List[Any]]
    deprecated: bool
    path_parameter_descriptions: Optional[Mapping[str, str]]
    _decorator: Any


JsonType = Union[None, int, str, bool, List["JsonType"], Dict[str, "JsonType"]]
