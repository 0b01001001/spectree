from typing import Any, Dict, Iterable, List, Optional, Tuple, Union

from pydantic import BaseModel

from ._types import ModelType, OptionalModelType
from .utils import gen_list_model, get_model_key, parse_code


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

    def generate_spec(self) -> Dict[str, Any]:
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
            model_name = get_model_key(model=model)
            responses[parse_code(code)] = {
                "description": self.get_code_description(code),
                "content": {
                    "application/json": {
                        "schema": {"$ref": f"#/components/schemas/{model_name}"}
                    }
                },
            }

        return responses


# according to https://tools.ietf.org/html/rfc2616#section-10
# https://tools.ietf.org/html/rfc7231#section-6.1
# https://developer.mozilla.org/sv-SE/docs/Web/HTTP/Status
DEFAULT_CODE_DESC: Dict[str, str] = {
    # Information 1xx
    "HTTP_100": "Continue",
    "HTTP_101": "Switching Protocols",
    # Successful 2xx
    "HTTP_200": "OK",
    "HTTP_201": "Created",
    "HTTP_202": "Accepted",
    "HTTP_203": "Non-Authoritative Information",
    "HTTP_204": "No Content",
    "HTTP_205": "Reset Content",
    "HTTP_206": "Partial Content",
    # Redirection 3xx
    "HTTP_300": "Multiple Choices",
    "HTTP_301": "Moved Permanently",
    "HTTP_302": "Found",
    "HTTP_303": "See Other",
    "HTTP_304": "Not Modified",
    "HTTP_305": "Use Proxy",
    "HTTP_306": "(Unused)",
    "HTTP_307": "Temporary Redirect",
    "HTTP_308": "Permanent Redirect",
    # Client Error 4xx
    "HTTP_400": "Bad Request",
    "HTTP_401": "Unauthorized",
    "HTTP_402": "Payment Required",
    "HTTP_403": "Forbidden",
    "HTTP_404": "Not Found",
    "HTTP_405": "Method Not Allowed",
    "HTTP_406": "Not Acceptable",
    "HTTP_407": "Proxy Authentication Required",
    "HTTP_408": "Request Timeout",
    "HTTP_409": "Conflict",
    "HTTP_410": "Gone",
    "HTTP_411": "Length Required",
    "HTTP_412": "Precondition Failed",
    "HTTP_413": "Request Entity Too Large",
    "HTTP_414": "Request-URI Too Long",
    "HTTP_415": "Unsupported Media Type",
    "HTTP_416": "Requested Range Not Satisfiable",
    "HTTP_417": "Expectation Failed",
    "HTTP_418": "I'm a teapot",
    "HTTP_421": "Misdirected Request",
    "HTTP_422": "Unprocessable Entity",
    "HTTP_423": "Locked",
    "HTTP_424": "Failed Dependency",
    "HTTP_425": "Too Early",
    "HTTP_426": "Upgrade Required",
    "HTTP_428": "Precondition Required",
    "HTTP_429": "Too Many Requests",
    "HTTP_431": "Request Header Fields Too Large",
    "HTTP_451": "Unavailable For Legal Reasons",
    # Server Error 5xx
    "HTTP_500": "Internal Server Error",
    "HTTP_501": "Not Implemented",
    "HTTP_502": "Bad Gateway",
    "HTTP_503": "Service Unavailable",
    "HTTP_504": "Gateway Timeout",
    "HTTP_505": "HTTP Version Not Supported",
    "HTTP_506": "Variant Also negotiates",
    "HTTP_507": "Insufficient Sotrage",
    "HTTP_508": "Loop Detected",
    "HTTP_511": "Network Authentication Required",
}
