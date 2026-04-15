import sys
from http import HTTPStatus
from typing import Any, Dict, Iterable, List, Optional, Tuple, TypeAlias, Union

from spectree._types import NamingStrategy
from spectree.model_adapter import ModelAdapter, ModelClass
from spectree.utils import get_model_key, parse_code

# according to https://tools.ietf.org/html/rfc2616#section-10
# https://tools.ietf.org/html/rfc7231#section-6.1
# https://developer.mozilla.org/sv-SE/docs/Web/HTTP/Status
DEFAULT_CODE_DESC: Dict[str, str] = dict(
    (f"HTTP_{status.value}", f"{status.phrase}") for status in HTTPStatus
)

# Python's typing cannot precisely express runtime type expressions such as
# `List[User]` or `list[User]` here without relying on non-portable internals.
ResponseModelSpec: TypeAlias = object
ResponseModelConfig: TypeAlias = Union[
    None,
    ResponseModelSpec,
    Tuple[Optional[ResponseModelSpec], str],
]

# additional status codes and fixes
if sys.version_info < (3, 13):
    # https://docs.python.org/3/library/http.html
    # https://datatracker.ietf.org/doc/html/rfc9110.html
    for code, phrase in [
        ("HTTP_418", "I'm a teapot"),
        ("HTTP_425", "Too Early"),
    ]:
        DEFAULT_CODE_DESC[code] = phrase
    DEFAULT_CODE_DESC["HTTP_422"] = "Unprocessable Content"


class Response:
    """
    response object

    :param codes: list of HTTP status code, format('HTTP_[0-9]{3}'), 'HTTP_200'
    :param code_models: dict of <HTTP status code>: <model class> or None or
        a two element tuple of (<model class> or None) as the first item and
        a custom status code description string as the second item.

    examples:

        >>> from typing import List
        >>> from spectree.response import Response
        >>> response = Response("HTTP_200")
        >>> response = Response(HTTP_200=None)
        >>> response = Response(HTTP_200=MyModel)
        >>> response = Response(HTTP_200=(MyModel, "status code description"))
        >>> response = Response(HTTP_200=List[MyModel])
        >>> response = Response(HTTP_200=(List[MyModel], "status code description"))
    """

    def __init__(
        self,
        *codes: str,
        **code_models: ResponseModelConfig,
    ) -> None:
        self.model_adapter: Optional[ModelAdapter[Any, Exception]] = None
        self.codes: List[str] = []
        self._raw_code_models: Dict[str, Any] = {}

        for code in codes:
            assert code in DEFAULT_CODE_DESC, "invalid HTTP status code"
            self.codes.append(code)

        self.code_models: Dict[str, ModelClass] = {}
        self.code_descriptions: Dict[str, Optional[str]] = {}
        for code, model_and_description in code_models.items():
            assert code in DEFAULT_CODE_DESC, "invalid HTTP status code"
            description: Optional[str] = None
            if isinstance(model_and_description, tuple):
                assert len(model_and_description) == 2, (
                    "unexpected number of arguments for a tuple of "
                    "response model and HTTP status code description"
                )
                model = model_and_description[0]
                description = model_and_description[1]
            else:
                model = model_and_description

            if model:
                self._raw_code_models[code] = model
                assert description is None or isinstance(description, str), (
                    "invalid HTTP status code description"
                )
            else:
                self.codes.append(code)

            if description:
                self.code_descriptions[code] = description

    def bind_model_adapter(self, model_adapter: ModelAdapter[Any, Exception]) -> None:
        self.model_adapter = model_adapter
        self.code_models = self._build_models(model_adapter)

    def _build_model(
        self, raw_model: Any, model_adapter: ModelAdapter[Any, Exception]
    ) -> ModelClass:
        model = raw_model
        origin_type = getattr(model, "__origin__", None)
        if origin_type is list or origin_type is List:
            model = model_adapter.make_list_model(model.__args__[0])  # type: ignore
        assert model_adapter.is_model_type(model), f"invalid response model: {model}"
        return model

    def _build_models(
        self, model_adapter: ModelAdapter[Any, Exception]
    ) -> Dict[str, ModelClass]:
        code_models: Dict[str, ModelClass] = {}
        for code, raw_model in self._raw_code_models.items():
            code_models[code] = self._build_model(raw_model, model_adapter)
        return code_models

    def _has_configured_model(self, code: int) -> bool:
        code_name = f"HTTP_{code}"
        return code_name in self.code_models or code_name in self._raw_code_models

    def add_model(
        self,
        code: int,
        model: ResponseModelSpec,
        replace: bool = True,
        description: Optional[str] = None,
    ) -> None:
        """Add data *model* for the specified status *code*.

        :param code: An HTTP status code.
        :param model: A response model class.
        :param replace: If `True` and a data *model* already exists for the given
            status *code* it will be replaced, if `False` the existing data *model*
            will be retained.
        :param description: The description string for the code.
        """
        if not replace and self._has_configured_model(code):
            return
        code_name: str = f"HTTP_{code}"
        self._raw_code_models[code_name] = model
        if self.model_adapter is not None:
            self.code_models[code_name] = self._build_model(model, self.model_adapter)
        if description:
            self.code_descriptions[code_name] = description

    def has_model(self) -> bool:
        """
        :returns: boolean -- does this response has models or not
        """
        return bool(self.code_models)

    def find_model(self, code: int) -> Optional[ModelClass]:
        """
        :param code: ``r'\\d{3}'``
        """
        return self.code_models.get(f"HTTP_{code}")

    def get_code_description(self, code: str) -> str:
        """Get the description of the given status code.

        :param code: Status code string, format('HTTP_[0-9]_{3}'), 'HTTP_200'.
        :returns: The status code's description.
        """
        return self.code_descriptions.get(code) or DEFAULT_CODE_DESC[code]

    @property
    def models(self) -> Iterable[ModelClass]:
        """
        :returns:  dict_values -- all the models in this response
        """
        return self.code_models.values() if self.model_adapter is not None else ()

    def generate_spec(
        self, naming_strategy: NamingStrategy = get_model_key
    ) -> Dict[str, Any]:
        """
        generate the spec for responses

        :returns: JSON
        """
        responses: Dict[str, Any] = {}
        for code in self.codes:
            responses[parse_code(code)] = {
                "description": self.get_code_description(code)
            }

        if self.model_adapter is None:
            raise RuntimeError("Response must be bound to a model adapter")

        for code, model in self.code_models.items():
            model_name = naming_strategy(model)
            responses[parse_code(code)] = {
                "description": self.get_code_description(code),
                "content": {
                    "application/json": {
                        "schema": {"$ref": f"#/components/schemas/{model_name}"}
                    }
                },
            }

        return responses
