import inspect
from collections import namedtuple
from functools import partial
from json import JSONDecodeError
from json import loads as json_loads

from pydantic import ValidationError

from .base import BasePlugin, Context
from .page import PAGES

METHODS = {"get", "post", "put", "patch", "delete"}
Route = namedtuple("Route", ["path", "methods", "func"])


class StarlettePlugin(BasePlugin):
    ASYNC = True

    def __init__(self, spectree):
        super().__init__(spectree)
        from starlette.convertors import CONVERTOR_TYPES

        self.conv2type = {conv: typ for typ, conv in CONVERTOR_TYPES.items()}

    def register_route(self, app):
        self.app = app
        from starlette.responses import HTMLResponse, JSONResponse

        self.app.add_route(
            self.config.spec_url,
            lambda request: JSONResponse(self.spectree.spec),
        )

        for ui in PAGES:
            self.app.add_route(
                f"/{self.config.PATH}/{ui}",
                lambda request, ui=ui: HTMLResponse(
                    PAGES[ui].format(self.config.spec_url)
                ),
            )

    async def request_validation(self, request, query, json, headers, cookies):
        request.context = Context(
            query.parse_obj(request.query_params) if query else None,
            json.parse_obj(json_loads(await request.body() or "{}")) if json else None,
            headers.parse_obj(request.headers) if headers else None,
            cookies.parse_obj(request.cookies) if cookies else None,
        )

    async def validate(
        self, func, query, json, headers, cookies, resp, before, after, *args, **kwargs
    ):
        from starlette.responses import JSONResponse

        # NOTE: If func is a `HTTPEndpoint`, it should have '.' in its ``__qualname__``
        # This is not elegant. But it seems `inspect` doesn't work here.
        instance = args[0] if "." in func.__qualname__ else None
        request = args[1] if "." in func.__qualname__ else args[0]
        response = None
        req_validation_error, resp_validation_error, json_decode_error = (
            None,
            None,
            None,
        )

        try:
            await self.request_validation(request, query, json, headers, cookies)
            if self.config.ANNOTATIONS:
                for name in ("query", "json", "headers", "cookies"):
                    if func.__annotations__.get(name):
                        kwargs[name] = getattr(request.context, name)
        except ValidationError as err:
            req_validation_error = err
            response = JSONResponse(err.errors(), 422)
        except JSONDecodeError as err:
            json_decode_error = err
            self.logger.info(
                "422 Validation Error", extra={"spectree_json_decode_error": str(err)}
            )
            response = JSONResponse({"error_msg": str(err)}, 422)

        before(request, response, req_validation_error, instance)
        if req_validation_error or json_decode_error:
            return response

        if inspect.iscoroutinefunction(func):
            response = await func(*args, **kwargs)
        else:
            response = func(*args, **kwargs)

        if resp:
            model = resp.find_model(response.status_code)
            if model:
                try:
                    model.parse_obj(json_loads(response.body))
                except ValidationError as err:
                    resp_validation_error = err
                    response = JSONResponse(err.errors(), 500)

        after(request, response, resp_validation_error, instance)

        return response

    def find_routes(self):
        routes = []

        def parse_route(app, prefix=""):
            # :class:`starlette.staticfiles.StaticFiles` doesn't have routes
            if not app.routes:
                return
            for route in app.routes:
                if route.path.startswith(f"/{self.config.PATH}"):
                    continue

                func = route.app
                if isinstance(func, partial):
                    try:
                        func = func.__wrapped__
                    except AttributeError:
                        pass

                if inspect.isclass(func):
                    for method in METHODS:
                        if getattr(func, method, None):
                            routes.append(
                                Route(
                                    f"{prefix}{route.path}",
                                    {method.upper()},
                                    getattr(func, method),
                                )
                            )
                elif inspect.isfunction(func):
                    routes.append(
                        Route(f"{prefix}{route.path}", route.methods, route.endpoint)
                    )
                else:
                    parse_route(route, prefix=f"{prefix}{route.path}")

        parse_route(self.app)
        return routes

    def bypass(self, func, method):
        if method in ["HEAD", "OPTIONS"]:
            return True
        return False

    def parse_func(self, route):
        for method in route.methods or ["GET"]:
            yield method, route.func

    def parse_path(self, route):
        from starlette.routing import compile_path

        _, path, variables = compile_path(route.path)
        parameters = []

        for name, conv in variables.items():
            schema = None
            typ = self.conv2type[conv]
            if typ == "int":
                schema = {"type": "integer", "format": "int32"}
            elif typ == "float":
                schema = {
                    "type": "number",
                    "format": "float",
                }
            elif typ == "path":
                schema = {
                    "type": "string",
                    "format": "path",
                }
            elif typ == "str":
                schema = {"type": "string"}

            parameters.append(
                {
                    "name": name,
                    "in": "path",
                    "required": True,
                    "schema": schema,
                }
            )

        return path, parameters
