

class BasePlugin:
    """
    Base plugin for SpecTree plugin classes.
    """

    def register_route(self, app, config, spec):
        raise NotImplementedError

    def validate(self, query, json, headers, resp):
        raise NotImplementedError

    def find_routes(self, app):
        raise NotImplementedError

    def bypass(self, func, method):
        raise NotImplementedError

    def parse_path(self, route):
        raise NotImplementedError
