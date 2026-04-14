import inspect
from typing import Any, Callable, Optional

import quart
from quart import Blueprint, abort, current_app, jsonify, make_response, request

from spectree.model_adapter import ModelClass
from spectree.plugins.base import Context, validate_response
from spectree.plugins.werkzeug_utils import WerkzeugPlugin, flask_response_unpack
from spectree.response import Response
from spectree.utils import cached_type_hints, get_multidict_items


class QuartPlugin(WerkzeugPlugin):
    FORM_MIMETYPE = ("application/x-www-form-urlencoded", "multipart/form-data")
    ASYNC = True

    def get_current_app(self):
        return current_app

    def is_app_response(self, resp):
        return isinstance(resp, quart.Response)

    @staticmethod
    def is_blueprint(app: Any) -> bool:
        return isinstance(app, Blueprint)

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
            self.model_adapter.validate_obj(query, req_query) if query else None,
            self.model_adapter.validate_obj(
                json, await request.get_json(silent=True) or {}
            )
            if use_json
            else None,
            self.model_adapter.validate_obj(form, self.fill_form(request))
            if use_form
            else None,
            self.model_adapter.validate_obj(headers, req_headers) if headers else None,
            self.model_adapter.validate_obj(cookies, req_cookies) if cookies else None,
        )

    async def validate_response(
        self,
        resp,
        resp_model: Optional[Response],
        skip_validation: bool,
        force_resp_serialize: bool,
    ):
        resp_validation_error = None
        payload, status, additional_headers = flask_response_unpack(resp)

        if self.is_app_response(payload):
            resp_status, resp_headers = payload.status_code, payload.headers
            payload = await payload.get_data()
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
                    model_adapter=self.model_adapter,
                    validation_model=resp_model.find_model(status),
                    response_payload=payload,
                    force_serialize=force_resp_serialize,
                )
            except self.model_adapter.validation_error as err:
                errors = self.model_adapter.validation_errors(err)
                response = await make_response(errors, 500)
                resp_validation_error = err
            else:
                response = await make_response(
                    self.get_current_app().response_class(
                        response_validation_result.payload,
                        mimetype="application/json",
                    )
                    if isinstance(response_validation_result.payload, bytes)
                    else response_validation_result.payload,
                    status,
                    additional_headers,
                )
        else:
            if self.model_adapter.is_partial_model_instance(payload):
                payload = self.get_current_app().response_class(
                    self.model_adapter.dump_json(payload),
                    mimetype="application/json",
                )
            response = await make_response(payload, status, additional_headers)

        return response, resp_validation_error

    async def validate(
        self,
        func: Callable,
        query: Optional[ModelClass],
        json: Optional[ModelClass],
        form: Optional[ModelClass],
        headers: Optional[ModelClass],
        cookies: Optional[ModelClass],
        resp: Optional[Response],
        before: Callable,
        after: Callable,
        validation_error_status: int,
        skip_validation: bool,
        force_resp_serialize: bool,
        *args: Any,
        **kwargs: Any,
    ):
        response, req_validation_error, resp_validation_error = None, None, None
        if not skip_validation:
            try:
                await self.request_validation(
                    request, query, json, form, headers, cookies
                )
            except self.model_adapter.validation_error as err:
                req_validation_error = err
                errors = self.model_adapter.validation_errors(err)
                response = await make_response(jsonify(errors), validation_error_status)

        before(request, response, req_validation_error, None)
        if req_validation_error:
            assert response  # make mypy happy
            abort(response)  # type: ignore

        if self.config.annotations:
            annotations = cached_type_hints(func)
            for name in ("query", "json", "form", "headers", "cookies"):
                if annotations.get(name):
                    kwargs[name] = getattr(
                        getattr(request, "context", None), name, None
                    )

        result = (
            await func(*args, **kwargs)
            if inspect.iscoroutinefunction(func)
            else func(*args, **kwargs)
        )

        response, resp_validation_error = await self.validate_response(
            result,
            resp,
            skip_validation,
            force_resp_serialize,
        )
        after(request, response, resp_validation_error, None)

        return response
