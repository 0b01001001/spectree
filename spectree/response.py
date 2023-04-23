from http import HTTPStatus
from typing import Any, Dict, Iterable, List, Optional, Tuple, Union

from pydantic import BaseModel

from ._types import ModelType, NamingStrategy, OptionalModelType
from .utils import gen_list_model, get_model_key, parse_code

# according to https://tools.ietf.org/html/rfc2616#section-10
# https://tools.ietf.org/html/rfc7231#section-6.1
# https://developer.mozilla.org/sv-SE/docs/Web/HTTP/Status
DEFAULT_CODE_DESC: Dict[str, str] = dict(
    (f"HTTP_{status.value}", f"{status.phrase}") for status in HTTPStatus
)
# additional status codes
for code, phrase in [
    ("HTTP_418", "I'm a teapot"),
    ("HTTP_425", "Too Early"),
]:
    DEFAULT_CODE_DESC[code] = phrase


class Response:
    """
    response object

    :param codes: list of HTTP status code, format('HTTP_[0-9]{3}'), 'HTTP_200'
    :param code_models: dict of <HTTP status code>: <`pydantic.BaseModel`> or None or
        a two element tuple of (<`pydantic.BaseModel`> or None) as the first item and
        a custom status code description string as the second item.

    examples:

        >>> from spectree.response import Response
        >>> from pydantic import BaseModel
        ...
        >>> class User(BaseModel):
        ...     id: int
        ...
        >>> response = Response(HTTP_200)
        >>> response = Response(HTTP_200=None)
        >>> response = Response(HTTP_200=User)
        >>> response = Response(HTTP_200=(User, "status code description"))
    """

    def __init__(
        self,
        *codes: str,
        **code_models: Union[OptionalModelType, Tuple[OptionalModelType, str]],
    ) -> None:
        self.codes: List[str] = []

        for code in codes:
            assert code in DEFAULT_CODE_DESC, "invalid HTTP status code"
            self.codes.append(code)

        self.code_models: Dict[str, ModelType] = {}
        self.code_descriptions: Dict[str, Optional[str]] = {}
        for code, model_and_description in code_models.items():
            assert code in DEFAULT_CODE_DESC, "invalid HTTP status code"
            description: Optional[str] = None
            if isinstance(model_and_description, tuple):
                assert len(model_and_description) == 2, (
                    "unexpected number of arguments for a tuple of "
                    "`pydantic.BaseModel` and HTTP status code description"
                )
                model = model_and_description[0]
                description = model_and_description[1]
            else:
                model = model_and_description

            if model:
                origin_type = getattr(model, "__origin__", None)
                if origin_type is list or origin_type is List:
                    # type is List[BaseModel]
                    model = gen_list_model(getattr(model, "__args__")[0])
                assert issubclass(model, BaseModel), "invalid `pydantic.BaseModel`"
                assert description is None or isinstance(
                    description, str
                ), "invalid HTTP status code description"
                self.code_models[code] = model
            else:
                self.codes.append(code)

            if description:
                self.code_descriptions[code] = description

    def add_model(
        self,
        code: int,
        model: ModelType,
        replace: bool = True,
        description: Optional[str] = None,
    ) -> None:
        """Add data *model* for the specified status *code*.

        :param code: An HTTP status code.
        :param model: A `pydantic.BaseModel`.
        :param replace: If `True` and a data *model* already exists for the given
            status *code* it will be replaced, if `False` the existing data *model*
            will be retained.
        :param description: The description string for the code.
        """
        if not replace and self.find_model(code):
            return
        code_name: str = f"HTTP_{code}"
        self.code_models[code_name] = model
        if description:
            self.code_descriptions[code_name] = description

    def has_model(self) -> bool:
        """
        :returns: boolean -- does this response has models or not
        """
        return bool(self.code_models)

    def find_model(self, code: int) -> OptionalModelType:
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
    def models(self) -> Iterable[ModelType]:
        """
        :returns:  dict_values -- all the models in this response
        """
        return self.code_models.values()

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
