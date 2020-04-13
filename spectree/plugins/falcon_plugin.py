import re
import inspect
from functools import partial
from pydantic import ValidationError

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


class OpenAPIAsgi(OpenAPI):
    async def on_get(self, req, resp):
        super().on_get(req, resp)


class DocPageAsgi(DocPage):
    async def on_get(self, req, resp):
        super().on_get(req, resp)


DOC_CLASS = [x.__name__ for x in (DocPage, OpenAPI, DocPageAsgi, OpenAPIAsgi)]

HTTP_422 = '422 Unprocessable Entity'


class FalconPlugin(BasePlugin):
    BASE_ROUTE = OpenAPI
    BASE_DOC_ROUTE = DocPage

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
            self.config.spec_url, self.BASE_ROUTE(self.spectree.spec)
        )
        for ui in PAGES:
            self.app.add_route(
                f'/{self.config.PATH}/{ui}',
                self.BASE_DOC_ROUTE(PAGES[ui], self.config.spec_url),
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

    def request_validation(self, req, query, json, headers, cookies):
        if query:
            req.context.query = query(**req.params)
        if headers:
            req.context.headers = headers(**req.headers)
        if cookies:
            req.context.cookies = cookies(**req.cookies)
        media = req.media or {}
        if json:
            req.context.json = json(**media)

    def validate(self, func, query, json, headers, cookies, resp, *args, **kwargs):
        # falcon endpoint method arguments: (self, req, resp)
        _self, _req, _resp = args[:3]
        try:
            self.request_validation(_req, query, json, headers, cookies)

        except ValidationError as err:
            self.logger.info(
                HTTP_422,
                extra={
                    'spectree_model': err.model.__name__,
                    'spectree_validation': err.errors(),
                },
            )
            _resp.status = HTTP_422
            _resp.media = err.errors()
            return
        except Exception:
            raise

        func(*args, **kwargs)
        if resp and resp.has_model():
            model = resp.find_model(_resp.status[:3])
            if model:
                model.validate(_resp.media)

    def bypass(self, func, method):
        if not isinstance(func, partial):
            return False
        if inspect.ismethod(func.func):
            return False
        # others are <cyfunction>
        return True

class FalconAsgiPlugin(FalconPlugin):
    """Light wrapper around default Falcon plug-in to support Falcon 3.0 ASGI apps"""
    IS_ASYNC = True
    BASE_ROUTE = OpenAPIAsgi
    BASE_DOC_ROUTE = DocPageAsgi

    async def request_validation(self, req, query, json, headers, cookies):
        if query:
            req.context.query = query(**req.params)
        if headers:
            req.context.headers = headers(**req.headers)
        if cookies:
            req.context.cookies = cookies(**req.cookies)
        if json:
            # `get_media()` is required for async Falcon apps, but will throw an exception if
            #  there is no JSON. To avoid accidentally hiding when we have legitimately invalid
            #  JSON, we only check for the media if we are expecting JSON input
            media = await req.get_media() or {}
            req.context.json = json(**media)

    async def validate(self, func, query, json, headers, cookies, resp, *args, **kwargs):
        # Falcon endpoint method arguments: (self, req, resp)
        _self, _req, _resp = args[:3]
        try:
            await self.request_validation(_req, query, json, headers, cookies)
        except ValidationError as err:
            self.logger.info(
                HTTP_422,
                extra={
                    'spectree_model': err.model.__name__,
                    'spectree_validation': err.errors(),
                },
            )
            _resp.status = HTTP_422
            _resp.media = err.errors()
            return
        except Exception:
            raise

        if inspect.iscoroutinefunction(func):
            await func(*args, **kwargs)
        else:
            func(*args, **kwargs)

        if resp and resp.has_model():
            model = resp.find_model(_resp.status[:3])
            if model:
                model.validate(_resp.media)

