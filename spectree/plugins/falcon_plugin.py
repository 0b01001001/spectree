import re
from pydantic import ValidationError

from ..utils import pop_keywords
from .base import BasePlugin
from .page import PAGES


class OpenAPI:
    def __init__(self, spec):
        self.spec = spec

    def on_get(self, req, resp):
        resp.media = self.spec


class DocPage:
    def __init__(self, html, spec_url):
        self.page = html.format(spec_url)

    def on_get(self, req, resp):
        resp.content_type = 'text/html'
        resp.body = self.page


DOC_CLASS = [x.__name__ for x in (DocPage, OpenAPI)]


class FlaconPlugin(BasePlugin):
    def __init__(self, spectree):
        super().__init__(spectree)
        from falcon.routing.compiled import _FIELD_PATTERN

        self.FIELD_PATTERN = _FIELD_PATTERN
        # NOTE from `falcon.routing.compiled.CompiledRouterNode`
        self.ESCAPE = r'[\.\(\)\[\]\?\$\*\+\^\|]'
        self.ESCAPE_TO = r'\\\g<0>'
        self.EXTRACT = r'{\2}'
        # NOTE this regex is copied from werkzeug.routing._converter_args_re and
        # modified to support only int args
        self.INT_ARGS = re.compile(r'''
            ((?P<name>\w+)\s*=\s*)?
            (?P<value>\d+)\s*
        ''', re.VERBOSE)
        self.INT_ARGS_NAMES = ('num_digits', 'min', 'max')

    def register_route(self, app):
        self.app = app
        self.app.add_route(
            self.config.spec_url, OpenAPI(self.spectree.spec)
        )
        for ui in PAGES:
            self.app.add_route(
                f'/{self.config.PATH}/{ui}',
                DocPage(PAGES[ui], self.config.spec_url),
            )

    def find_routes(self):
        routes = []

        def find_node(node):
            if node.resource and node.resource.__class__.__name__ not in DOC_CLASS:
                routes.append(node)

            for child in node.children:
                find_node(child)

        for route in self.app._router._roots:
            find_node(route)

        return routes

    def parse_func(self, route):
        return route.method_map.items()

    def parse_path(self, route):
        subs, parameters = [], []
        for segment in route.uri_template.strip('/').split('/'):
            matches = self.FIELD_PATTERN.finditer(segment)
            if not matches:
                subs.append(segment)
                continue

            escaped = re.sub(self.ESCAPE, self.ESCAPE_TO, segment)
            subs.append(self.FIELD_PATTERN.sub(self.EXTRACT, escaped))

            for field in matches:
                variable, converter, argstr = [field.group(name) for name in
                                               ('fname', 'cname', 'argstr')]

                if converter == 'int':
                    if argstr is None:
                        argstr = ''

                    arg_values = [None, None, None]
                    for index, match in enumerate(self.INT_ARGS.finditer(argstr)):
                        name, value = match.group('name'), match.group('value')
                        if name:
                            index = self.INT_ARGS_NAMES.index(name)
                        arg_values[index] = value

                    num_digits, minumum, maximum = arg_values
                    schema = {
                        'type': 'integer',
                        'format': f'int{num_digits}' if num_digits else 'int32',
                    }
                    if minumum:
                        schema['minimum'] = minumum
                    if maximum:
                        schema['maximum'] = maximum
                elif converter == 'uuid':
                    schema = {
                        'type': 'string',
                        'format': 'uuid'
                    }
                elif converter == 'dt':
                    schema = {
                        'type': 'string',
                        'format': 'date-time',
                    }
                else:
                    # no converter specified or customized converters
                    schema = {'type': 'string'}

                parameters.append({
                    'name': variable,
                    'in': 'path',
                    'required': True,
                    'schema': schema,
                })

        return f'/{"/".join(subs)}', parameters

    def validate(self, _req, _resp, *args, **kwargs):
        func, query, json, headers, cookies, resp = pop_keywords(kwargs)
        try:
            if query:
                _req.context.query = query(**_req.params)
            if headers:
                _req.context.headers = headers(**_req.headers)
            if cookies:
                _req.context.cookies = cookies(**_req.cookies)
            media = _req.media or {}
            if json:
                _req.context.media = json(**media)

        except ValidationError as err:
            _resp.status = '422 Unprocessable Entity'
            _resp.media = err.errors()
            return
        except Exception:
            raise

        func(self, _req, _resp, *args, **kwargs)
        if resp:
            _resp.media = _resp.context.media.dict()

    def bypass(self, func, method):
        if not func.args:
            return False
        return True
