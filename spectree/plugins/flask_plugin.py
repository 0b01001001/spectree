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

    def request_validation(self, request, query, json, headers, cookies):
        req_query = request.args or {}
        req_json = request.get_json() or {}
        req_headers = request.headers or {}
        req_cookies = request.cookies or {}
        request.context = Context(
            query.parse_obj(req_query) if query else None,
            json.parse_obj(req_json) if json else None,
            headers.parse_obj(req_headers) if headers else None,
            cookies.parse_obj(req_cookies) if cookies else None,
        )

    def validate(self,
                 func,
                 query, json, headers, cookies, resp,
                 before, after,
                 *args, **kwargs):
        from flask import request, abort, make_response, jsonify

        response, req_validation_error, resp_validation_error = None, None, None
        try:
            self.request_validation(request, query, json, headers, cookies)
        except ValidationError as err:
            req_validation_error = err
            response = make_response(jsonify(err.errors()), 422)

        before(request, response, req_validation_error, None)
        if req_validation_error:
            abort(response)

        response = make_response(func(*args, **kwargs))

        if resp and resp.has_model():
            model = resp.find_model(response.status_code)
            if model:
                try:
                    model.validate(response.get_json())
                except ValidationError as err:
                    resp_validation_error = err
                    response = make_response(jsonify(
                        {'message': 'response validation error'}
                    ), 500)

        after(request, response, resp_validation_error, None)

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
