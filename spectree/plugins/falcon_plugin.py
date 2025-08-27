import inspect
import re
from functools import partial
from typing import Any, Callable, Dict, List, Mapping, Optional

try:
    # some platforms may ban `tempfile`, e.g. Google App Engine
    # this is similar to what `werkzeug` did in `werkzeug.formparser`
    from tempfile import SpooledTemporaryFile

    CachedFile = partial(SpooledTemporaryFile, max_size=1024 * 1024)
except ImportError:
    from io import BytesIO as CachedFile  # type: ignore[assignment]

from falcon import MEDIA_JSON, http_status_to_code
from falcon import Request as FalconRequest
from falcon import Response as FalconResponse
from falcon.asgi import Request as FalconASGIRequest
from falcon.routing.compiled import _FIELD_PATTERN as FALCON_FIELD_PATTERN

from spectree._pydantic import (
    InternalValidationError,
    SerializedPydanticResponse,
    ValidationError,
    is_partial_base_model_instance,
    serialize_model_instance,
)
from spectree._types import ModelType
from spectree.plugins.base import BasePlugin, validate_response
from spectree.response import Response
from spectree.utils import cached_type_hints


class StreamWrapper:
    def __init__(self, stream):
        self._buf = CachedFile()
        self._buf.write(stream)
        self._buf.seek(0)

    def read(self, size: Optional[int] = -1, /) -> bytes:
        return self._buf.read(size)

    def exhaust(self) -> None:
        self._buf.seek(0)
        self._buf.truncate(0)


class AsyncStreamWrapper(StreamWrapper):
    async def read(self, size: Optional[int] = -1, /) -> bytes:  # type: ignore[override]
        return super().read(size)

    async def exhaust(self) -> None:  # type: ignore[override]
        super().exhaust()


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
        app.add_route(
            self.config.spec_url, self.OPEN_API_ROUTE_CLASS(self.spectree.spec)
        )
        for ui in self.config.page_templates:
            app.add_route(
                f"/{self.config.path}/{ui}",
                self.DOC_PAGE_ROUTE_CLASS(
                    self.config.page_templates[ui],
                    spec_url=self.config.filename,
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

        for route in self.spectree.app._router._roots:
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
                    for i, match in enumerate(self.INT_ARGS.finditer(argstr)):
                        name, value = match.group("name"), match.group("value")
                        index = i
                        if name:
                            index = self.INT_ARGS_NAMES.index(name)
                        arg_values[index] = value

                    num_digits, minimum, maximum = arg_values
                    schema = {
                        "type": "integer",
                        "format": f"int{num_digits}" if num_digits else "int32",
                    }
                    if minimum:
                        schema["minimum"] = minimum
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

        return f"/{'/'.join(subs)}", parameters

    def validate_request(self, req: FalconRequest, query, json, form, headers, cookies):
        if query:
            req.context.query = query.parse_obj(req.params)
        if headers:
            req.context.headers = headers.parse_obj(req.headers)
        if cookies:
            req.context.cookies = cookies.parse_obj(req.cookies)
        if json:
            req.context.json = json.parse_obj(req.get_media())
        if form and req.content_type:
            req_form = {}
            if req.content_type == "application/x-www-form-urlencoded":
                req_form = req.get_media()
            elif req.content_type.startswith("multipart/form-data"):
                for part in req.get_media():
                    if part.filename is None:
                        req_form[part.name] = part.get_data()
                    else:
                        # pass the `falcon.BodyPart` if it's attached as a file
                        req_form[part.name] = part
                        # try to consume the file data, otherwise it will be lost
                        # this is hacky since it changed the underlying stream type
                        part.stream = StreamWrapper(part.stream.read())
            req.context.form = form.parse_obj(req_form)

    def validate_response(
        self,
        resp: FalconResponse,
        resp_model: Optional[Response],
        skip_validation: bool,
    ) -> Optional[ValueError]:
        resp_validation_error = None
        if not self._data_set_manually(resp):
            if not skip_validation and resp_model:
                try:
                    status = http_status_to_code(resp.status)
                    response_validation_result = validate_response(
                        validation_model=resp_model.find_model(status)
                        if resp_model
                        else None,
                        response_payload=resp.media,
                    )
                except (InternalValidationError, ValidationError) as err:
                    resp_validation_error = err
                    resp.status = HTTP_500
                    resp.media = (
                        err.errors()
                        if isinstance(err, InternalValidationError)
                        else err.errors(include_context=False)
                    )
                else:
                    # mark the data from SerializedPydanticResponse as JSON
                    if isinstance(
                        response_validation_result.payload, SerializedPydanticResponse
                    ):
                        resp.data = response_validation_result.payload.data
                        resp.content_type = MEDIA_JSON
                    else:
                        resp.media = response_validation_result.payload
            elif is_partial_base_model_instance(resp.media):
                resp.data = serialize_model_instance(resp.media).data
                resp.content_type = MEDIA_JSON

        return resp_validation_error

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
        req_validation_error = None
        if not skip_validation:
            try:
                self.validate_request(_req, query, json, form, headers, cookies)

            except (InternalValidationError, ValidationError) as err:
                req_validation_error = err
                _resp.status = f"{validation_error_status} Validation Error"
                _resp.media = (
                    err.json()
                    if isinstance(err, InternalValidationError)
                    else err.json(include_context=False)
                )

        before(_req, _resp, req_validation_error, _self)
        if req_validation_error:
            return None

        if self.config.annotations:
            annotations = cached_type_hints(func)
            for name in ("query", "json", "form", "headers", "cookies"):
                if annotations.get(name):
                    kwargs[name] = getattr(_req.context, name, None)

        result = func(*args, **kwargs)

        resp_validation_error = self.validate_response(_resp, resp, skip_validation)
        after(_req, _resp, resp_validation_error, _self)
        # `falcon` doesn't use this return value. However, some users may have
        # their own processing logics that depend on this return value.
        return result

    @staticmethod
    def _data_set_manually(resp):
        return (resp.text is not None or resp.data is not None) and resp.media is None

    def bypass(self, func, method):
        if isinstance(func, partial):
            return True
        return inspect.isfunction(func)


class FalconAsgiPlugin(FalconPlugin):
    """Light wrapper around default Falcon plug-in to support Falcon 3.0 ASGI apps"""

    ASYNC = True
    OPEN_API_ROUTE_CLASS = OpenAPIAsgi
    DOC_PAGE_ROUTE_CLASS = DocPageAsgi

    async def validate_async_request(
        self, req: FalconASGIRequest, query, json, form, headers, cookies
    ):
        if query:
            req.context.query = query.parse_obj(req.params)
        if headers:
            req.context.headers = headers.parse_obj(req.headers)
        if cookies:
            req.context.cookies = cookies.parse_obj(req.cookies)
        if json:
            media = await req.get_media()
            req.context.json = json.parse_obj(media)
        if form and req.content_type:
            req_form = {}
            if req.content_type == "application/x-www-form-urlencoded":
                req_form = await req.get_media()
            elif req.content_type.startswith("multipart/form-data"):
                async for part in await req.get_media():
                    if part.filename is None:
                        req_form[part.name] = await part.get_data()
                    else:
                        # pass the `falcon.BodyPart` if it's attached as a file
                        req_form[part.name] = part
                        # try to consume the file data, otherwise it will be lost
                        part.stream = AsyncStreamWrapper(await part.stream.read())
            req.context.form = form.parse_obj(req_form)

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
        req_validation_error = None
        if not skip_validation:
            try:
                await self.validate_async_request(
                    _req, query, json, form, headers, cookies
                )

            except (InternalValidationError, ValidationError) as err:
                req_validation_error = err
                _resp.status = f"{validation_error_status} Validation Error"
                _resp.media = (
                    err.json()
                    if isinstance(err, InternalValidationError)
                    else err.json(include_context=False)
                )

        before(_req, _resp, req_validation_error, _self)
        if req_validation_error:
            return None

        if self.config.annotations:
            annotations = cached_type_hints(func)
            for name in ("query", "json", "form", "headers", "cookies"):
                if annotations.get(name):
                    kwargs[name] = getattr(_req.context, name, None)

        result = (
            await func(*args, **kwargs)
            if inspect.iscoroutinefunction(func)
            else func(*args, **kwargs)
        )

        resp_validation_error = self.validate_response(_resp, resp, skip_validation)
        after(_req, _resp, resp_validation_error, _self)
        return result
