import inspect
from functools import partial


def parse_comments(func):
    """
    parse function comments

    First line of comments will be saved as summary, and the rest
    will be saved as description.
    """
    doc = inspect.getdoc(func)
    if doc is None:
        return None, None
    doc = doc.split('\n', 1)
    if len(doc) == 1:
        return doc[0], None
    return doc


def parse_request(func):
    data = {
        'content': {
            'application/json': {
                'schema': {
                    '$ref': f'#/components/schemas/{func.json}'
                    if hasattr(func, 'json') else ''
                }
            }
        }
    }
    return data


def parse_params(func, params):
    if hasattr(func, 'query'):
        params.append({
            'name': func.query,
            'in': 'query',
            'required': True,
            'schema': {
                '$ref': f'#/components/schemas/{func.query}',
            }
        })
    if hasattr(func, 'headers'):
        params.append({
            'name': func.headers,
            'in': 'header',
            'schema': {
                '$ref': f'#/components/schemas/{func.headers}',
            }
        })
    if hasattr(func, 'cookies'):
        params.append({
            'name': func.cookies,
            'in': 'cookie',
            'schema': {
                '$ref': f'#/components/schemas/{func.cookies}',
            }
        })
    return params


def parse_resp(func):
    if not hasattr(func, 'resp'):
        return {}
    responses = func.resp.generate_spec()

    if '422' not in responses and has_model(func):
        responses['422'] = {'description': 'Validation Error'}

    return responses


def has_model(func):
    if any(hasattr(func, x) for x in ('query', 'json', 'headers')):
        return True

    if hasattr(func, 'resp') and func.resp.has_model():
        return True

    return False


def parse_code(http_code):
    return http_code.split('_', 1)[1]


def parse_name(func):
    if isinstance(func, partial):
        if inspect.ismethod(func.func):
            return func.func.__class__.__name__
        else:
            return func.__wrapped__.__name__
    else:
        return func.__name__


def pop_keywords(kwargs):
    query = kwargs.pop('query')
    json = kwargs.pop('json')
    headers = kwargs.pop('headers')
    cookies = kwargs.pop('cookies')
    resp = kwargs.pop('resp')
    func = kwargs.pop('func')
    return func, query, json, headers, cookies, resp
