import inspect
from collections import namedtuple
from contextvars import ContextVar
from functools import partial
from json import JSONDecodeError
from typing import Any, Callable, Optional

from starlette.convertors import CONVERTOR_TYPES
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse
from starlette.routing import compile_path

from spectree._types import HookHandler, ModelAdapterType
from spectree.model_adapter import ModelSpec
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
_active_model_adapter: ContextVar[ModelAdapterType | None] = ContextVar(
    "spectree_starlette_model_adapter",
    default=None,
)
_response_models: dict[object, ModelSpec] = {}


def _get_response_model(model_adapter: ModelAdapterType) -> ModelSpec:
    response_model = _response_models.get(model_adapter)
    if response_model is None:
        response_model = model_adapter.make_root_model(
            Any,
            name="_SpecTreeStarletteResponseModel",
        )
        _response_models[model_adapter] = response_model
    return response_model


def _get_starlette_response_model_adapter() -> ModelAdapterType:
    model_adapter = _active_model_adapter.get()
    if model_adapter is None:
        raise RuntimeError(
            "SpecTreeStarletteResponse must be rendered inside a SpecTree request"
        )
    return model_adapter


class SpecTreeStarletteResponse(JSONResponse):
    def render(self, content) -> bytes:
        adapter = _get_starlette_response_model_adapter()
        response_model = _get_response_model(adapter)
        self._model_class = content.__class__
        return adapter.dump_json(adapter.validate_obj(response_model, content))


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
            self.model_adapter.validate_obj(
                query, get_multidict_items_starlette(request.query_params, query)
            )
            if query
            else None,
            self.model_adapter.validate_obj(json, await request.json() or {})
            if use_json
            else None,
            self.model_adapter.validate_obj(form, await request.form() or {})
            if use_form
            else None,
            self.model_adapter.validate_obj(headers, request.headers)
            if headers
            else None,
            self.model_adapter.validate_obj(cookies, request.cookies)
            if cookies
            else None,
        )

    async def validate(
        self,
        func: Callable,
        query: Optional[ModelSpec],
        json: Optional[ModelSpec],
        form: Optional[ModelSpec],
        headers: Optional[ModelSpec],
        cookies: Optional[ModelSpec],
        resp: Optional[Response],
        before: HookHandler,
        after: HookHandler,
        validation_error_status: int,
        skip_validation: bool,
        force_resp_serialize: bool,
        *args: Any,
        **kwargs: Any,
    ):
        async def call_with_model_adapter() -> Any:
            model_adapter_token = _active_model_adapter.set(self.model_adapter)
            try:
                if inspect.iscoroutinefunction(func):
                    return await func(*args, **kwargs)
                return func(*args, **kwargs)
            finally:
                _active_model_adapter.reset(model_adapter_token)

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
            except self.model_adapter.validation_error as err:
                req_validation_error = err
                response = JSONResponse(
                    self.model_adapter.validation_errors(err),
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

        before(request, response, req_validation_error, instance, self.model_adapter)
        if req_validation_error or json_decode_error:
            return response

        if self.config.annotations:
            annotations = cached_type_hints(func)
            for name in ("query", "json", "form", "headers", "cookies"):
                if annotations.get(name):
                    kwargs[name] = getattr(
                        getattr(request, "context", None), name, None
                    )

        response = await call_with_model_adapter()

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
                response_validation_result = validate_response(
                    model_adapter=self.model_adapter,
                    validation_model=resp.find_model(response.status_code),
                    response_payload=RawResponsePayload(payload=response.body),
                    force_serialize=force_resp_serialize,
                )
            except self.model_adapter.validation_error as err:
                response = JSONResponse(
                    self.model_adapter.validation_errors(err),
                    500,
                )
                resp_validation_error = err
            else:
                # replace the body of the response if it was serialized during validation
                if isinstance(response_validation_result.payload, bytes):
                    response.body = response_validation_result.payload

        after(request, response, resp_validation_error, instance, self.model_adapter)

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
