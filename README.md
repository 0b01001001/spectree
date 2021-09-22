# Spectree


[![GitHub Actions](https://github.com/0b01001001/spectree/workflows/Python%20package/badge.svg)](https://github.com/0b01001001/spectree/actions)
[![pypi](https://img.shields.io/pypi/v/spectree.svg)](https://pypi.python.org/pypi/spectree)
[![versions](https://img.shields.io/pypi/pyversions/spectree.svg)](https://github.com/0b01001001/spectree)
[![Language grade: Python](https://img.shields.io/lgtm/grade/python/g/0b01001001/spectree.svg?logo=lgtm&logoWidth=18)](https://lgtm.com/projects/g/0b01001001/spectree/context:python)
[![Python document](https://github.com/0b01001001/spectree/workflows/Python%20document/badge.svg)](https://0b01001001.github.io/spectree/)

Yet another library to generate OpenAPI document and validate request & response with Python annotations.

## Features

* Less boilerplate code, only annotations, no need for YAML :sparkles:
* Generate API document with [Redoc UI](https://github.com/Redocly/redoc) or [Swagger UI](https://github.com/swagger-api/swagger-ui) :yum:
* Validate query, JSON data, response data with [pydantic](https://github.com/samuelcolvin/pydantic/) :wink:
* Current support:
  * Flask [demo](#flask)
  * Falcon [demo](#falcon) (including ASGI under Falcon 3+)
  * Starlette [demo](#starlette)

## Quick Start

install with pip: `pip install spectree`

### Examples

Check the [examples](/examples) folder.

* [flask example](/examples/flask_demo.py)
* [falcon example with logging when validation failed](/examples/falcon_demo.py)
* [starlette example](examples/starlette_demo.py)

### Step by Step

1. Define your data structure used in (query, json, headers, cookies, resp) with `pydantic.BaseModel`
2. create `spectree.SpecTree` instance with the web framework name you are using, like `api = SpecTree('flask')`
3. `api.validate` decorate the route with
   * `query`
   * `json`
   * `headers`
   * `cookies`
   * `resp`
   * `tags`
   * `security`
4. access these data with `context(query, json, headers, cookies)` (of course, you can access these from the original place where the framework offered)
   * flask: `request.context`
   * falcon: `req.context`
   * starlette: `request.context`
5. register to the web application `api.register(app)`
6. check the document at URL location `/apidoc/redoc` or `/apidoc/swagger`

If the request doesn't pass the validation, it will return a 422 with JSON error message(ctx, loc, msg, type).

### Falcon response validation

For falcon response, this library only validates against media as it is the serializable object. Response.body(deprecated in falcon 3.0 and replaced by text) is a string representing response content and will not be validated. For no assigned media situation, `resp` parameter in `api.validate` should be like `Response(HTTP_200=None)`

### Opt-in type annotation feature
This library also supports injection of validated fields into view function arguments along with parameter annotation based type declaration. This works well with linters that can take advantage of typing features like mypy. See examples section below.

## How To

> How to add summary and description to endpoints?

Just add docs to the endpoint function. The 1st line is the summary, and the rest is the description for this endpoint.

> How to add description to parameters?

Check the [pydantic](https://pydantic-docs.helpmanual.io/usage/schema/) document about description in `Field`.

> Any config I can change?

Of course. Check the [config](https://spectree.readthedocs.io/en/latest/config.html) document.

You can update the config when init the spectree like:

```py
SpecTree('flask', title='Demo API', version='v1.0', path='doc')
```

> What is `Response` and how to use it?

To build a response for the endpoint, you need to declare the status code with format `HTTP_{code}` and corresponding data (optional).

```py
Response(HTTP_200=None, HTTP_403=ForbidModel)
Response('HTTP_200') # equals to Response(HTTP_200=None)
```

> How to secure API endpoints?

For secure API endpoints it is needed to define `security_schemes` argument in `SpecTree` constructor. `security_schemes` argument needs to contain array of `SecurityScheme` objects. Then there are two ways to enforce security:

1. You can enforce security on individual API endpoints by defining the `security` argument in the `api.validate` decorator of relevant function / method (this corresponds to define security section on operation level, under `paths`, in `OpenAPI`). `security` argument is defined as dictionary, where each key is the name of security used in `security_schemes` argument of `SpecTree` constructor and its value is required security scope, as is showed in following example:
```py
api = SpecTree(security_schemes=[
        SecurityScheme(
            name="auth_apiKey",
            data={"type": "apiKey", "name": "Authorization", "in": "header"},
        ),
        SecurityScheme(
            name="auth_oauth2",
            data={
                "type": "oauth2",
                "flows": {
                    "authorizationCode": {
                        "authorizationUrl": "https://example.com/oauth/authorize",
                        "tokenUrl": "https://example.com/oauth/token",
                        "scopes": {
                            "read": "Grants read access",
                            "write": "Grants write access",
                            "admin": "Grants access to admin operations",
                        },
                    },
                },
            },
        ),
        # ...
    ],
    # ...
)


# Not secured API endpoint
@api.validate(
    resp=Response(HTTP_200=None),
)
def foo():
    ...


# API endpoint secured by API key type or OAuth2 type
@api.validate(
    resp=Response(HTTP_200=None),
    security={"auth_apiKey": [], "auth_oauth2": ["read", "write"]},  # Local security type
)
def bar():
    ...
```
2. You can enforce security on whole API by defining `security` argument in the `SpecTree` constructor (this corresponds to define security section on the root level in `OpenAPI`). It is possible to override global security by defining local security, as well as override to no security on some API endpoint, in `security` argument of `api.validate` decorator of relevant function / method as was described in previous point. It is also shown in following small example:
```py
api = SpecTree(security_schemes=[
        SecurityScheme(
            name="auth_apiKey",
            data={"type": "apiKey", "name": "Authorization", "in": "header"},
        ),
        SecurityScheme(
            name="auth_oauth2",
            data={
                "type": "oauth2",
                "flows": {
                    "authorizationCode": {
                        "authorizationUrl": "https://example.com/oauth/authorize",
                        "tokenUrl": "https://example.com/oauth/token",
                        "scopes": {
                            "read": "Grants read access",
                            "write": "Grants write access",
                            "admin": "Grants access to admin operations",
                        },
                    },
                },
            },
        ),
        # ...
    ],
    security={"auth_apiKey": []},  # Global security type
    # ...
)

# Force no security
@api.validate(
    resp=Response(HTTP_200=None),
    security={}, # Locally overridden security type
)
def foo():
    ...


# Force another type of security than global one
@api.validate(
    resp=Response(HTTP_200=None),
    security={"auth_oauth2": ["read"]}, # Locally overridden security type
)
def bar():
    ...


# Use the global security
@api.validate(
    resp=Response(HTTP_200=None),
)
def foobar():
    ...
```

> What should I return when I'm using the library?

No need to change anything. Just return what the framework required.

> How to logging when the validation failed?

Validation errors are logged with INFO level. Details are passed into `extra`. Check the [falcon example](examples/falcon_demo.py) for details.

> How can I write a customized plugin for another backend framework?

Inherit `spectree.plugins.base.BasePlugin` and implement the functions you need. After that, init like `api = SpecTree(backend=MyCustomizedPlugin)`.

> How can I change the response when there is a validation error? Can I record some metrics?

This library provides `before` and `after` hooks to do these. Check the [doc](https://spectree.readthedocs.io/en/latest) or the [test case](tests/test_plugin_flask.py). You can change the handlers for SpecTree or for a specific endpoint validation.

## Demo

Try it with `http post :8000/api/user name=alice age=18`. (if you are using `httpie`)

### Flask

```py
from flask import Flask, request, jsonify
from pydantic import BaseModel, Field, constr
from spectree import SpecTree, Response


class Profile(BaseModel):
    name: constr(min_length=2, max_length=40) # Constrained Str
    age: int = Field(
        ...,
        gt=0,
        lt=150,
        description='user age(Human)'
    )

    class Config:
        schema_extra = {
            # provide an example
            'example': {
                'name': 'very_important_user',
                'age': 42,
            }
        }


class Message(BaseModel):
    text: str


app = Flask(__name__)
api = SpecTree('flask')


@app.route('/api/user', methods=['POST'])
@api.validate(json=Profile, resp=Response(HTTP_200=Message, HTTP_403=None), tags=['api'])
def user_profile():
    """
    verify user profile (summary of this endpoint)

    user's name, user's age, ... (long description)
    """
    print(request.context.json) # or `request.json`
    return jsonify(text='it works')


if __name__ == "__main__":
    api.register(app) # if you don't register in api init step
    app.run(port=8000)

```

#### Flask example with type annotation

```python
# opt in into annotations feature
api = SpecTree("flask", annotations=True)


@app.route('/api/user', methods=['POST'])
@api.validate(resp=Response(HTTP_200=Message, HTTP_403=None), tags=['api'])
def user_profile(json: Profile):
    """
    verify user profile (summary of this endpoint)

    user's name, user's age, ... (long description)
    """
    print(json) # or `request.json`
    return jsonify(text='it works')
```

### Falcon

```py
import falcon
from wsgiref import simple_server
from pydantic import BaseModel, Field, constr
from spectree import SpecTree, Response


class Profile(BaseModel):
    name: constr(min_length=2, max_length=40)  # Constrained Str
    age: int = Field(
        ...,
        gt=0,
        lt=150,
        description='user age(Human)'
    )


class Message(BaseModel):
    text: str


api = SpecTree('falcon')


class UserProfile:
    @api.validate(json=Profile, resp=Response(HTTP_200=Message, HTTP_403=None), tags=['api'])
    def on_post(self, req, resp):
        """
        verify user profile (summary of this endpoint)

        user's name, user's age, ... (long description)
        """
        print(req.context.json)  # or `req.media`
        resp.media = {'text': 'it works'}


if __name__ == "__main__":
    app = falcon.API()
    app.add_route('/api/user', UserProfile())
    api.register(app)

    httpd = simple_server.make_server('localhost', 8000, app)
    httpd.serve_forever()

```

#### Falcon with type annotations

```python
# opt in into annotations feature
api = SpecTree("falcon", annotations=True)


class UserProfile:
    @api.validate(resp=Response(HTTP_200=Message, HTTP_403=None), tags=['api'])
    def on_post(self, req, resp, json: Profile):
        """
        verify user profile (summary of this endpoint)

        user's name, user's age, ... (long description)
        """
        print(req.context.json)  # or `req.media`
        resp.media = {'text': 'it works'}
```

### Starlette

```py
import uvicorn
from starlette.applications import Starlette
from starlette.routing import Route, Mount
from starlette.responses import JSONResponse
from pydantic import BaseModel, Field, constr
from spectree import SpecTree, Response


class Profile(BaseModel):
    name: constr(min_length=2, max_length=40)  # Constrained Str
    age: int = Field(
        ...,
        gt=0,
        lt=150,
        description='user age(Human)'
    )


class Message(BaseModel):
    text: str


api = SpecTree('starlette')


@api.validate(json=Profile, resp=Response(HTTP_200=Message, HTTP_403=None), tags=['api'])
async def user_profile(request):
    """
    verify user profile (summary of this endpoint)

    user's name, user's age, ... (long description)
    """
    print(request.context.json)  # or await request.json()
    return JSONResponse({'text': 'it works'})


if __name__ == "__main__":
    app = Starlette(routes=[
        Mount('api', routes=[
            Route('/user', user_profile, methods=['POST']),
        ])
    ])
    api.register(app)

    uvicorn.run(app)

```

#### Starlette example with type annotations

```python
# opt in into annotations feature
api = SpecTree("flask", annotations=True)


@api.validate(resp=Response(HTTP_200=Message, HTTP_403=None), tags=['api'])
async def user_profile(request, json=Profile):
    """
    verify user profile (summary of this endpoint)

    user's name, user's age, ... (long description)
    """
    print(request.context.json)  # or await request.json()
    return JSONResponse({'text': 'it works'})
```


## FAQ

> ValidationError: missing field for headers

The HTTP headers' keys in Flask are capitalized, in Falcon are upper cases, in Starlette are lower cases.
You can use [`pydantic.root_validators(pre=True)`](https://pydantic-docs.helpmanual.io/usage/validators/#root-validators) to change all the keys into lower cases or upper cases.

> ValidationError: value is not a valid list for query

Since there is no standard for HTTP query with multiple values, it's hard to find the way to handle this for different web frameworks. So I suggest not to use list type in query until I find a suitable way to fix it.
