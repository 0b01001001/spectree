import logging
from collections import namedtuple
from typing import TYPE_CHECKING, Any, Callable, Generic, Mapping, TypeVar

from ..config import Configuration

if TYPE_CHECKING:
    # to avoid cyclic import
    from ..spec import SpecTree

Context = namedtuple("Context", ["query", "json", "headers", "cookies"])


BackendRoute = TypeVar("BackendRoute")


class BasePlugin(Generic[BackendRoute]):
    """
    Base plugin for SpecTree plugin classes.

    :param spectree: :class:`spectree.SpecTree` instance
    """

    # ASYNC: is it an async framework or not
    ASYNC = False

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

    def validate(self, *args: Any, **kwargs: Any):
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

    def parse_path(self, route: Any, path_parameter_descriptions: Mapping[str, str]):
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
