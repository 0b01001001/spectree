import sys
from http import HTTPStatus
from typing import Any, Dict, Iterable, List, Optional, Tuple, Union

from spectree._types import NamingStrategy
from spectree.model_adapter import ModelAdapter, ModelClass
from spectree.utils import get_model_key, parse_code

# according to https://tools.ietf.org/html/rfc2616#section-10
# https://tools.ietf.org/html/rfc7231#section-6.1
# https://developer.mozilla.org/sv-SE/docs/Web/HTTP/Status
DEFAULT_CODE_DESC: Dict[str, str] = dict(
    (f"HTTP_{status.value}", f"{status.phrase}") for status in HTTPStatus
)
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
        **code_models: Union[
            Optional[ModelClass],
            Tuple[Optional[ModelClass], str],
            type[List[Any]],
            Tuple[type[List[Any]], str],
        ],
    ) -> None:
        self.model_adapter: Optional[ModelAdapter] = None
        self.codes: List[str] = []
        self._raw_code_models: Dict[str, Any] = {}
        self._raw_list_item_types: Dict[str, ModelClass] = {}

        for code in codes:
            assert code in DEFAULT_CODE_DESC, "invalid HTTP status code"
            self.codes.append(code)

        self.code_models: Dict[str, ModelClass] = {}
        self.code_descriptions: Dict[str, Optional[str]] = {}
        self.code_list_item_types: Dict[str, ModelClass] = {}
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
                origin_type = getattr(model, "__origin__", None)
                if origin_type is list or origin_type is List:
                    self._raw_list_item_types[code] = model.__args__[0]  # type: ignore
                self._raw_code_models[code] = model
                assert description is None or isinstance(description, str), (
                    "invalid HTTP status code description"
                )
            else:
                self.codes.append(code)

            if description:
                self.code_descriptions[code] = description

    def bind_model_adapter(self, model_adapter: ModelAdapter) -> None:
        self.model_adapter = model_adapter
        self.code_models, self.code_list_item_types = self._build_models(model_adapter)

    def _build_models(
        self, model_adapter: ModelAdapter
    ) -> tuple[Dict[str, ModelClass], Dict[str, ModelClass]]:
        code_models: Dict[str, ModelClass] = {}
        code_list_item_types: Dict[str, ModelClass] = {}
        for code, raw_model in self._raw_code_models.items():
            model = raw_model
            origin_type = getattr(model, "__origin__", None)
            if origin_type is list or origin_type is List:
                list_item_type = model.__args__[0]  # type: ignore
                model = model_adapter.make_list_model(list_item_type)
                code_list_item_types[code] = list_item_type
            assert model_adapter.is_model_type(model), (
                f"invalid response model: {model}"
            )
            code_models[code] = model
        return code_models, code_list_item_types

    def add_model(
        self,
        code: int,
        model: ModelClass,
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
        if not replace and self.find_model(code):
            return
        code_name: str = f"HTTP_{code}"
        origin_type = getattr(model, "__origin__", None)
        if origin_type is list or origin_type is List:
            self._raw_list_item_types[code_name] = model.__args__[0]  # type: ignore
        self._raw_code_models[code_name] = model
        if self.model_adapter is not None:
            self.code_models, self.code_list_item_types = self._build_models(
                self.model_adapter
            )
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
        model = self.code_models.get(f"HTTP_{code}")
        if model is not None:
            return model
        raw_model = self._raw_code_models.get(f"HTTP_{code}")
        return raw_model if isinstance(raw_model, type) else None

    def expect_list_result(self, code: int) -> bool:
        """Check whether a specific HTTP code expects a list result.

        :param code: Status code (example: 200)
        """
        code_name = f"HTTP_{code}"
        return (
            code_name in self.code_list_item_types
            or code_name in self._raw_list_item_types
        )

    def get_expected_list_item_type(self, code: int) -> ModelClass:
        """Get the expected list result item type.

        :param code: Status code (example: 200)
        """
        code_name = f"HTTP_{code}"
        return (
            self.code_list_item_types.get(code_name)
            or self._raw_list_item_types[code_name]
        )

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
