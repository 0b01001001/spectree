from typing import Any, Callable, Optional

import flask
from flask import Blueprint, abort, current_app, jsonify, make_response, request

from spectree._pydantic import (
    InternalValidationError,
    ValidationError,
)
from spectree._types import ModelType
from spectree.plugins.base import Context
from spectree.plugins.werkzeug_utils import WerkzeugPlugin
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
            query.parse_obj(req_query) if query else None,
            json.parse_obj(request.get_json(silent=True) or {}) if use_json else None,
            form.parse_obj(self.fill_form(request)) if use_form else None,
            headers.parse_obj(req_headers) if headers else None,
            cookies.parse_obj(req_cookies) if cookies else None,
        )

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
            except (InternalValidationError, ValidationError) as err:
                req_validation_error = err
                errors = (
                    err.json()
                    if isinstance(err, InternalValidationError)
                    else err.json(include_context=False)
                )
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
