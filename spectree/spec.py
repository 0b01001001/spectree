from functools import partial, update_wrapper
from pydantic import BaseModel

from .plugins import PLUGINS
from .config import Config
from .utils import (
    parse_comments, parse_request, parse_params, parse_resp, parse_name,
    partial_as_func
)


class SpecTree:
    """
    Interface

    :param str backend: choose from ('flask', 'falcon', 'starlette')
    :param app: backend framework application instance (you can also register to it later)
    :param kwargs: update default :class:`spectree.config.Config`
    """

    def __init__(self, backend_name='base', app=None, **kwargs):
        self.config = Config(**kwargs)
        self.backend_name = backend_name
        self.backend = PLUGINS[backend_name](self)
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
        if not hasattr(self, '_spec'):
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
        if self.config.MODE == 'greedy':
            return False
        elif self.config.MODE == 'strict':
            if getattr(func, '_decorator', None) == self:
                return False
            return True
        else:
            decorator = getattr(func, '_decorator', None)
            if decorator and decorator != self:
                return True
            return False

    def validate(self, query=None, json=None, headers=None, cookies=None, resp=None, tags=[]):
        """
        - validate query, json, headers in request
        - validate response body and status code
        - add tags to this API route

        :param query: `pydantic.BaseModel`, query in uri like `?name=value`
        :param json: `pydantic.BaseModel`, JSON format request body
        :param headers: `pydantic.BaseModel`, if you have specific headers
        :param cookies: `pydantic.BaseModel`, if you have cookies for this route
        :param resp: `spectree.Response`
        :param tags: list of tags' string
        """
        def decorate_validation(func):
            if self.backend_name == 'falcon':
                # NOTE `functools.partialmethod` cannot be wrapped correctly
                validation = update_wrapper(partial_as_func(
                    self.backend.validate,
                    query=query, json=json, headers=headers, cookies=cookies,
                    func=func, resp=resp), func)
            else:
                validation = update_wrapper(partial(
                    self.backend.validate,
                    query=query, json=json, headers=headers, cookies=cookies,
                    func=func, resp=resp), func)

            # register
            for name, model in zip(('query', 'json', 'headers', 'cookies'),
                                   (query, json, headers, cookies)):
                if model is not None:
                    assert(issubclass(model, BaseModel))
                    self.models[model.__name__] = model.schema()
                    setattr(validation, name, model.__name__)

            if resp:
                for model in resp.models:
                    self.models[model.__name__] = model.schema()
                validation.resp = resp

            if tags:
                validation.tags = tags

            # register decorator
            validation._decorator = self
            return validation
        return decorate_validation

    def _generate_spec(self):
        """
        generate OpenAPI spec according to routes and decorators
        """
        routes, tags = {}, {}
        for route in self.backend.find_routes():
            path, parameters = self.backend.parse_path(route)
            routes[path] = routes.get(path, {})
            for method, func in self.backend.parse_func(route):
                if self.backend.bypass(func, method) or self.bypass(func):
                    continue

                name = parse_name(func)
                summary, desc = parse_comments(func)
                func_tags = getattr(func, 'tags', [])
                for tag in func_tags:
                    if tag not in tags:
                        tags[tag] = {'name': tag}

                routes[path][method.lower()] = {
                    'summary': summary or f'{name} <{method}>',
                    'operationID': f'{name}__{method.lower()}',
                    'description': desc or '',
                    'tags': getattr(func, 'tags', []),
                    'requestBody': parse_request(func),
                    'parameters': parse_params(func, parameters[:]),
                    'responses': parse_resp(func),
                }

        spec = {
            'openapi': self.config.OPENAPI_VERSION,
            'info': {
                'title': self.config.TITLE,
                'version': self.config.VERSION,
            },
            'tags': list(tags.values()),
            'paths': {**routes},
            'components': {
                'schemas': {**self.models}
            },
            'definitions': self._get_model_definitions()
        }
        return spec

    def _get_model_definitions(self):
        """
        handle nested models
        """
        definitions = {}
        for schema in self.models.values():
            if 'definitions' in schema:
                for key, value in schema['definitions'].items():
                    definitions[key] = value
                del schema['definitions']

        return definitions
