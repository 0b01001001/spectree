import re
from typing import Any, Iterator, List, Mapping, Optional, Tuple, Union

from werkzeug.datastructures import Headers
from werkzeug.routing import parse_converter_args

from spectree._pydantic import (
    InternalValidationError,
    SerializedPydanticResponse,
    ValidationError,
    is_partial_base_model_instance,
    serialize_model_instance,
)
from spectree.plugins.base import BasePlugin, validate_response
from spectree.response import Response
from spectree.utils import get_multidict_items

RE_FLASK_RULE = re.compile(
    r"""
    (?P<static>[^<]*)                           # static rule data
    <
    (?:
        (?P<converter>[a-zA-Z_][a-zA-Z0-9_]*)   # converter name
        (?:\((?P<args>.*?)\))?                  # converter arguments
        \:                                      # variable delimiter
    )?
    (?P<variable>[a-zA-Z_][a-zA-Z0-9_]*)        # variable name
    >
    """,
    re.VERBOSE,
)


def werkzeug_parse_rule(
    rule: str,
) -> Iterator[Tuple[Optional[str], Optional[str], str]]:
    """A copy of werkzeug.parse_rule which is now removed.

    Parse a rule and return it as generator. Each iteration yields tuples
    in the form ``(converter, arguments, variable)``. If the converter is
    `None` it's a static url part, otherwise it's a dynamic one.
    """
    pos = 0
    end = len(rule)
    do_match = RE_FLASK_RULE.match
    used_names = set()
    while pos < end:
        m = do_match(rule, pos)
        if m is None:
            break
        data = m.groupdict()
        if data["static"]:
            yield None, None, data["static"]
        variable = data["variable"]
        converter = data["converter"] or "default"
        if variable in used_names:
            raise ValueError(f"variable name {variable!r} used twice.")
        used_names.add(variable)
        yield converter, data["args"] or None, variable
        pos = m.end()
    if pos < end:
        remaining = rule[pos:]
        if ">" in remaining or "<" in remaining:
            raise ValueError(f"malformed url rule: {rule!r}")
        yield None, None, remaining


def flask_response_unpack(
    resp: Any,
) -> Tuple[Any, int, Union[List[Tuple[str, str]], Headers]]:
    """Parse Flask response object into a tuple of (payload, status_code, headers)."""
    status = 200
    headers: List[Tuple[str, str]] = []
    payload = None
    if not isinstance(resp, tuple):
        return resp, status, headers
    if len(resp) == 1:
        payload = resp[0]
    elif len(resp) == 2:
        payload = resp[0]
        if isinstance(resp[1], int):
            status = resp[1]
        else:
            headers = resp[1]
    elif len(resp) == 3:
        payload, status, headers = resp
    else:
        raise ValueError(
            f"Invalid return tuple: {resp}, expect (body,), (body, status), "
            "(body, headers), or (body, status, headers)."
        )
    return payload, status, headers


class WerkzeugPlugin(BasePlugin):
    blueprint_state = None

    def get_current_app(self):
        raise NotImplementedError()

    def is_app_response(self, resp) -> bool:
        raise NotImplementedError()

    def make_response_with_addition(self, *args):
        """This method is derived from Flask's `make_response` method."""
        current_app = self.get_current_app()
        if len(args) == 1:
            args = args[0]
        return current_app.make_response(args)

    @staticmethod
    def is_blueprint(app) -> bool:
        raise NotImplementedError()

    def find_routes(self):
        # https://werkzeug.palletsprojects.com/en/stable/routing/#werkzeug.routing.Rule
        for rule in self.get_current_app().url_map.iter_rules():
            if any(
                str(rule).startswith(path)
                for path in (f"/{self.config.path}", "/static")
            ):
                continue
            if rule.endpoint.startswith("openapi"):
                continue
            if getattr(rule, "websocket", False):
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
            func = self.get_current_app().view_functions[route.endpoint]

        # view class: https://flask.palletsprojects.com/en/1.1.x/views/
        view_cls = getattr(func, "view_class", None)
        if view_cls:
            for method in route.methods:
                view = getattr(view_cls, method.lower(), None)
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

    def fill_form(self, request) -> dict:
        req_data = get_multidict_items(request.form)
        req_data.update(get_multidict_items(request.files) if request.files else {})
        return req_data

    def validate_response(
        self,
        resp,
        resp_model: Optional[Response],
        skip_validation: bool,
    ):
        resp_validation_error = None
        payload, status, additional_headers = flask_response_unpack(resp)

        if self.is_app_response(payload):
            resp_status, resp_headers = payload.status_code, payload.headers
            payload = payload.get_data()
            # the inner flask.Response.status_code only takes effect when there is
            # no other status code
            if status == 200:
                status = resp_status
            # use the `Header` object to avoid deduplicated by `make_response`
            resp_headers.extend(additional_headers)
            additional_headers = resp_headers

        if not skip_validation and resp_model:
            try:
                response_validation_result = validate_response(
                    validation_model=resp_model.find_model(status),
                    response_payload=payload,
                )
            except (InternalValidationError, ValidationError) as err:
                errors = (
                    err.errors()
                    if isinstance(err, InternalValidationError)
                    else err.errors(include_context=False)
                )
                response = self.make_response_with_addition(errors, 500)
                resp_validation_error = err
            else:
                response = self.make_response_with_addition(
                    (
                        self.get_current_app().response_class(
                            response_validation_result.payload.data,
                            mimetype="application/json",
                        )
                        if isinstance(
                            response_validation_result.payload,
                            SerializedPydanticResponse,
                        )
                        else response_validation_result.payload,
                        status,
                        additional_headers,
                    )
                )
        else:
            if is_partial_base_model_instance(payload):
                payload = self.get_current_app().response_class(
                    serialize_model_instance(payload).data,
                    mimetype="application/json",
                )
            response = self.make_response_with_addition(
                payload, status, additional_headers
            )

        return response, resp_validation_error

    def register_route(self, app):
        app.add_url_rule(
            rule=self.config.spec_url,
            endpoint=f"openapi_{self.config.path}",
            view_func=lambda: self.get_current_app().json.response(self.spectree.spec),
        )

        if self.is_blueprint(app):

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
