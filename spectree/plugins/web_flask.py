from .base import BasePlugin


class FlaskPlugin(BasePlugin):
    def find_routes(self):
        return super().find_routes()

    def bypass(self, func, method):
        return super().bypass(func, method)

    def parse_path(self, route):
        return super().parse_path(route)

    def validate(self, *args, **kwargs):
        pass

    def register_route(self, spectree):
        return super().register_route(spectree)
