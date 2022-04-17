from typing import Any, Dict, Iterator, List, Mapping, Optional, Sequence, Type, Union

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


class FunctionDecorator(Protocol):
    resp: Any
    tags: Sequence[Any]
    security: Union[None, Dict, List[Any]]
    deprecated: bool
    path_parameter_descriptions: Optional[Mapping[str, str]]
    _decorator: Any
