from collections import defaultdict
from functools import wraps
from typing import Mapping

from pydantic import BaseModel
from inflection import camelize
from nested_lookup import nested_alter
from .config import Config
from .flask_backend import FlaskBackend
from .utils import (
    parse_comments,
    parse_request,
    parse_params,
    parse_resp,
    parse_name,
    default_before_handler,
    default_after_handler,
)


def _move_schema_reference(reference: str) -> str:
    if "/definitions" in reference:
        return f"#/components/schemas/{reference.split('/definitions/')[-1]}"
    return reference


class SpecTree:
    """
    Interface

    :param str backend_name: choose from ('flask', 'falcon', 'starlette')
    :param backend: a backend that inherit `SpecTree.plugins.base.BasePlugin`
    :param app: backend framework application instance (you can also register to it later)
    :param before: a callback function of the form :meth:`spectree.utils.default_before_handler`
        ``func(req, resp, req_validation_error, instance)``
        that will be called after the request validation before the endpoint function
    :param after: a callback function of the form :meth:`spectree.utils.default_after_handler`
        ``func(req, resp, resp_validation_error, instance)``
        that will be called after the response validation
    :param kwargs: update default :class:`spectree.config.Config`
    """

    def __init__(
        self,
        backend_name="base",
        backend=FlaskBackend,
        app=None,
        before=default_before_handler,
        after=default_after_handler,
        **kwargs,
    ):
        self.before = before
        self.after = after
        self.config = Config(**kwargs)
        self.backend_name = backend_name
        self.backend = backend(self)
        # init
        self.models = {}
        if app:
            self.register(app)

    def register(self, app):
        """
        register to backend application

        This will be automatically triggered if the app is passed into the
        init step.
        """
        self.app = app
        self.backend.register_route(self.app)

    @property
    def spec(self):
        """
        get the OpenAPI spec
        """
        if not hasattr(self, "_spec"):
            self._spec = self._generate_spec()
        return self._spec

    def bypass(self, func):
        """
        bypass rules for routes (mode defined in config)

        :normal:    collect all the routes that are not decorated by other
                    `SpecTree` instance
        :greedy:    collect all the routes
        :strict:    collect all the routes decorated by this instance
        """
        if self.config.MODE == "greedy":
            return False
        elif self.config.MODE == "strict":
            if getattr(func, "_decorator", None) == self:
                return False
            return True
        else:
            decorator = getattr(func, "_decorator", None)
            if decorator and decorator != self:
                return True
            return False

    def validate(
        self,
        query=None,
        json=None,
        headers=None,
        cookies=None,
        resp=None,
        tags=(),
        deprecated=False,
        before=None,
        after=None,
    ):
        """
        - validate query, json, headers in request
        - validate response body and status code
        - add tags to this API route

        :param query: `pydantic.BaseModel`, query in uri like `?name=value`
        :param json: `pydantic.BaseModel`, JSON format request body
        :param headers: `pydantic.BaseModel`, if you have specific headers
        :param cookies: `pydantic.BaseModel`, if you have cookies for this route
        :param resp: `spectree.Response`
        :param tags: a tuple of tags string
        :param deprecated: You can mark specific operations as deprecated to indicate that they should be transitioned out of usage
        :param before: :meth:`spectree.utils.default_before_handler` for specific endpoint
        :param after: :meth:`spectree.utils.default_after_handler` for specific endpoint
        """

        def decorate_validation(func):
            # for sync framework
            @wraps(func)
            def sync_validate(*args, **kwargs):
                return self.backend.validate(
                    func,
                    query,
                    json,
                    headers,
                    cookies,
                    resp,
                    before or self.before,
                    after or self.after,
                    *args,
                    **kwargs,
                )

            # for async framework
            @wraps(func)
            async def async_validate(*args, **kwargs):
                return await self.backend.validate(
                    func,
                    query,
                    json,
                    headers,
                    cookies,
                    resp,
                    before or self.before,
                    after or self.after,
                    *args,
                    **kwargs,
                )

            validation = (
                async_validate if self.backend_name == "starlette" else sync_validate
            )

            # register
            for name, model in zip(
                ("query", "json", "headers", "cookies"), (query, json, headers, cookies)
            ):
                if model is not None:
                    assert issubclass(model, BaseModel)
                    self.models[model.__name__] = self._get_open_api_schema(
                        model.schema()
                    )
                    setattr(validation, name, model.__name__)

            if resp:
                for model in resp.models:
                    self.models[model.__name__] = self._get_open_api_schema(
                        model.schema()
                    )
                validation.resp = resp

            if tags:
                validation.tags = tags

            if deprecated:
                validation.deprecated = True

            # register decorator
            validation._decorator = self
            return validation

        return decorate_validation

    def _generate_spec(self):
        """
        generate OpenAPI spec according to routes and decorators
        """
        tag_lookup = {tag["name"]: tag for tag in self.config.TAGS}
        routes, tags = {}, {}
        for route in self.backend.find_routes():
            path, parameters = self.backend.parse_path(route)
            routes[path] = routes.get(path, {})
            for method, func in self.backend.parse_func(route):
                if self.backend.bypass(func, method) or self.bypass(func):
                    continue

                name = parse_name(func)
                summary, desc = parse_comments(func)
                func_tags = getattr(func, "tags", ())
                for tag in func_tags:
                    if tag not in tags:
                        tags[tag] = tag_lookup.get(tag, {"name": tag})

                routes[path][method.lower()] = {
                    "summary": summary or f"{name} <{method}>",
                    "operationId": camelize(f"{name}", False),
                    "description": desc or "",
                    "tags": getattr(func, "tags", []),
                    "parameters": parse_params(func, parameters[:], self.models),
                    "responses": parse_resp(func, self.config.VALIDATION_ERROR_CODE),
                }
                if hasattr(func, "deprecated"):
                    routes[path][method.lower()]["deprecated"] = True

                request_body = parse_request(func)
                if request_body:
                    routes[path][method.lower()]["requestBody"] = request_body

        spec = {
            "openapi": self.config.OPENAPI_VERSION,
            "info": {
                **self.config.INFO,
                **{
                    "title": self.config.TITLE,
                    "version": self.config.VERSION,
                },
            },
            "tags": list(tags.values()),
            "paths": {**routes},
            "components": {"schemas": {**self._get_model_definitions()}},
        }
        return spec

    def _validate_property(self, property: Mapping) -> Mapping:
        allowed_fields = {
            "title",
            "multipleOf",
            "maximum",
            "exclusiveMaximum",
            "minimum",
            "exclusiveMinimum",
            "maxLength",
            "minLength",
            "pattern",
            "maxItems",
            "minItems",
            "uniqueItems",
            "maxProperties",
            "minProperties",
            "required",
            "enum",
            "type",
            "allOf",
            "anyOf",
            "oneOf",
            "not",
            "items",
            "properties",
            "additionalProperties",
            "description",
            "format",
            "default",
            "nullable",
            "discriminator",
            "readOnly",
            "writeOnly",
            "xml",
            "externalDocs",
            "example",
            "deprecated",
            "$ref",
        }
        result = defaultdict(dict)

        for key, value in property.items():
            for prop, val in value.items():
                if prop in allowed_fields:
                    result[key][prop] = val

        return result

    def _get_open_api_schema(self, schema: Mapping) -> Mapping:
        """
        Convert a Pydantic model into an OpenAPI compliant schema object.
        """
        result = {}
        for key, value in schema.items():
            if key == "properties":
                result[key] = self._validate_property(value)
            else:
                result[key] = value
        return result

    def _get_model_definitions(self):
        """
        handle nested models
        """
        definitions = {}
        for model, schema in self.models.items():
            if model not in definitions.keys():
                definitions[model] = schema
            if "definitions" in schema:
                for key, value in schema["definitions"].items():
                    definitions[key] = self._get_open_api_schema(value)
                del schema["definitions"]

        return nested_alter(definitions, "$ref", _move_schema_reference)
