import logging
from dataclasses import dataclass
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Generic,
    Mapping,
    NamedTuple,
    Optional,
    TypeVar,
    Union,
)

from .._pydantic import ValidationError, is_root_model, serialize_model_instance
from .._types import JsonType, ModelType, OptionalModelType
from ..config import Configuration
from ..response import Response

if TYPE_CHECKING:
    # to avoid cyclic import
    from ..spec import SpecTree


class Context(NamedTuple):
    query: list
    json: list
    form: list
    headers: dict
    cookies: dict


BackendRoute = TypeVar("BackendRoute")


class BasePlugin(Generic[BackendRoute]):
    """
    Base plugin for SpecTree plugin classes.

    :param spectree: :class:`spectree.SpecTree` instance
    """

    # ASYNC: is it an async framework or not
    ASYNC = False
    FORM_MIMETYPE = ("application/x-www-form-urlencoded", "multipart/form-data")

    def __init__(self, spectree: "SpecTree"):
        self.spectree = spectree
        self.config: Configuration = spectree.config
        self.logger = logging.getLogger(__name__)

    def register_route(self, app: Any):
        """
        :param app: backend framework application

        register document API routes to application
        """
        raise NotImplementedError

    def validate(
        self,
        func: Callable,
        query: Optional[ModelType],
        json: Optional[ModelType],
        form: Optional[ModelType],
        headers: Optional[ModelType],
        cookies: Optional[ModelType],
        resp: Optional[Response],
        before: Callable,
        after: Callable,
        validation_error_status: int,
        skip_validation: bool,
        *args: Any,
        **kwargs: Any,
    ):
        """
        validate the request and response
        """
        raise NotImplementedError

    def find_routes(self) -> BackendRoute:
        """
        find the routes from application
        """
        raise NotImplementedError

    def bypass(self, func: Callable, method: str) -> bool:
        """
        :param func: route function (endpoint)
        :param method: HTTP method for this route function

        bypass some routes that shouldn't be shown in document
        """
        raise NotImplementedError

    def parse_path(
        self, route: Any, path_parameter_descriptions: Optional[Mapping[str, str]]
    ):
        """
        :param route: API routes
        :param path_parameter_descriptions: A dictionary of path parameter names and
            their description.

        parse URI path to get the variables in path
        """
        raise NotImplementedError

    def parse_func(self, route: BackendRoute):
        """
        :param route: API routes

        get the endpoint function from routes
        """
        raise NotImplementedError

    def get_func_operation_id(self, func: Callable, path: str, method: str):
        """
        :param func: route function (endpoint)
        :param method: URI path for this route function
        :param method: HTTP method for this route function

        get the operation_id value for the endpoint
        """
        operation_id = getattr(func, "operation_id", None)
        if not operation_id:
            operation_id = f"{method.lower()}_{path.replace('/', '_')}"
        return operation_id


@dataclass(frozen=True)
class RawResponsePayload:
    payload: Union[JsonType, bytes]


@dataclass(frozen=True)
class ResponseValidationResult:
    payload: Any


def validate_response(
    skip_validation: bool,
    validation_model: OptionalModelType,
    response_payload: Any,
):
    """Validate a given `response_payload` against a `validation_model`.

    :param skip_validation: When set to true, validation is not carried out
        and the input `response_payload` is returned as-is. This is equivalent
        to not providing a `validation_model`.
    :param validation_model: Pydantic model used to validate the provided
        `response_payload`.
    :param response_payload: Validated response payload. A `RawResponsePayload`
        should be provided when the plugin view function returned an already
        JSON-serialized response payload.
    """
    final_response_payload = None
    if isinstance(response_payload, RawResponsePayload):
        final_response_payload = response_payload.payload
    elif skip_validation or validation_model is None:
        final_response_payload = response_payload

    if not skip_validation and validation_model and not final_response_payload:
        if isinstance(response_payload, validation_model):
            skip_validation = True
            final_response_payload = serialize_model_instance(response_payload)
        elif is_root_model(validation_model) and not isinstance(
            response_payload, validation_model
        ):
            # Make it possible to return an instance of the model __root__ type
            # (i.e. not the root model itself).
            try:
                response_payload = validation_model(__root__=response_payload)
            except ValidationError:
                raise
            else:
                skip_validation = True
                final_response_payload = serialize_model_instance(response_payload)
        else:
            final_response_payload = response_payload

    if validation_model and not skip_validation:
        validator = (
            validation_model.parse_raw
            if isinstance(final_response_payload, bytes)
            else validation_model.parse_obj
        )
        validator(final_response_payload)

    return ResponseValidationResult(payload=final_response_payload)
