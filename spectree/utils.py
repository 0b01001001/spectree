from inspect import getdoc


def parse_comments(func):
    """
    parse function comments

    First line of comments will be saved as summary, and the rest
    will be saved as description.
    """
    doc = getdoc(func.keywords['func'])
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
