import logging
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Generic,
    Mapping,
    NamedTuple,
    Optional,
    TypeVar,
)

from .._types import ModelType
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
