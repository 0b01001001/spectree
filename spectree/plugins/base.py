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

from spectree._pydantic import is_partial_base_model_instance, serialize_model_instance
from spectree._types import JsonType, ModelType, OptionalModelType
from spectree.config import Configuration
from spectree.response import Response

if TYPE_CHECKING:
    # to avoid cyclic import
    from spectree.spec import SpecTree


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
    validation_model: OptionalModelType,
    response_payload: Any,
) -> ResponseValidationResult:
    """Validate a given ``response_payload`` against a ``validation_model``.
    This does nothing if ``validation_model is None``.

    :param validation_model: Pydantic model used to validate the provided
        ``response_payload``.
    :param response_payload: Validated response payload. A :class:`RawResponsePayload`
        should be provided when the plugin view function returned an already
        JSON-serialized response payload.
    """
    if not validation_model:
        return ResponseValidationResult(payload=response_payload)

    final_response_payload = None
    skip_validation = False
    if isinstance(response_payload, RawResponsePayload):
        final_response_payload = response_payload.payload
    elif isinstance(response_payload, validation_model):
        skip_validation = True
        final_response_payload = serialize_model_instance(response_payload)
    else:
        # non-BaseModel response or partial BaseModel response
        final_response_payload = response_payload

    if not skip_validation:
        validator = (
            validation_model.parse_raw
            if isinstance(final_response_payload, bytes)
            else validation_model.parse_obj
        )
        validated_instance = validator(final_response_payload)
        # in case the response model contains (alias, default_none, unset fields) which
        # might not be the what the users want, we only return the validated dict when
        # the response contains BaseModel
        if is_partial_base_model_instance(final_response_payload):
            final_response_payload = serialize_model_instance(validated_instance)

    return ResponseValidationResult(payload=final_response_payload)
