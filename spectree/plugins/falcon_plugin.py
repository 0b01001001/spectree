import inspect
import re
from functools import partial
from typing import Any, Callable, Dict, List, Mapping, Optional, get_type_hints

from falcon import HTTP_400, HTTP_415, HTTPError
from falcon.routing.compiled import _FIELD_PATTERN as FALCON_FIELD_PATTERN
from pydantic import ValidationError

from .._types import ModelType
from ..response import Response
from .base import BasePlugin


class OpenAPI:
    def __init__(self, spec: Mapping[str, str]):
        self.spec = spec

    def on_get(self, _: Any, resp: Any):
        resp.media = self.spec


class DocPage:
    def __init__(self, html: str, **kwargs: Any):
        self.page = html.format(**kwargs)

    def on_get(self, _: Any, resp: Any):
        resp.content_type = "text/html"
        resp.text = self.page


class OpenAPIAsgi(OpenAPI):
    async def on_get(self, req: Any, resp: Any):
        super().on_get(req, resp)


class DocPageAsgi(DocPage):
    async def on_get(self, req: Any, resp: Any):
        super().on_get(req, resp)


DOC_CLASS: List[str] = [
    x.__name__ for x in (DocPage, OpenAPI, DocPageAsgi, OpenAPIAsgi)
]

HTTP_500: str = "500 Internal Service Response Validation Error"


class FalconPlugin(BasePlugin):
    OPEN_API_ROUTE_CLASS = OpenAPI
    DOC_PAGE_ROUTE_CLASS = DocPage

    def __init__(self, spectree):
        super().__init__(spectree)

        self.FALCON_MEDIA_ERROR_CODE = (HTTP_400, HTTP_415)
        # NOTE from `falcon.routing.compiled.CompiledRouterNode`
        self.ESCAPE = r"[\.\(\)\[\]\?\$\*\+\^\|]"
        self.ESCAPE_TO = r"\\\g<0>"
        self.EXTRACT = r"{\2}"
        # NOTE this regex is copied from werkzeug.routing._converter_args_re and
        # modified to support only int args
        self.INT_ARGS = re.compile(
            r"""
            ((?P<name>\w+)\s*=\s*)?
            (?P<value>\d+)\s*
        """,
            re.VERBOSE,
        )
        self.INT_ARGS_NAMES = ("num_digits", "min", "max")

    def register_route(self, app: Any):
        self.app = app
        self.app.add_route(
            self.config.spec_url, self.OPEN_API_ROUTE_CLASS(self.spectree.spec)
        )
        for ui in self.config.page_templates:
            self.app.add_route(
                f"/{self.config.path}/{ui}",
                self.DOC_PAGE_ROUTE_CLASS(
                    self.config.page_templates[ui],
                    spec_url=self.config.spec_url,
                    spec_path=self.config.path,
                    **self.config.swagger_oauth2_config(),
                ),
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

    def parse_func(self, route: Any) -> Dict[str, Any]:
        return route.method_map.items()

    def parse_path(self, route, path_parameter_descriptions):
        subs, parameters = [], []
        for segment in route.uri_template.strip("/").split("/"):
            matches = FALCON_FIELD_PATTERN.finditer(segment)
            if not matches:
                subs.append(segment)
                continue

            escaped = re.sub(self.ESCAPE, self.ESCAPE_TO, segment)
            subs.append(FALCON_FIELD_PATTERN.sub(self.EXTRACT, escaped))

            for field in matches:
                variable, converter, argstr = [
                    field.group(name) for name in ("fname", "cname", "argstr")
                ]

                if converter == "int":
                    if argstr is None:
                        argstr = ""

                    arg_values = [None, None, None]
                    for index, match in enumerate(self.INT_ARGS.finditer(argstr)):
                        name, value = match.group("name"), match.group("value")
                        if name:
                            index = self.INT_ARGS_NAMES.index(name)
                        arg_values[index] = value

                    num_digits, minumum, maximum = arg_values
                    schema = {
                        "type": "integer",
                        "format": f"int{num_digits}" if num_digits else "int32",
                    }
                    if minumum:
                        schema["minimum"] = minumum
                    if maximum:
                        schema["maximum"] = maximum
                elif converter == "uuid":
                    schema = {"type": "string", "format": "uuid"}
                elif converter == "dt":
                    schema = {
                        "type": "string",
                        "format": "date-time",
                    }
                else:
                    # no converter specified or customized converters
                    schema = {"type": "string"}

                description = (
                    path_parameter_descriptions.get(variable, "")
                    if path_parameter_descriptions
                    else ""
                )
                parameters.append(
                    {
                        "name": variable,
                        "in": "path",
                        "required": True,
                        "schema": schema,
                        "description": description,
                    }
                )

        return f'/{"/".join(subs)}', parameters

    def request_validation(self, req, query, json, form, headers, cookies):
        if query:
            req.context.query = query.parse_obj(req.params)
        if headers:
            req.context.headers = headers.parse_obj(req.headers)
        if cookies:
            req.context.cookies = cookies.parse_obj(req.cookies)
        if json:
            try:
                media = req.media
            except HTTPError as err:
                if err.status not in self.FALCON_MEDIA_ERROR_CODE:
                    raise
                media = None
            req.context.json = json.parse_obj(media)
        if form:
            # TODO - possible to pass the BodyPart here?
            # req_form = {x.name: x for x in req.get_media()}
            req_form = {x.name: x.stream.read() for x in req.get_media()}
            req.context.form = form.parse_obj(req_form)

    def validate(
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
        # falcon endpoint method arguments: (self, req, resp)
        _self, _req, _resp = args[:3]
        req_validation_error, resp_validation_error = None, None
        try:
            self.request_validation(_req, query, json, form, headers, cookies)
            if self.config.annotations:
                annotations = get_type_hints(func)
                for name in ("query", "json", "form", "headers", "cookies"):
                    if annotations.get(name):
                        kwargs[name] = getattr(_req.context, name)

        except ValidationError as err:
            req_validation_error = err
            _resp.status = f"{validation_error_status} Validation Error"
            _resp.media = err.errors()

        before(_req, _resp, req_validation_error, _self)
        if req_validation_error:
            return

        func(*args, **kwargs)

        if resp and resp.has_model():
            model = resp.find_model(_resp.status[:3])
            if model and isinstance(_resp.media, model):
                _resp.media = _resp.media.dict()
                skip_validation = True

            if model and not skip_validation:
                try:
                    model.parse_obj(_resp.media)
                except ValidationError as err:
                    resp_validation_error = err
                    _resp.status = HTTP_500
                    _resp.media = err.errors()

        after(_req, _resp, resp_validation_error, _self)

    def bypass(self, func, method):
        if isinstance(func, partial):
            return True
        return inspect.isfunction(func)


class FalconAsgiPlugin(FalconPlugin):
    """Light wrapper around default Falcon plug-in to support Falcon 3.0 ASGI apps"""

    ASYNC = True
    OPEN_API_ROUTE_CLASS = OpenAPIAsgi
    DOC_PAGE_ROUTE_CLASS = DocPageAsgi

    async def request_validation(self, req, query, json, form, headers, cookies):
        if query:
            req.context.query = query.parse_obj(req.params)
        if headers:
            req.context.headers = headers.parse_obj(req.headers)
        if cookies:
            req.context.cookies = cookies.parse_obj(req.cookies)
        if json:
            try:
                media = await req.get_media()
            except HTTPError as err:
                if err.status not in self.FALCON_MEDIA_ERROR_CODE:
                    raise
                media = None
            req.context.json = json.parse_obj(media)
        if form:
            try:
                form_data = await req.get_media()
            except HTTPError as err:
                if err.status not in self.FALCON_MEDIA_ERROR_CODE:
                    raise
                req.context.form = None
            else:
                res_data = {}
                async for x in form_data:
                    res_data[x.name] = x
                    await x.data  # TODO - how to avoid this?
                req.context.form = form.parse_obj(res_data)

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
        # falcon endpoint method arguments: (self, req, resp)
        _self, _req, _resp = args[:3]
        req_validation_error, resp_validation_error = None, None
        try:
            await self.request_validation(_req, query, json, form, headers, cookies)
            if self.config.annotations:
                annotations = get_type_hints(func)
                for name in ("query", "json", "form", "headers", "cookies"):
                    if annotations.get(name):
                        kwargs[name] = getattr(_req.context, name)

        except ValidationError as err:
            req_validation_error = err
            _resp.status = f"{validation_error_status} Validation Error"
            _resp.media = err.errors()

        before(_req, _resp, req_validation_error, _self)
        if req_validation_error:
            return

        await func(*args, **kwargs)

        if resp and resp.has_model():
            model = resp.find_model(_resp.status[:3])
            if model and isinstance(_resp.media, model):
                _resp.media = _resp.media.dict()
                skip_validation = True

            model = resp.find_model(_resp.status[:3])
            if model and not skip_validation:
                try:
                    model.parse_obj(_resp.media)
                except ValidationError as err:
                    resp_validation_error = err
                    _resp.status = HTTP_500
                    _resp.media = err.errors()

        after(_req, _resp, resp_validation_error, _self)
