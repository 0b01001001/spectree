from copy import deepcopy
from functools import wraps

from .config import Config
from .models import Tag
from .plugins import PLUGINS
from .utils import (
    default_after_handler,
    default_before_handler,
    get_model_key,
    get_model_schema,
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

    :param str backend_name: choose from ('flask', 'falcon', 'falcon-asgi', 'starlette')
    :param backend: a backend that inherit `SpecTree.plugins.base.BasePlugin`
    :param app: backend framework application instance (can be registered later)
    :param before: a callback function of the form
        :meth:`spectree.utils.default_before_handler`
        ``func(req, resp, req_validation_error, instance)``
        that will be called after the request validation before the endpoint function
    :param after: a callback function of the form
        :meth:`spectree.utils.default_after_handler`
        ``func(req, resp, resp_validation_error, instance)``
        that will be called after the response validation
    :param kwargs: update default :class:`spectree.config.Config`
    """

    def __init__(
        self,
        backend_name="base",
        backend=None,
        app=None,
        before=default_before_handler,
        after=default_after_handler,
        **kwargs,
    ):
        self.before = before
        self.after = after
        self.config = Config(**kwargs)
        self.backend_name = backend_name
        self.backend = backend(self) if backend else PLUGINS[backend_name](self)
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
            return getattr(func, "_decorator", None) != self
        else:
            decorator = getattr(func, "_decorator", None)
            return bool(decorator and decorator != self)

    def validate(
        self,
        query=None,
        json=None,
        headers=None,
        cookies=None,
        resp=None,
        tags=(),
        security=None,
        before=None,
        after=None,
    ):
        """
        - validate query, json, headers in request
        - validate response body and status code
        - add tags to this API route
        - add security to this API route

        :param query: `pydantic.BaseModel`, query in uri like `?name=value`
        :param json: `pydantic.BaseModel`, JSON format request body
        :param headers: `pydantic.BaseModel`, if you have specific headers
        :param cookies: `pydantic.BaseModel`, if you have cookies for this route
        :param resp: `spectree.Response`
        :param tags: a tuple of strings or :class:`spectree.models.Tag`
        :param security: dict with security config for current route and method
        :param before: :meth:`spectree.utils.default_before_handler` for
            specific endpoint
        :param after: :meth:`spectree.utils.default_after_handler` for
            specific endpoint
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

            validation = async_validate if self.backend.ASYNC else sync_validate

            if self.config.ANNOTATIONS:
                nonlocal query
                query = func.__annotations__.get("query", query)
                nonlocal json
                json = func.__annotations__.get("json", json)
                nonlocal headers
                headers = func.__annotations__.get("headers", headers)
                nonlocal cookies
                cookies = func.__annotations__.get("cookies", cookies)

            # register
            for name, model in zip(
                ("query", "json", "headers", "cookies"), (query, json, headers, cookies)
            ):
                if model is not None:
                    model_key = self._add_model(model=model)
                    setattr(validation, name, model_key)

            if resp:
                for model in resp.models:
                    self._add_model(model=model)
                validation.resp = resp

            if tags:
                validation.tags = tags

            validation.security = security
            # register decorator
            validation._decorator = self
            return validation

        return decorate_validation

    def _add_model(self, model) -> str:
        """
        unified model processing
        """

        model_key = get_model_key(model=model)
        self.models[model_key] = deepcopy(get_model_schema(model=model))

        return model_key

    def _generate_spec(self):
        """
        generate OpenAPI spec according to routes and decorators
        """
        routes, tags = {}, {}
        for route in self.backend.find_routes():
            path, parameters = self.backend.parse_path(route)
            routes[path] = routes.get(path, {})
            path_is_empty = True
            for method, func in self.backend.parse_func(route):
                if self.backend.bypass(func, method) or self.bypass(func):
                    continue

                path_is_empty = False
                name = parse_name(func)
                summary, desc = parse_comments(func)
                func_tags = getattr(func, "tags", ())
                for tag in func_tags:
                    if str(tag) not in tags:
                        tags[str(tag)] = (
                            tag.dict() if isinstance(tag, Tag) else {"name": tag}
                        )

                routes[path][method.lower()] = {
                    "summary": summary or f"{name} <{method}>",
                    "operationId": f"{method.lower()}_{path}",
                    "description": desc or "",
                    "tags": [str(x) for x in getattr(func, "tags", ())],
                    "parameters": parse_params(func, parameters[:], self.models),
                    "responses": parse_resp(func),
                }
                security = getattr(func, "security", None)
                if security is not None:
                    routes[path][method.lower()]["security"] = get_security(security)
                request_body = parse_request(func)
                if request_body:
                    routes[path][method.lower()]["requestBody"] = request_body

            if path_is_empty:
                del routes[path]

        spec = {
            "openapi": self.config.OPENAPI_VERSION,
            "info": {
                "title": self.config.TITLE,
                "version": self.config.VERSION,
                "description": self.config.DESCRIPTION,
            },
            "tags": list(tags.values()),
            "paths": {**routes},
            "components": {
                "schemas": {**self.models, **self._get_model_definitions()},
            },
        }

        if self.config.SERVERS:
            spec["servers"] = [
                server.dict(exclude_none=True) for server in self.config.SERVERS
            ]

        if self.config.SECURITY_SCHEMES:
            spec["components"]["securitySchemes"] = {
                scheme.name: scheme.data.dict(exclude_none=True, by_alias=True)
                for scheme in self.config.SECURITY_SCHEMES
            }

        spec["security"] = get_security(self.config.SECURITY)
        return spec

    def _get_model_definitions(self):
        """
        handle nested models
        """
        definitions = {}
        for name, schema in self.models.items():
            if "definitions" in schema:
                for key, value in schema["definitions"].items():
                    definitions[f"{name}.{key}"] = value
                del schema["definitions"]

        return definitions
