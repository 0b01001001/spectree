import inspect
from json import loads as json_loads
from collections import namedtuple
from functools import partial
from pydantic import ValidationError

from ..utils import pop_keywords
from .base import BasePlugin, Context
from .page import PAGES


METHODS = {'get', 'post', 'put', 'patch', 'delete'}
Route = namedtuple('Route', ['path', 'methods', 'func'])


class StarlettePlugin(BasePlugin):
    def __init__(self, spectree):
        super().__init__(spectree)
        from starlette.convertors import CONVERTOR_TYPES
        self.conv2type = {
            conv: typ for typ, conv in CONVERTOR_TYPES.items()
        }

    def register_route(self, app):
        self.app = app
        from starlette.responses import JSONResponse, HTMLResponse

        self.app.add_route(
            self.config.spec_url,
            lambda request: JSONResponse(self.spectree.spec),
        )

        for ui in PAGES:
            self.app.add_route(
                f'/{self.config.PATH}/{ui}',
                lambda request, ui=ui: HTMLResponse(
                    PAGES[ui].format(self.config.spec_url)
                ),
            )

    async def validate(self, scope, receive, send, *args, **kwargs):
        from starlette.requests import Request
        from starlette.responses import JSONResponse

        func, query, json, headers, cookies, resp = pop_keywords(kwargs)

        request = Request(scope, receive)
        try:
            request.context = Context(
                query(**request.query_params) if query else None,
                json(**(await request.json())) if json else None,
                headers(**request.headers) if headers else None,
                cookies(**request.cookies) if cookies else None,
            )
        except ValidationError as err:
            return JSONResponse(err.errors(), 422)
        except Exception:
            raise

        if inspect.iscoroutinefunction(func):
            response = await func(request, *args, **kwargs)
        else:
            response = func(request, *args, **kwargs)

        if resp:
            model = resp.find_model(response.status_code)
            model.validate(json_loads(response.body))

        await response(scope, receive, send)

    def find_routes(self):
        routes = []

        def parse_route(app, prefix=''):
            for route in app.routes:
                if route.path.startswith(f'/{self.config.PATH}'):
                    continue

                func = route.endpoint
                if isinstance(func, partial):
                    try:
                        func = func.__wrapped__
                    except AttributeError:
                        pass

                if inspect.isclass(func):
                    for method in METHODS:
                        if getattr(func, method, None):
                            routes.append(Route(
                                f'{prefix}{route.path}',
                                {method.upper()},
                                getattr(func, method)
                            ))
                elif inspect.isfunction(func):
                    routes.append(Route(
                        f'{prefix}{route.path}',
                        route.methods,
                        route.endpoint))
                else:
                    parse_route(route, prefix=f'{prefix}{route.path}')

        parse_route(self.app)
        return routes

    def bypass(self, func, method):
        if method in ['HEAD', 'OPTIONS']:
            return True
        return False

    def parse_func(self, route):
        for method in route.methods or ['GET']:
            yield method, route.func

    def parse_path(self, route):
        from starlette.routing import compile_path
        variables = compile_path(route.path)[-1]
        parameters = []

        for name, conv in variables.items():
            schema = None
            typ = self.conv2type[conv]
            if typ == 'int':
                schema = {
                    'type': 'integer',
                    'format': 'int32'
                }
            elif typ == 'float':
                schema = {
                    'type': 'number',
                    'format': 'float',
                }
            elif typ == 'path':
                schema = {
                    'type': 'string',
                    'format': 'path',
                }
            elif typ == 'str':
                schema = {'type': 'string'}

            parameters.append({
                'name': name,
                'in': 'path',
                'required': True,
                'schema': schema,
            })

        return route.path, parameters
