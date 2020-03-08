import re
import inspect

# parse HTTP status code to get the code
HTTP_CODE = re.compile(r'^HTTP_(?P<code>\d{3})$')


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
    return doc[0], doc[1].strip()


def parse_request(func):
    """
    get json spec
    """
    data = {}
    if hasattr(func, 'json'):
        data = {
            'content': {
                'application/json': {
                    'schema': {
                        '$ref': f'#/components/schemas/{func.json}'
                    }
                }
            }
        }
    return data


def parse_params(func, params, models):
    """
    get spec for (query, headers, cookies)
    """
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
        headers = models[func.headers]
        for key, value in headers['properties'].items():
            params.append({
                'name': key,
                'in': 'header',
                'type': value['type'],
                'required': key in headers['required'],
            })
    if hasattr(func, 'cookies'):
        cookies = models[func.cookies]
        for key, value in cookies['properties'].items():
            params.append({
                'name': key,
                'in': 'cookie',
                'type': value['type'],
                'required': key in cookies['required'],
            })
    return params


def parse_resp(func):
    """
    get the response spec

    If this function does not have explicit ``resp`` but have other models,
    a ``422 Validation Error`` will be append to the response spec. Since
    this may be triggered in the validation step.
    """
    responses = {}
    if hasattr(func, 'resp'):
        responses = func.resp.generate_spec()

    if '422' not in responses and has_model(func):
        responses['422'] = {'description': 'Validation Error'}

    return responses


def has_model(func):
    """
    return True if this function have ``pydantic.BaseModel``
    """
    if any(hasattr(func, x) for x in ('query', 'json', 'headers')):
        return True

    if hasattr(func, 'resp') and func.resp.has_model():
        return True

    return False


def parse_code(http_code):
    """
    get the code of this HTTP status

    :param str http_code: format like ``HTTP_200``
    """
    match = HTTP_CODE.match(http_code)
    if not match:
        return None
    return match.group('code')


def parse_name(func):
    """
    the func can be

        * undecorated functions
        * decorated functions
        * decorated class methods
    """
    return func.__name__
