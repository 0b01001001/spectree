from pydantic import ValidationError

from .base import BasePlugin, Context
from .page import PAGES


class FlaskPlugin(BasePlugin):
    def find_routes(self):
        for rule in self.app.url_map.iter_rules():
            if any(str(rule).startswith(path) for path in (
                f'/{self.config.PATH}', '/static'
            )):
                continue
            yield rule

    def bypass(self, func, method):
        if method in ['HEAD', 'OPTIONS']:
            return True
        return False

    def parse_func(self, route):
        func = self.app.view_functions[route.endpoint]
        for method in route.methods:
            yield method, func

    def parse_path(self, route):
        from werkzeug.routing import parse_rule, parse_converter_args

        subs = []
        parameters = []

        for converter, arguments, variable in parse_rule(str(route)):
            if converter is None:
                subs.append(variable)
                continue
            subs.append(f'{{{variable}}}')

            args, kwargs = [], {}

            if arguments:
                args, kwargs = parse_converter_args(arguments)

            schema = None
            if converter == 'any':
                schema = {
                    'type': 'array',
                    'items': {
                        'type': 'string',
                        'enum': args,
                    }
                }
            elif converter == 'int':
                schema = {
                    'type': 'integer',
                    'format': 'int32',
                }
                if 'max' in kwargs:
                    schema['maximum'] = kwargs['max']
                if 'min' in kwargs:
                    schema['minimum'] = kwargs['min']
            elif converter == 'float':
                schema = {
                    'type': 'number',
                    'format': 'float',
                }
            elif converter == 'uuid':
                schema = {
                    'type': 'string',
                    'format': 'uuid',
                }
            elif converter == 'path':
                schema = {
                    'type': 'string',
                    'format': 'path',
                }
            elif converter == 'string':
                schema = {
                    'type': 'string',
                }
                for prop in ['length', 'maxLength', 'minLength']:
                    if prop in kwargs:
                        schema[prop] = kwargs[prop]
            elif converter == 'default':
                schema = {'type': 'string'}

            parameters.append({
                'name': variable,
                'in': 'path',
                'required': True,
                'schema': schema,
            })

        return ''.join(subs), parameters

    def get_req_data(self, request):
        query = request.args or {}
        json = request.get_json() or {}
        headers = request.headers or {}
        cookies = request.cookies or {}
        return query, json, headers, cookies

    def validate(self, func, query, json, headers, cookies, resp, *args, **kwargs):
        from flask import request, abort, make_response, jsonify

        try:
            arg, json_data, header, cookie = self.get_req_data(request)
            request.context = Context(
                query(**arg) if query else None,
                json(**json_data) if json else None,
                headers(**header) if headers else None,
                cookies(**cookie) if cookies else None,
            )
        except ValidationError as err:
            self.logger.info(
                '422 Validation Error',
                extra={
                    'spectree_model': err.model.__name__,
                    'spectree_validation': err.errors(),
                },
            )
            abort(make_response(jsonify(err.errors()), 422))
        except Exception:
            raise

        response = make_response(func(*args, **kwargs))

        if resp and resp.has_model():
            model = resp.find_model(response.status_code)
            if model:
                model.validate(response.get_json())

        return response

    def register_route(self, app):
        self.app = app
        from flask import jsonify

        self.app.add_url_rule(
            self.config.spec_url,
            'openapi',
            lambda: jsonify(self.spectree.spec),
        )

        for ui in PAGES:
            self.app.add_url_rule(
                f'/{self.config.PATH}/{ui}',
                f'doc_page_{ui}',
                lambda ui=ui: PAGES[ui].format(self.config.spec_url)
            )
