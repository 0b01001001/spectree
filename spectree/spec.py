import warnings
import weakref
from collections import ChainMap, defaultdict
from functools import wraps
from importlib import import_module
from typing import (
    Any,
    Callable,
    Mapping,
    Sequence,
)

from spectree._types import (
    HookHandler,
    ModelAdapterType,
    NamingStrategy,
    NestedNamingStrategy,
)
from spectree.config import Configuration, ModeEnum
from spectree.metadata import (
    FunctionDecorator,
    is_validated_function,
    iter_wrapped_functions,
    register_validated_function,
)
from spectree.model_adapter import ModelClass, get_pydantic_model_adapter
from spectree.model_adapter.protocol import SchemaMode
from spectree.models import Tag
from spectree.plugins import PLUGINS, BasePlugin
from spectree.response import Response
from spectree.schema_registry import COMPONENT_REF_PREFIX, SchemaRegistry
from spectree.utils import (
    default_after_handler,
    default_before_handler,
    get_model_key,
    get_nested_key,
    get_request_model_hints,
    get_security,
    parse_comments,
    parse_name,
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
        ``func(req, resp, req_validation_error, instance, model_adapter)``
        that will be called after the request validation before the endpoint function
    :param after: a callback function of the form
        :meth:`spectree.utils.default_after_handler`
        ``func(req, resp, resp_validation_error, instance, model_adapter)``
        that will be called after the response validation
    :param validation_error_status: The default response status code to use in the
        event of a validation error. This value can be overridden for specific endpoints
        if needed.
    :param validation_error_model: The default validation error type to be shown
        in the generated OpenAPI frontend. Make sure it's derived from the model
        adapter (including the ValidationError).
    :param naming_strategy: A callable that receives a model class and returns
        the top-level component schema name used in the OpenAPI document.
        For example, ``lambda model: model.__name__.lower()``. When a model's
        request (validation) and response (serialization) schemas differ, the
        response schema is published as ``<name>.serialization``.
    :param nested_naming_strategy: A callable that receives ``(parent, child)``
        schema names and returns the component schema name for nested models
        lifted from ``$defs``. The default includes the parent name to avoid
        collisions. To share nested models by child name, use
        ``lambda _parent, child: child``; a nested model whose response schema
        differs from its request schema is then published as
        ``<name>.serialization`` for responses.
    :param model_adapter: adapter for validation and OpenAPI JSON schema generation.
        Choose from the `spectree.model_adapter`. If not set, will use `pydantic`.
    :param kwargs: init :class:`spectree.config.Configuration`, they can also be
        configured through the environment variables with prefix `spectree_`
    """

    def __init__(
        self,
        backend_name: str = "base",
        backend: type[BasePlugin] | None = None,
        app: Any = None,
        before: HookHandler = default_before_handler,
        after: HookHandler = default_after_handler,
        validation_error_status: int = 422,
        validation_error_model: ModelClass | None = None,
        naming_strategy: NamingStrategy = get_model_key,
        nested_naming_strategy: NestedNamingStrategy = get_nested_key,
        model_adapter: ModelAdapterType | None = None,
        **kwargs: Any,
    ):
        self.naming_strategy = naming_strategy
        self.nested_naming_strategy = nested_naming_strategy
        self.validation_error_status = validation_error_status
        self.model_adapter = model_adapter or get_pydantic_model_adapter()
        self.validation_error_model = validation_error_model
        self.before = before
        self.after = after
        self.config: Configuration = Configuration.model_validate(
            kwargs,
            model_adapter=self.model_adapter,
        )
        self.backend_name = backend_name
        if backend:
            self.backend = backend(self)
        else:
            plugin = PLUGINS[backend_name]
            module = import_module(plugin.name, plugin.package)
            self.backend = getattr(module, plugin.class_name)(self)
        self._schemas = SchemaRegistry()
        self._spec: dict[str, Any] | None = None
        self._function_metadata: weakref.WeakKeyDictionary[
            Callable, FunctionDecorator
        ] = weakref.WeakKeyDictionary()
        if app:
            self.register(app)

    @property
    def models(self) -> dict[str, Any]:
        """
        the component schemas of the models registered by validated endpoints

        This is a new copy on every access: changing it does not change the
        OpenAPI document.
        """
        models, _ = self._schemas.render(self.nested_naming_strategy)
        return models

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

        The document is generated on first access and cached until another
        endpoint is decorated by this instance.
        """
        # `getattr`: deleting `_spec` was the way to force a regeneration before
        # the cache was invalidated automatically.
        if getattr(self, "_spec", None) is None:
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
        owned_by_self = self.get_function_metadata(func) is not None
        if self.config.mode == ModeEnum.strict:
            return not owned_by_self
        return not owned_by_self and is_validated_function(func)

    def get_function_metadata(self, func: Callable) -> FunctionDecorator | None:
        """Return metadata for a callable validated by this instance."""
        for candidate in iter_wrapped_functions(func):
            try:
                metadata = self._function_metadata.get(candidate)
            except TypeError:
                continue
            if metadata is not None:
                return metadata
        return None

    def validate(  # noqa: PLR0913, PLR0917
        self,
        query: ModelClass | None = None,
        json: ModelClass | None = None,
        form: ModelClass | None = None,
        headers: ModelClass | None = None,
        cookies: ModelClass | None = None,
        resp: Response | None = None,
        tags: Sequence = (),
        security: Any = None,
        deprecated: bool = False,
        before: HookHandler | None = None,
        after: HookHandler | None = None,
        validation_error_status: int = 0,
        path_parameter_descriptions: Mapping[str, str] | None = None,
        skip_validation: bool = False,
        operation_id: str | None = None,
        force_resp_serialize: bool = False,
    ) -> Callable:
        """
        - validate query, json, headers in request
        - validate response body and status code
        - add tags to this API route
        - add security to this API route

        :param query: model class for query params in the URI, like `?name=value`
        :param json: model class for a JSON request body
        :param form: model class for a form-data request body
        :param headers: model class for validating request headers
        :param cookies: model class for validating request cookies
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
        :force_resp_serialize: Always return the serialized result of the validated response.
            Requires `skip_validation` to be `False`.
        """
        # If the status code for validation errors is not overridden on the level of
        # the view function, use the globally set status code for validation errors.
        if validation_error_status == 0:
            validation_error_status = self.validation_error_status

        def decorate_validation(func: Callable):
            # Resolve the models of this function only. The arguments of
            # `validate()` are shared by every function this decorator object is
            # applied to, so they must never be reassigned here.
            query_model, json_model, form_model, headers_model, cookies_model = (
                query,
                json,
                form,
                headers,
                cookies,
            )
            if self.config.annotations:
                annotations = get_request_model_hints(func)
                if skip_validation and annotations:
                    warnings.warn(
                        "`skip_validation` cannot be used with `annotations` enabled. "
                        "The instances of `json`, `headers`, `cookies`, etc. read from "
                        "the function will be `None`.",
                        UserWarning,
                        stacklevel=2,
                    )
                query_model = annotations.get("query", query_model)
                json_model = annotations.get("json", json_model)
                form_model = annotations.get("form", form_model)
                headers_model = annotations.get("headers", headers_model)
                cookies_model = annotations.get("cookies", cookies_model)

            metadata = FunctionDecorator()

            # register
            for name, model in zip(
                ("query", "json", "form", "headers", "cookies"),
                (query_model, json_model, form_model, headers_model, cookies_model),
                strict=True,
            ):
                if model is not None:
                    model_key = self._add_model(model=model, mode="validation")
                    setattr(metadata, name, model_key)

            if resp:
                resp.bind_model_adapter(self.model_adapter)
                # Make sure that the endpoint specific status code and data model for
                # validation errors shows up in the response spec.
                resp.add_model(
                    validation_error_status,
                    self.validation_error_model or self.model_adapter.validation_error,
                    replace=False,
                )
                for model in resp.models:
                    self._add_model(model=model, mode="serialization")
                metadata.resp = resp

            # for sync framework
            @wraps(func)
            def sync_validate(*args: Any, **kwargs: Any):
                return self.backend.validate(
                    func,
                    query_model,
                    json_model,
                    form_model,
                    headers_model,
                    cookies_model,
                    resp,
                    before or self.before,
                    after or self.after,
                    validation_error_status,
                    skip_validation,
                    force_resp_serialize,
                    *args,
                    **kwargs,
                )

            # for async framework
            @wraps(func)
            async def async_validate(*args: Any, **kwargs: Any):
                return await self.backend.validate(
                    func,
                    query_model,
                    json_model,
                    form_model,
                    headers_model,
                    cookies_model,
                    resp,
                    before or self.before,
                    after or self.after,
                    validation_error_status,
                    skip_validation,
                    force_resp_serialize,
                    *args,
                    **kwargs,
                )

            validation: Callable = (
                async_validate if self.backend.ASYNC else sync_validate  # type: ignore
            )

            if tags:
                metadata.tags = tags

            metadata.security = security
            metadata.deprecated = deprecated
            metadata.path_parameter_descriptions = path_parameter_descriptions
            metadata.operation_id = operation_id
            self._function_metadata[validation] = metadata
            register_validated_function(validation)
            # A document generated earlier does not contain this endpoint.
            self._spec = None
            return validation

        return decorate_validation

    def _add_model(self, model: ModelClass, mode: SchemaMode = "validation") -> str:
        """
        unified model processing

        :param model: model class to add to the schema
        :param mode: schema generation mode - 'validation' for input models
            and 'serialization' for output models
        :returns: the component key of the model
        """
        model_key = self.naming_strategy(model)
        schema = self.model_adapter.json_schema(
            model=model,
            ref_template=f"{COMPONENT_REF_PREFIX}{{model}}",
            mode=mode,
        )
        self._schemas.register(model_key, mode, schema)
        return model_key

    def _response_component_name(self, model: Any) -> str:
        return self._schemas.component_name(
            self.naming_strategy(model), "serialization"
        )

    def _generate_spec(self) -> dict[str, Any]:
        """
        generate OpenAPI spec according to routes and decorators
        """
        routes: dict[str, dict] = defaultdict(dict)
        tags = {}
        models, definitions = self._schemas.render(self.nested_naming_strategy)
        # Parameters are built from the request models themselves, even if a
        # nested definition is published under the same name.
        parameter_models = ChainMap(models, definitions)
        for route in self.backend.find_routes():
            for method, func in self.backend.parse_func(route):
                if self.backend.bypass(func, method) or self.bypass(func):
                    continue

                metadata = self.get_function_metadata(func) or FunctionDecorator()
                path_parameter_descriptions = metadata.path_parameter_descriptions
                path, parameters = self.backend.parse_path(
                    route, path_parameter_descriptions
                )

                name = parse_name(func)
                summary, desc = parse_comments(func)
                func_tags = metadata.tags
                for tag in func_tags:
                    if str(tag) not in tags:
                        tags[str(tag)] = (
                            tag.to_dict(exclude_none=True)
                            if isinstance(tag, Tag)
                            else {"name": tag}
                        )

                routes[path][method.lower()] = {
                    "summary": summary or f"{name} <{method}>",
                    "operationId": metadata.operation_id
                    or self.backend.get_func_operation_id(func, path, method),
                    "description": desc or "",
                    "tags": [str(x) for x in metadata.tags],
                    "parameters": metadata.parse_params(
                        parameters[:], parameter_models
                    ),
                    "responses": metadata.parse_resp(self._response_component_name),
                }

                security = metadata.security
                if security is not None:
                    routes[path][method.lower()]["security"] = get_security(security)

                deprecated = metadata.deprecated
                if deprecated:
                    routes[path][method.lower()]["deprecated"] = deprecated

                request_body = metadata.parse_request()
                if request_body:
                    routes[path][method.lower()]["requestBody"] = request_body

        spec: dict[str, Any] = {
            "openapi": self.config.openapi_version,
            "info": self.config.openapi_info(),
            "tags": list(tags.values()),
            "paths": {**routes},
            "components": {"schemas": {**models, **definitions}},
        }

        if self.config.servers:
            spec["servers"] = [
                server.to_dict(exclude_none=True) for server in self.config.servers
            ]

        if self.config.security_schemes:
            spec["components"]["securitySchemes"] = {
                scheme.name: scheme.data.to_dict(exclude_none=True)
                for scheme in self.config.security_schemes
            }

        spec["security"] = get_security(self.config.security)
        return spec
