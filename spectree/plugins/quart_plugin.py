import inspect
from typing import Any, Callable, Mapping, Optional, Tuple, get_type_hints

from pydantic import BaseModel, ValidationError
from quart import Blueprint, abort, current_app, jsonify, make_response, request
from werkzeug.routing import parse_converter_args

from .._types import ModelType
from ..response import Response
from ..utils import get_multidict_items, werkzeug_parse_rule
from .base import BasePlugin, Context


class QuartPlugin(BasePlugin):
    blueprint_state = None
    FORM_MIMETYPE = ("application/x-www-form-urlencoded", "multipart/form-data")
    ASYNC = True

    def find_routes(self):
        for rule in current_app.url_map.iter_rules():
            if any(
                str(rule).startswith(path)
                for path in (f"/{self.config.path}", "/static")
            ):
                continue
            if rule.endpoint.startswith("openapi"):
                continue
            if (
                self.blueprint_state
                and self.blueprint_state.url_prefix
                and (
                    not str(rule).startswith(self.blueprint_state.url_prefix)
                    or str(rule).startswith(
                        "/".join([self.blueprint_state.url_prefix, self.config.path])
                    )
                )
            ):
                continue
            yield rule

    def bypass(self, func, method):
        return method in ["HEAD", "OPTIONS"]

    def parse_func(self, route: Any):
        if self.blueprint_state:
            func = self.blueprint_state.app.view_functions[route.endpoint]
        else:
            func = current_app.view_functions[route.endpoint]

        # view class: https://flask.palletsprojects.com/en/1.1.x/views/
        if getattr(func, "view_class", None):
            cls = getattr(func, "view_class")
            for method in route.methods:
                view = getattr(cls, method.lower(), None)
                if view:
                    yield method, view
        else:
            for method in route.methods:
                yield method, func

    def parse_path(
        self,
        route: Optional[Mapping[str, str]],
        path_parameter_descriptions: Optional[Mapping[str, str]],
    ) -> Tuple[str, list]:
        subs = []
        parameters = []

        for converter, arguments, variable in werkzeug_parse_rule(str(route)):
            if converter is None:
                subs.append(variable)
                continue
            subs.append(f"{{{variable}}}")

            args: tuple = ()
            kwargs: dict = {}

            if arguments:
                args, kwargs = parse_converter_args(arguments)

            schema = None
            if converter == "any":
                schema = {
                    "type": "string",
                    "enum": args,
                }
            elif converter == "int":
                schema = {
                    "type": "integer",
                    "format": "int32",
                }
                if "max" in kwargs:
                    schema["maximum"] = kwargs["max"]
                if "min" in kwargs:
                    schema["minimum"] = kwargs["min"]
            elif converter == "float":
                schema = {
                    "type": "number",
                    "format": "float",
                }
            elif converter == "uuid":
                schema = {
                    "type": "string",
                    "format": "uuid",
                }
            elif converter == "path":
                schema = {
                    "type": "string",
                    "format": "path",
                }
            elif converter == "string":
                schema = {
                    "type": "string",
                }
                for prop in ["length", "maxLength", "minLength"]:
                    if prop in kwargs:
                        schema[prop] = kwargs[prop]
            elif converter == "default":
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

        return "".join(subs), parameters

    async def request_validation(self, request, query, json, form, headers, cookies):
        """
        req_query: werkzeug.datastructures.ImmutableMultiDict
        req_json: dict
        req_headers: werkzeug.datastructures.EnvironHeaders
        req_cookies: werkzeug.datastructures.ImmutableMultiDict
        """
        req_query = get_multidict_items(request.args)
        req_headers = dict(iter(request.headers)) or {}
        req_cookies = get_multidict_items(request.cookies) or {}
        has_data = request.method not in ("GET", "DELETE")
        use_json = json and has_data and request.mimetype == "application/json"
        use_form = (
            form
            and has_data
            and any([x in request.mimetype for x in self.FORM_MIMETYPE])
        )

        request.context = Context(
            query.parse_obj(req_query) if query else None,
            json.parse_obj(await request.get_json(silent=True) or {})
            if use_json
            else None,
            form.parse_obj(self._fill_form(request)) if use_form else None,
            headers.parse_obj(req_headers) if headers else None,
            cookies.parse_obj(req_cookies) if cookies else None,
        )

    def _fill_form(self, request) -> dict:
        req_data = get_multidict_items(request.form)
        req_data.update(get_multidict_items(request.files) if request.files else {})
        return req_data

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
        response, req_validation_error, resp_validation_error = None, None, None
        try:
            await self.request_validation(request, query, json, form, headers, cookies)
            if self.config.annotations:
                annotations = get_type_hints(func)
                for name in ("query", "json", "form", "headers", "cookies"):
                    if annotations.get(name):
                        kwargs[name] = getattr(request.context, name)
        except ValidationError as err:
            req_validation_error = err
            response = await make_response(
                jsonify(err.errors()), validation_error_status
            )

        before(request, response, req_validation_error, None)
        if req_validation_error:
            after(request, response, req_validation_error, None)
            assert response  # make mypy happy
            abort(response)  # type: ignore

        result = (
            await func(*args, **kwargs)
            if inspect.iscoroutinefunction(func)
            else func(*args, **kwargs)
        )

        status = 200
        rest = []
        if resp and isinstance(result, tuple) and isinstance(result[0], BaseModel):
            if len(result) > 1:
                model, status, *rest = result
            else:
                model = result[0]
        else:
            model = result

        if resp:
            expect_model = resp.find_model(status)
            if expect_model and isinstance(model, expect_model):
                skip_validation = True
                result = (model.dict(), status, *rest)

        response = await make_response(result)

        if resp and resp.has_model():

            model = resp.find_model(response.status_code)
            if model and not skip_validation:
                try:
                    model.parse_obj(await response.get_json())  # type: ignore
                except ValidationError as err:
                    resp_validation_error = err
                    response = await make_response(
                        jsonify({"message": "response validation error"}), 500
                    )

        after(request, response, resp_validation_error, None)

        return response

    def register_route(self, app):
        app.add_url_rule(
            self.config.spec_url,
            endpoint=f"openapi_{self.config.path}",
            view_func=lambda: jsonify(self.spectree.spec),
        )

        if isinstance(app, Blueprint):

            def gen_doc_page(ui):
                spec_url = self.config.spec_url
                if self.blueprint_state.url_prefix is not None:
                    spec_url = "/".join(
                        (
                            self.blueprint_state.url_prefix.rstrip("/"),
                            self.config.spec_url.lstrip("/"),
                        )
                    )

                return self.config.page_templates[ui].format(
                    spec_url=spec_url,
                    spec_path=self.config.path,
                    **self.config.swagger_oauth2_config(),
                )

            for ui in self.config.page_templates:
                app.add_url_rule(
                    f"/{self.config.path}/{ui}/",
                    endpoint=f"openapi_{self.config.path}_{ui.replace('.', '_')}",
                    view_func=lambda ui=ui: gen_doc_page(ui),
                )

            app.record(lambda state: setattr(self, "blueprint_state", state))
        else:
            for ui in self.config.page_templates:
                app.add_url_rule(
                    f"/{self.config.path}/{ui}/",
                    endpoint=f"openapi_{self.config.path}_{ui}",
                    view_func=lambda ui=ui: self.config.page_templates[ui].format(
                        spec_url=self.config.spec_url,
                        spec_path=self.config.path,
                        **self.config.swagger_oauth2_config(),
                    ),
                )
