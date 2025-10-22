from typing import Any, Callable, Optional

import flask
from flask import Blueprint, abort, current_app, jsonify, make_response, request
from pydantic import ValidationError

from spectree._pydantic import (
    SerializedPydanticResponse,
    is_partial_base_model_instance,
    serialize_model_instance,
)
from spectree._types import ModelType
from spectree.plugins.base import Context, validate_response
from spectree.plugins.werkzeug_utils import WerkzeugPlugin, flask_response_unpack
from spectree.response import Response
from spectree.utils import cached_type_hints, get_multidict_items


class FlaskPlugin(WerkzeugPlugin):
    def get_current_app(self):
        return current_app

    def is_app_response(self, resp):
        return isinstance(resp, flask.Response)

    @staticmethod
    def is_blueprint(app: Any) -> bool:
        return isinstance(app, Blueprint)

    def request_validation(self, request, query, json, form, headers, cookies):
        """
        req_query: werkzeug.datastructures.ImmutableMultiDict
        req_json: dict
        req_headers: werkzeug.datastructures.EnvironHeaders
        req_cookies: werkzeug.datastructures.ImmutableMultiDict
        """
        req_query = get_multidict_items(request.args, query)
        req_headers = dict(iter(request.headers)) or {}
        req_cookies = get_multidict_items(request.cookies)
        has_data = request.method not in ("GET", "DELETE")
        # flask Request.mimetype is already normalized
        use_json = json and has_data and request.mimetype not in self.FORM_MIMETYPE
        use_form = form and has_data and request.mimetype in self.FORM_MIMETYPE

        request.context = Context(
            query.model_validate(req_query) if query else None,
            json.model_validate(request.get_json(silent=True) or {})
            if use_json
            else None,
            form.model_validate(self.fill_form(request)) if use_form else None,
            headers.model_validate(req_headers) if headers else None,
            cookies.model_validate(req_cookies) if cookies else None,
        )

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
            except ValidationError as err:
                errors = err.errors(include_context=False)
                response = make_response(errors, 500)
                resp_validation_error = err
            else:
                response = make_response(
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
        else:
            if is_partial_base_model_instance(payload):
                payload = self.get_current_app().response_class(
                    serialize_model_instance(payload).data,
                    mimetype="application/json",
                )
            response = make_response(payload, status, additional_headers)

        return response, resp_validation_error

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
        response, req_validation_error = None, None
        if not skip_validation:
            try:
                self.request_validation(request, query, json, form, headers, cookies)
            except ValidationError as err:
                req_validation_error = err
                errors = err.errors(include_context=False)
                response = make_response(jsonify(errors), validation_error_status)

        before(request, response, req_validation_error, None)

        if req_validation_error is not None:
            assert response  # make mypy happy
            abort(response)

        if self.config.annotations:
            annotations = cached_type_hints(func)
            for name in ("query", "json", "form", "headers", "cookies"):
                if annotations.get(name):
                    kwargs[name] = getattr(
                        getattr(request, "context", None), name, None
                    )

        result = func(*args, **kwargs)

        response, resp_validation_error = self.validate_response(
            result, resp, skip_validation
        )
        after(request, response, resp_validation_error, None)

        return response
