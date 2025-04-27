import inspect
from collections import namedtuple
from functools import partial
from json import JSONDecodeError
from typing import Any, Callable, Optional

from starlette.convertors import CONVERTOR_TYPES
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse
from starlette.routing import compile_path

from spectree._pydantic import (
    InternalValidationError,
    ValidationError,
    generate_root_model,
    serialize_model_instance,
)
from spectree._types import ModelType
from spectree.plugins.base import (
    BasePlugin,
    Context,
    RawResponsePayload,
    validate_response,
)
from spectree.response import Response
from spectree.utils import cached_type_hints, get_multidict_items_starlette

METHODS = {"get", "post", "put", "patch", "delete"}
Route = namedtuple("Route", ["path", "methods", "func"])


_PydanticResponseModel = generate_root_model(Any, name="_PydanticResponseModel")


def PydanticResponse(content):
    class _PydanticResponse(JSONResponse):
        def render(self, content) -> bytes:
            self._model_class = content.__class__
            return super().render(
                serialize_model_instance(_PydanticResponseModel.parse_obj(content))
            )

    return _PydanticResponse(content)


class StarlettePlugin(BasePlugin):
    ASYNC = True

    def __init__(self, spectree):
        super().__init__(spectree)

        self.conv2type = {conv: typ for typ, conv in CONVERTOR_TYPES.items()}

    def register_route(self, app):
        app.add_route(
            self.config.spec_url,
            lambda request: JSONResponse(self.spectree.spec),
        )

        for ui in self.config.page_templates:
            app.add_route(
                f"/{self.config.path}/{ui}",
                lambda request, ui=ui: HTMLResponse(
                    self.config.page_templates[ui].format(
                        spec_url=self.config.filename,
                        spec_path=self.config.path,
                        **self.config.swagger_oauth2_config(),
                    )
                ),
            )

    async def request_validation(self, request, query, json, form, headers, cookies):
        has_data = request.method not in ("GET", "DELETE")
        content_type = request.headers.get("content-type", "").lower()
        use_json = json and has_data and content_type == "application/json"
        use_form = (
            form and has_data and any([x in content_type for x in self.FORM_MIMETYPE])
        )
        request.context = Context(
            query.parse_obj(get_multidict_items_starlette(request.query_params))
            if query
            else None,
            json.parse_obj(await request.json() or {}) if use_json else None,
            form.parse_obj(await request.form() or {}) if use_form else None,
            headers.parse_obj(request.headers) if headers else None,
            cookies.parse_obj(request.cookies) if cookies else None,
        )

    async def validate(
        self,
        func: Callable,
        query: Optional[ModelType],
        json: Optional[ModelType],
        form: Optional[ModelType],
        headers: Optional[ModelType],
        cookies: Optional[ModelType],
        resp: Optional[Response],
        before: Callable,
        after: Callable,
        validation_error_status: int,
        skip_validation: bool,
        *args: Any,
        **kwargs: Any,
    ):
        if isinstance(args[0], Request):
            instance, request = None, args[0]
        else:
            instance, request = args[:2]

        response = None
        req_validation_error = resp_validation_error = json_decode_error = None

        if not skip_validation:
            try:
                await self.request_validation(
                    request, query, json, form, headers, cookies
                )
            except (InternalValidationError, ValidationError) as err:
                req_validation_error = err
                response = JSONResponse(
                    err.errors()
                    if isinstance(err, InternalValidationError)
                    else err.errors(include_context=False),
                    validation_error_status,
                )
            except JSONDecodeError as err:
                json_decode_error = err
                self.logger.info(
                    "%s Validation Error",
                    validation_error_status,
                    extra={"spectree_json_decode_error": str(err)},
                )
                response = JSONResponse(
                    {"error_msg": str(err)}, validation_error_status
                )

        before(request, response, req_validation_error, instance)
        if req_validation_error or json_decode_error:
            return response

        if self.config.annotations:
            annotations = cached_type_hints(func)
            for name in ("query", "json", "form", "headers", "cookies"):
                if annotations.get(name):
                    kwargs[name] = getattr(
                        getattr(request, "context", None), name, None
                    )

        if inspect.iscoroutinefunction(func):
            response = await func(*args, **kwargs)
        else:
            response = func(*args, **kwargs)

        if (
            not skip_validation
            and resp
            and response
            and not (
                isinstance(response, JSONResponse)
                and hasattr(response, "_model_class")
                and response._model_class == resp.find_model(response.status_code)
            )
        ):
            try:
                validate_response(
                    validation_model=resp.find_model(response.status_code),
                    response_payload=RawResponsePayload(payload=response.body),
                )
            except (InternalValidationError, ValidationError) as err:
                response = JSONResponse(
                    err.errors()
                    if isinstance(err, InternalValidationError)
                    else err.errors(include_context=False),
                    500,
                )
                resp_validation_error = err

        after(request, response, resp_validation_error, instance)

        return response

    def find_routes(self):
        routes = []

        def parse_route(app, prefix=""):
            # :class:`starlette.staticfiles.StaticFiles` doesn't have routes
            if not app.routes:
                return
            for route in app.routes:
                if route.path.startswith(f"/{self.config.path}"):
                    continue

                func = route.app
                if isinstance(func, partial):
                    try:
                        func = func.__wrapped__
                    except AttributeError as err:
                        self.logger.warning(
                            "failed to get the wrapped func %s: %s", func, err
                        )

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

        parse_route(self.spectree.app)
        return routes

    def bypass(self, func, method):
        return method in ["HEAD", "OPTIONS"]

    def parse_func(self, route):
        for method in route.methods or ["GET"]:
            yield method, route.func

    def parse_path(self, route, path_parameter_descriptions):
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

            description = (
                path_parameter_descriptions.get(name, "")
                if path_parameter_descriptions
                else ""
            )
            parameters.append(
                {
                    "name": name,
                    "in": "path",
                    "required": True,
                    "schema": schema,
                    "description": description,
                }
            )

        return path, parameters
