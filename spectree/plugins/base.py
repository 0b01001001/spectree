import logging
from collections import namedtuple

Context = namedtuple("Context", ["query", "json", "headers", "cookies"])


class BasePlugin:
    """
    Base plugin for SpecTree plugin classes.

    :param spectree: :class:`spectree.SpecTree` instance
    """

    # ASYNC: is it an async framework or not
    ASYNC = False

    def __init__(self, spectree):
        self.spectree = spectree
        self.config = spectree.config
        self.logger = logging.getLogger(__name__)

    def register_route(self, app):
        """
        :param app: backend framework application

        register document API routes to application
        """
        raise NotImplementedError

    def validate(self, *args, **kwargs):
        """
        validate the request and response
        """
        raise NotImplementedError

    def find_routes(self):
        """
        find the routes from application
        """
        raise NotImplementedError

    def bypass(self, func, method):
        """
        :param func: route function (endpoint)
        :param method: HTTP method for this route function

        bypass some routes that shouldn't be shown in document
        """
        raise NotImplementedError

    def parse_path(self, route):
        """
        :param route: API routes

        parse URI path to get the variables in path
        """
        raise NotImplementedError

    def parse_func(self, route):
        """
        :param route: API routes

        get the endpoint function from routes
        """
        raise NotImplementedError
