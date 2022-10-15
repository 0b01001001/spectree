from typing import Any, Callable, Optional, get_type_hints

from flask import Blueprint, abort, current_app, jsonify, make_response, request
from pydantic import BaseModel, ValidationError
from werkzeug.routing import parse_converter_args

from .._types import ModelType
from ..response import Response
from ..utils import get_multidict_items, werkzeug_parse_rule
from .base import BasePlugin, Context


class FlaskPlugin(BasePlugin):
    blueprint_state = None
    FORM_MIMETYPE = ("application/x-www-form-urlencoded", "multipart/form-data")

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

    def parse_path(self, route, path_parameter_descriptions):
        subs = []
        parameters = []

        for converter, arguments, variable in werkzeug_parse_rule(str(route)):
            if converter is None:
                subs.append(variable)
                continue
            subs.append(f"{{{variable}}}")

            args, kwargs = [], {}

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

    def request_validation(self, request, query, json, headers, cookies):
        """
        req_query: werkzeug.datastructures.ImmutableMultiDict
        req_json: dict
        req_headers: werkzeug.datastructures.EnvironHeaders
        req_cookies: werkzeug.datastructures.ImmutableMultiDict
        """
        req_query = get_multidict_items(request.args) or {}
        req_headers = dict(iter(request.headers)) or {}
        req_cookies = get_multidict_items(request.cookies) or {}
        use_json = json and request.method not in ("GET", "DELETE")

        request.context = Context(
            query.parse_obj(req_query) if query else None,
            json.parse_obj(self._fill_json(request)) if use_json else None,
            headers.parse_obj(req_headers) if headers else None,
            cookies.parse_obj(req_cookies) if cookies else None,
        )

    def _fill_json(self, request):
        if request.mimetype not in self.FORM_MIMETYPE:
            return request.get_json(silent=True) or {}

        req_json = get_multidict_items(request.form) or {}
        if request.files:
            req_json = {
                **req_json,
                **get_multidict_items(request.files),
            }
        return req_json

    def validate(
        self,
        func: Callable,
        query: Optional[ModelType],
        json: Optional[ModelType],
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
            self.request_validation(request, query, json, headers, cookies)
            if self.config.annotations:
                annotations = get_type_hints(func)
                for name in ("query", "json", "headers", "cookies"):
                    if annotations.get(name):
                        kwargs[name] = getattr(request.context, name)
        except ValidationError as err:
            req_validation_error = err
            response = make_response(jsonify(err.errors()), validation_error_status)

        before(request, response, req_validation_error, None)
        if req_validation_error:
            after(request, response, req_validation_error, None)
            assert response  # make mypy happy
            abort(response)

        result = func(*args, **kwargs)

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

        response = make_response(result)

        if resp and resp.has_model():

            model = resp.find_model(response.status_code)
            if model and not skip_validation:
                try:
                    model.parse_obj(response.get_json())
                except ValidationError as err:
                    resp_validation_error = err
                    response = make_response(
                        jsonify({"message": "response validation error"}), 500
                    )

        after(request, response, resp_validation_error, None)

        return response

    def register_route(self, app):
        app.add_url_rule(
            rule=self.config.spec_url,
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
                    rule=f"/{self.config.path}/{ui}/",
                    endpoint=f"openapi_{self.config.path}_{ui.replace('.', '_')}",
                    view_func=lambda ui=ui: gen_doc_page(ui),
                )

            app.record(lambda state: setattr(self, "blueprint_state", state))
        else:
            for ui in self.config.page_templates:
                app.add_url_rule(
                    rule=f"/{self.config.path}/{ui}/",
                    endpoint=f"openapi_{self.config.path}_{ui}",
                    view_func=lambda ui=ui: self.config.page_templates[ui].format(
                        spec_url=self.config.spec_url,
                        spec_path=self.config.path,
                        **self.config.swagger_oauth2_config(),
                    ),
                )
