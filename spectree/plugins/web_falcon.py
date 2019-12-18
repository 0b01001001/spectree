import re
from pydantic import ValidationError

from .base import BasePlugin
from .page import PAGES


class OpenAPI:
    def __init__(self, spec):
        self.spec = spec

    def on_get(self, req, resp):
        resp.media = self.spec


class DocPage:
    def __init__(self, config):
        self.page = PAGES[config.UI].format(config.spec_url)

    def on_get(self, req, resp):
        resp.content_type = 'text/html'
        resp.body = self.page


DOC_CLASS = [x.__name__ for x in (DocPage, OpenAPI)]
_FIELD_PATTERN = re.compile(
    # NOTE from `falcon.routing.compiled`
    r'{((?P<fname>[^}:]*)((?P<cname_sep>:(?P<cname>[^}\(]*))(\((?P<argstr>[^}]*)\))?)?)}'
)
# NOTE from `falcon.routing.compiled.CompiledRouterNode`
ESCAPE = r'[\.\(\)\[\]\?\$\*\+\^\|]'
ESCAPE_TO = r'\\\g<0>'
EXTRACT = r'{\2}'
# NOTE this regex is copied from werkzeug.routing._converter_args_re and
# modified to support only int args
INT_ARGS = re.compile(r'''
    ((?P<name>\w+)\s*=\s*)?
    (?P<value>\d+)\s*
''', re.VERBOSE)
INT_ARGS_NAMES = ('num_digits', 'min', 'max')


class FlaconPlugin(BasePlugin):
    def register_route(self, app, config, spec):
        app.add_route(
            f'/{config.PATH}', DocPage(config)
        )
        app.add_route(
            config.spec_url, OpenAPI(spec)
        )

    def find_routes(self, app):
        routes = []

        def find_node(node):
            if node.resource and node.resource.__class__.__name__ not in DOC_CLASS:
                routes.append(node)

            for child in node.children:
                find_node(child)

        for route in app._router._roots:
            find_node(route)

        return routes

    def parse_path(self, route):
        subs, parameters = [], []
        for segment in route.uri_template.strip('/').split('/'):
            matches = _FIELD_PATTERN.finditer(segment)
            if not matches:
                subs.append(segment)
                continue

            escaped = re.sub(ESCAPE, ESCAPE_TO, segment)
            subs.append(_FIELD_PATTERN.sub(EXTRACT, escaped))

            for field in matches:
                variable, converter, argstr = [field.group(name) for name in
                                               ('fname', 'cname', 'argstr')]

                if converter == 'int':
                    if argstr is None:
                        argstr = ''

                    arg_values = [None, None, None]
                    for index, field in enumerate(INT_ARGS.finditer(argstr)):
                        name, value = field.group('name'), field.group('value')
                        if name:
                            index = INT_ARGS_NAMES.index(name)
                        arg_values[index] = value

                    num_digits, minumum, maximum = arg_values
                    schema = {
                        'type': 'integer',
                        'format': f'int{num_digits}' if num_digits else 'int32',
                    }
                    if minumum:
                        schema['minimum'] = minumum
                    if maximum:
                        schema['maximum'] = maximum
                elif converter == 'uuid':
                    schema = {
                        'type': 'string',
                        'format': 'uuid'
                    }
                elif converter == 'dt':
                    schema = {
                        'type': 'string',
                        'format': 'date-time',
                    }
                else:
                    # no converter specified or customized converters
                    schema = {'type': 'string'}

                parameters.append({
                    'name': variable,
                    'in': 'path',
                    'required': True,
                    'schema': schema,
                })

        return f'/{"/".join(subs)}', parameters

    def validate(self, _req, _resp, *args, **kwargs):
        query = kwargs.pop('query')
        json = kwargs.pop('json')
        headers = kwargs.pop('headers')
        resp = kwargs.pop('resp')
        func = kwargs.pop('func')
        try:
            if query:
                _req.context.query = query(**_req.params)
            if headers:
                _req.context.headers = headers(**_req.headers)
            media = _req.media or {}
            if json:
                _req.context.media = json(**media)

        except ValidationError as err:
            _resp.status = '422 Unprocessable Entity'
            _resp.media = err.errors()
            return
        except Exception:
            raise

        print(args, kwargs)
        func(self, _req, _resp, *args, **kwargs)
        if resp:
            _resp.media = _resp.context.media.dict()

    def bypass(self, func, method):
        if not func.args:
            return False
        return True
