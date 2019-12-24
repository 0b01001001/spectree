from collections import namedtuple

Context = namedtuple('Context', ['query', 'json', 'headers', 'cookies'])


class BasePlugin:
    """
    Base plugin for SpecTree plugin classes.
    """

    def __init__(self, spectree):
        self.spectree = spectree
        self.config = spectree.config

    def register_route(self, app):
        raise NotImplementedError

    def validate(self, query, json, headers, resp):
        raise NotImplementedError

    def find_routes(self):
        raise NotImplementedError

    def bypass(self, func, method):
        raise NotImplementedError

    def parse_path(self, route):
        raise NotImplementedError

    def parse_func(self, route):
        raise NotImplementedError
