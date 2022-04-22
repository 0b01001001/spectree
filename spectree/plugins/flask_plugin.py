from pydantic import BaseModel, ValidationError

from ..utils import get_multidict_items
from .base import BasePlugin, Context


class FlaskPlugin(BasePlugin):
    blueprint_state = None
    FORM_MIMETYPE = ("application/x-www-form-urlencoded", "multipart/form-data")

    def find_routes(self):
        from flask import current_app

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

    def parse_func(self, route):
        from flask import current_app

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
        from werkzeug.routing import parse_converter_args, parse_rule

        subs = []
        parameters = []

        for converter, arguments, variable in parse_rule(str(route)):
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
        if request.mimetype in self.FORM_MIMETYPE:
            req_json = get_multidict_items(request.form) or {}
            if request.files:
                req_json = {
                    **req_json,
                    **get_multidict_items(request.files),
                }
        else:
            req_json = request.get_json(silent=True) or {}
        req_headers = dict(iter(request.headers)) or {}
        req_cookies = get_multidict_items(request.cookies) or {}

        request.context = Context(
            query.parse_obj(req_query) if query else None,
            json.parse_obj(req_json) if json else None,
            headers.parse_obj(req_headers) if headers else None,
            cookies.parse_obj(req_cookies) if cookies else None,
        )

    def validate(
        self,
        func,
        query,
        json,
        headers,
        cookies,
        resp,
        before,
        after,
        validation_error_status,
        skip_validation,
        *args,
        **kwargs,
    ):
        from flask import abort, jsonify, make_response, request

        response, req_validation_error, resp_validation_error = None, None, None
        try:
            self.request_validation(request, query, json, headers, cookies)
            if self.config.annotations:
                for name in ("query", "json", "headers", "cookies"):
                    if func.__annotations__.get(name):
                        kwargs[name] = getattr(request.context, name)
        except ValidationError as err:
            req_validation_error = err
            response = make_response(jsonify(err.errors()), validation_error_status)

        before(request, response, req_validation_error, None)
        if req_validation_error:
            after(request, response, req_validation_error, None)
            abort(response)

        result = func(*args, **kwargs)

        if resp and isinstance(result, tuple) and isinstance(result[0], BaseModel):
            if len(result) > 1:
                result = result[0].dict(), *result[1:]
            else:
                result = (result[0].dict(),)

            skip_validation = True
        elif resp and isinstance(result, BaseModel):
            result = result.dict()
            skip_validation = True

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
        from flask import Blueprint, jsonify

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
                    rule=f"/{self.config.path}/{ui}",
                    endpoint=f"openapi_{self.config.path}_{ui.replace('.', '_')}",
                    view_func=lambda ui=ui: gen_doc_page(ui),
                )

            app.record(lambda state: setattr(self, "blueprint_state", state))
        else:
            for ui in self.config.page_templates:
                app.add_url_rule(
                    rule=f"/{self.config.path}/{ui}",
                    endpoint=f"openapi_{self.config.path}_{ui}",
                    view_func=lambda ui=ui: self.config.page_templates[ui].format(
                        spec_url=self.config.spec_url,
                        spec_path=self.config.path,
                        **self.config.swagger_oauth2_config(),
                    ),
                )
