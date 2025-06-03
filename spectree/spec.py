import warnings
from collections import defaultdict
from copy import deepcopy
from functools import wraps
from importlib import import_module
from typing import (
    Any,
    Callable,
    Dict,
    Mapping,
    Optional,
    Sequence,
    Type,
    get_type_hints,
)

from ._types import FunctionDecorator, ModelType, NamingStrategy, NestedNamingStrategy
from .config import Configuration, ModeEnum
from .models import Tag, ValidationError
from .plugins import PLUGINS, BasePlugin
from .response import Response
from .utils import (
    default_after_handler,
    default_before_handler,
    get_model_key,
    get_model_schema,
    get_nested_key,
    get_security,
    parse_comments,
    parse_name,
    parse_params,
    parse_request,
    parse_resp,
)


class SpecTree:
    """
    Interface

    :param str backend_name: choose from
        ('flask', 'quart', 'falcon', 'falcon-asgi', 'starlette')
    :param backend: a backend that inherit `SpecTree.plugins.base.BasePlugin`, this will
        override the `backend_name` if provided
    :param app: backend framework application instance (can be registered later)
    :param before: a callback function of the form
        :meth:`spectree.utils.default_before_handler`
        ``func(req, resp, req_validation_error, instance)``
        that will be called after the request validation before the endpoint function
    :param after: a callback function of the form
        :meth:`spectree.utils.default_after_handler`
        ``func(req, resp, resp_validation_error, instance)``
        that will be called after the response validation
    :param validation_error_status: The default response status code to use in the
        event of a validation error. This value can be overridden for specific endpoints
        if needed.
    :param kwargs: init :class:`spectree.config.Configuration`, they can also be
        configured through the environment variables with prefix `spectree_`
    """

    def __init__(
        self,
        backend_name: str = "base",
        backend: Optional[Type[BasePlugin]] = None,
        app: Any = None,
        before: Callable = default_before_handler,
        after: Callable = default_after_handler,
        validation_error_status: int = 422,
        validation_error_model: Optional[ModelType] = None,
        naming_strategy: NamingStrategy = get_model_key,
        nested_naming_strategy: NestedNamingStrategy = get_nested_key,
        **kwargs: Any,
    ):
        self.naming_strategy = naming_strategy
        self.nested_naming_strategy = nested_naming_strategy
        self.before = before
        self.after = after
        self.validation_error_status = validation_error_status
        self.validation_error_model = validation_error_model or ValidationError
        self.config: Configuration = Configuration.parse_obj(kwargs)
        self.backend_name = backend_name
        if backend:
            self.backend = backend(self)
        else:
            plugin = PLUGINS[backend_name]
            module = import_module(plugin.name, plugin.package)
            self.backend = getattr(module, plugin.class_name)(self)
        self.models: Dict[str, Any] = {}
        if app:
            self.register(app)

    def register(self, app: Any):
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

    def bypass(self, func: Callable):
        """
        bypass rules for routes (mode defined in config)

        :normal:    collect all the routes exclude those decorated by other
                    `SpecTree` instance
        :greedy:    collect all the routes
        :strict:    collect all the routes decorated by this instance
        """
        if self.config.mode == ModeEnum.greedy:
            return False
        elif self.config.mode == ModeEnum.strict:
            return getattr(func, "_decorator", None) != self
        else:
            decorator = getattr(func, "_decorator", None)
            return bool(decorator and decorator != self)

    def validate(  # noqa: PLR0913  [too-many-arguments]
        self,
        query: Optional[ModelType] = None,
        json: Optional[ModelType] = None,
        form: Optional[ModelType] = None,
        headers: Optional[ModelType] = None,
        cookies: Optional[ModelType] = None,
        resp: Optional[Response] = None,
        tags: Sequence = (),
        security: Any = None,
        deprecated: bool = False,
        before: Optional[Callable] = None,
        after: Optional[Callable] = None,
        validation_error_status: int = 0,
        path_parameter_descriptions: Optional[Mapping[str, str]] = None,
        skip_validation: bool = False,
        operation_id: Optional[str] = None,
    ) -> Callable:
        """
        - validate query, json, headers in request
        - validate response body and status code
        - add tags to this API route
        - add security to this API route

        :param query: `pydantic.BaseModel`, query in uri like `?name=value`
        :param json: `pydantic.BaseModel`, JSON format request body
        :param form: `pydantic.BaseModel`, form-data request body
        :param headers: `pydantic.BaseModel`, if you have specific headers
        :param cookies: `pydantic.BaseModel`, if you have cookies for this route
        :param resp: `spectree.Response`
        :param tags: a tuple of strings or :class:`spectree.models.Tag`
        :param security: dict with security config for current route and method
        :param deprecated: bool, if endpoint is marked as deprecated
        :param before: :meth:`spectree.utils.default_before_handler` for
            specific endpoint
        :param after: :meth:`spectree.utils.default_after_handler` for
            specific endpoint
        :param validation_error_status: The response status code to use for the
            specific endpoint, in the event of a validation error. If not specified,
            the global `validation_error_status` is used instead, defined
            in :meth:`spectree.spec.SpecTree`.
        :param path_parameter_descriptions: A dictionary of path parameter names and
            their description.
        :param skip_validation: If set to `True`, the endpoint will skip
            request / response validations.
        :param operation_id: a string override for operationId for the given endpoint
        """
        # If the status code for validation errors is not overridden on the level of
        # the view function, use the globally set status code for validation errors.
        if validation_error_status == 0:
            validation_error_status = self.validation_error_status

        if self.config.annotations and skip_validation:
            warnings.warn(
                "`skip_validation` cannot be used with `annotations` enabled. The instances"
                " of `json`, `headers`, `cookies`, etc. read from function will be `None`.",
                UserWarning,
                stacklevel=2,
            )

        def decorate_validation(func: Callable):
            # for sync framework
            @wraps(func)
            def sync_validate(*args: Any, **kwargs: Any):
                return self.backend.validate(
                    func,
                    query,
                    json,
                    form,
                    headers,
                    cookies,
                    resp,
                    before or self.before,
                    after or self.after,
                    validation_error_status,
                    skip_validation,
                    *args,
                    **kwargs,
                )

            # for async framework
            @wraps(func)
            async def async_validate(*args: Any, **kwargs: Any):
                return await self.backend.validate(
                    func,
                    query,
                    json,
                    form,
                    headers,
                    cookies,
                    resp,
                    before or self.before,
                    after or self.after,
                    validation_error_status,
                    skip_validation,
                    *args,
                    **kwargs,
                )

            validation: FunctionDecorator = (
                async_validate if self.backend.ASYNC else sync_validate  # type: ignore
            )

            if self.config.annotations:
                nonlocal query, json, form, headers, cookies
                annotations = get_type_hints(func)
                query = annotations.get("query", query)
                json = annotations.get("json", json)
                form = annotations.get("form", form)
                headers = annotations.get("headers", headers)
                cookies = annotations.get("cookies", cookies)

            # register
            for name, model in zip(
                ("query", "json", "form", "headers", "cookies"),
                (query, json, form, headers, cookies),
            ):
                if model is not None:
                    model_key = self._add_model(model=model)
                    setattr(validation, name, model_key)

            if resp:
                # Make sure that the endpoint specific status code and data model for
                # validation errors shows up in the response spec.
                resp.add_model(
                    validation_error_status, self.validation_error_model, replace=False
                )
                for model in resp.models:
                    self._add_model(model=model)
                validation.resp = resp

            if tags:
                validation.tags = tags

            validation.security = security
            validation.deprecated = deprecated
            validation.path_parameter_descriptions = path_parameter_descriptions
            validation.operation_id = operation_id
            # register decorator
            validation._decorator = self
            return validation

        return decorate_validation

    def _add_model(self, model: ModelType) -> str:
        """
        unified model processing
        """

        model_key = self.naming_strategy(model)
        self.models[model_key] = deepcopy(
            get_model_schema(
                model=model,
                naming_strategy=self.naming_strategy,
                nested_naming_strategy=self.nested_naming_strategy,
            )
        )

        return model_key

    def _generate_spec(self) -> Dict[str, Any]:
        """
        generate OpenAPI spec according to routes and decorators
        """
        routes: Dict[str, Dict] = defaultdict(dict)
        tags = {}
        for route in self.backend.find_routes():
            for method, func in self.backend.parse_func(route):
                if self.backend.bypass(func, method) or self.bypass(func):
                    continue

                path_parameter_descriptions = getattr(
                    func, "path_parameter_descriptions", None
                )
                path, parameters = self.backend.parse_path(
                    route, path_parameter_descriptions
                )

                name = parse_name(func)
                summary, desc = parse_comments(func)
                func_tags = getattr(func, "tags", ())
                for tag in func_tags:
                    if str(tag) not in tags:
                        tags[str(tag)] = (
                            tag.dict(exclude_none=True)
                            if isinstance(tag, Tag)
                            else {"name": tag}
                        )

                routes[path][method.lower()] = {
                    "summary": summary or f"{name} <{method}>",
                    "operationId": self.backend.get_func_operation_id(
                        func, path, method
                    ),
                    "description": desc or "",
                    "tags": [str(x) for x in getattr(func, "tags", ())],
                    "parameters": parse_params(func, parameters[:], self.models),
                    "responses": parse_resp(func, self.naming_strategy),
                }

                security = getattr(func, "security", None)
                if security is not None:
                    routes[path][method.lower()]["security"] = get_security(security)

                deprecated = getattr(func, "deprecated", False)
                if deprecated:
                    routes[path][method.lower()]["deprecated"] = deprecated

                request_body = parse_request(func)
                if request_body:
                    routes[path][method.lower()]["requestBody"] = request_body

        spec: Dict[str, Any] = {
            "openapi": self.config.openapi_version,
            "info": self.config.openapi_info(),
            "tags": list(tags.values()),
            "paths": {**routes},
            "components": {
                "schemas": {**self.models, **self._get_model_definitions()},
            },
        }

        if self.config.servers:
            spec["servers"] = [
                server.dict(exclude_none=True) for server in self.config.servers
            ]

        if self.config.security_schemes:
            spec["components"]["securitySchemes"] = {
                scheme.name: scheme.data.dict(exclude_none=True, by_alias=True)
                for scheme in self.config.security_schemes
            }

        spec["security"] = get_security(self.config.security)
        return spec

    def _get_model_definitions(self) -> Dict[str, Any]:
        """
        handle nested models
        """
        definitions = {}
        for name, schema in self.models.items():
            # handle pydantic v1 & v2 def keys
            for def_key in ["definitions", "$defs"]:
                if def_key in schema:
                    for key, value in schema[def_key].items():
                        composed_key = self.nested_naming_strategy(name, key)
                        if composed_key not in definitions:
                            definitions[composed_key] = value
                    del schema[def_key]

        return definitions
