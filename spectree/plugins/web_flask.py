from .base import BasePlugin


class FlaskPlugin(BasePlugin):
    def find_routes(self, app):
        pass

    def bypass(self, func, method):
        pass

    def parse_path(self, route):
        pass

    def validate(self, *args, **kwargs):
        pass

    def register_route(self, app, config, spec):
        pass
