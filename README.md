# SpecTree


[![GitHub Actions](https://github.com/0b01001001/spectree/workflows/Python%20package/badge.svg)](https://github.com/0b01001001/spectree/actions)
[![pypi](https://img.shields.io/pypi/v/spectree.svg)](https://pypi.python.org/pypi/spectree)
[![versions](https://img.shields.io/pypi/pyversions/spectree.svg)](https://github.com/0b01001001/spectree)
[![CodeQL](https://github.com/0b01001001/spectree/actions/workflows/codeql.yml/badge.svg)](https://github.com/0b01001001/spectree/actions/workflows/codeql.yml)
[![Python document](https://github.com/0b01001001/spectree/workflows/Python%20document/badge.svg)](https://0b01001001.github.io/spectree/)

Yet another library to generate OpenAPI documents and validate requests & responses with Python annotations.

If all you need is a framework-agnostic library that can generate OpenAPI document, check [defspec](https://github.com/kemingy/defspec/).

## Features

* Less boilerplate code, only annotations, no need for YAML :sparkles:
* Generate API document with [Redoc UI](https://github.com/Redocly/redoc), [Scalar UI](https://github.com/scalar/scalar) or [Swagger UI](https://github.com/swagger-api/swagger-ui) :yum:
* Validate query, JSON data, response data with [pydantic](https://github.com/samuelcolvin/pydantic/) (both v1 & v2) :wink:
* Current support:
  * Flask [demo](#flask)
  * Quart [demo](#quart)
  * Falcon [demo](#falcon)
  * Starlette [demo](#starlette)

## Quick Start

Install with pip:

```bash
pip install spectree
```

If you want to install with offline OpenAPI web pages support:

> Offline mode doesn't support SwaggerUI OAuth2 redirection.

```bash
pip install spectree[offline]
```

### Examples

Check the [examples](examples) folder.

* [flask example](examples/flask_demo.py)
* [quart example](examples/quart_demo.py)
* [falcon example with logging when validation failed](examples/falcon_demo.py)
* [starlette example](examples/starlette_demo.py)

### Step by Step

1. Define your data structure used in (query, json, headers, cookies, resp) with `pydantic.BaseModel`
2. create `spectree.SpecTree` instance with the web framework name you are using, like `api = SpecTree('flask')`
3. `api.validate` decorate the route with (the default value is given in parentheses):
   * `query`
   * `json`
   * `headers`
   * `cookies`
   * `resp`
   * `tags` *(no tags on endpoint)*
   * `security` *(`None` - endpoint is not secured)*
   * `deprecated` *(`False` - endpoint is not marked as deprecated)*
4. access these data from the function annotations (see the examples below). Of course, you can still access them from the original place where the framework offered.
5. register to the web application `api.register(app)`
6. check the document at URL location `/apidoc/redoc` or `/apidoc/swagger` or `/apidoc/scalar`

If the request doesn't pass the validation, it will return a 422 with a JSON error message(ctx, loc, msg, type).

### Falcon response validation

For Falcon response, this library only validates against media as it is the serializable object. Response.text is a string representing response content and will not be validated. For no assigned media situation, `resp` parameter in `api.validate` should be like `Response(HTTP_200=None)`

### Opt-in type annotation feature
This library also supports the injection of validated fields into view function arguments along with parameter annotation-based type declaration. This works well with linters that can take advantage of typing features like mypy. See the examples section below.

## How-To

> How to add summary and description to endpoints?

Just add docs to the endpoint function. The 1st line is the summary, and the rest is the description for this endpoint.

> How to add a description to parameters?

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
# with custom code description
Response(HTTP_403=(ForbidModel, "custom code description"))
```

> How can I skip the validation?

Add `skip_validation=True` to the decorator.

Before v1.3.0, this only skip the response validation.

Starts from v1.3.0, this will skip all the validations. As an result, you won't be able to access the validated data from `context`.

```py
@api.validate(json=Profile, resp=Response(HTTP_200=Message, HTTP_403=None), skip_validation=True)
```

> How can I use the validation without the OpenAPI document?

The OpenAPI endpoints are added by `spectree.register(app)`. If you don't want to add the OpenAPI endpoints, you don't need to register it to the application.

> How to secure API endpoints?

For secure API endpoints, it is needed to define the `security_schemes` argument in the `SpecTree` constructor. `security_schemes` argument needs to contain an array of `SecurityScheme` objects. Then there are two ways to enforce security:

1. You can enforce security on individual API endpoints by defining the `security` argument in the `api.validate` decorator of relevant function/method (this corresponds to define security section on operation level, under `paths`, in `OpenAPI`). `security` argument is defined as a dictionary, where each key is the name of security used in `security_schemes` argument of `SpecTree` constructor and its value is required security scope, as is showed in the following example:

<details>
<summary>Click to expand the code example:</summary>
<p>

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

</p>
</details>


2. You can enforce security on the whole API by defining the `security` argument in the `SpecTree` constructor (this corresponds to the define security section on the root level in `OpenAPI`). It is possible to override global security by defining local security, as well as override to no security on some API endpoint, in the `security` argument of `api.validate` decorator of relevant function/method as was described in the previous point. It is also shown in the following small example:

<details>
<summary>Click to expand the code example:</summary>
<p>

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

</p>
</details>

> How to mark deprecated endpoint?

Use `deprecated` attribute with value `True` in `api.validate()` decorator. This way, an endpoint will be marked as
 deprecated and will be marked with a strikethrough in API documentation.

Code example:
```
@api.validate(
    deprecated=True,
)
def deprecated_endpoint():
    ...
```

> What should I return when I'm using the library?

No need to change anything. Just return what the framework required.

> How to log when the validation failed?

Validation errors are logged with the INFO level. Details are passed into `extra`. Check the [falcon example](examples/falcon_demo.py) for details.

> How can I write a customized plugin for another backend framework?

Inherit `spectree.plugins.base.BasePlugin` and implement the functions you need. After that, init like `api = SpecTree(backend=MyCustomizedPlugin)`.

> How to use a customized template page?

```py
SpecTree(page_templates={"page_name": "customized page contains {spec_url} for rendering"})
```

In the above example, the key "page_name" will be used in the URL to access this page "/apidoc/page_name". The value should be a string that contains `{spec_url}` which will be used to access the OpenAPI JSON file.

> How can I change the response when there is a validation error? Can I record some metrics?

This library provides `before` and `after` hooks to do these. Check the [doc](https://spectree.readthedocs.io/en/latest) or the [test case](tests/test_plugin_flask.py). You can change the handlers for SpecTree or a specific endpoint validation.

> How to change the default `ValidationError` status code?

You can change the `validation_error_status` in SpecTree (global) or a specific endpoint (local). This also takes effect in the OpenAPI documentation.

> How can I return my model directly?

Yes, returning an instance of `BaseModel` will assume the model is valid and bypass spectree's validation and automatically call `.dict()` on the model.

For starlette you should return a `PydanticResponse`:
```py
from spectree.plugins.starlette_plugin import PydanticResponse

return PydanticResponse(MyModel)
```

## Demo

Try it with `http post :8000/api/user name=alice age=18`. (if you are using `httpie`)

### Flask

```py
from flask import Flask, jsonify
from pydantic import BaseModel, Field

from spectree import Response, SpecTree


class Profile(BaseModel):
    name: str
    age: int = Field(..., gt=0, lt=150, description="user age(Human)")

    class Config:
        schema_extra = {
            # provide an example
            "example": {
                "name": "very_important_user",
                "age": 42,
            }
        }


class Message(BaseModel):
    text: str


app = Flask(__name__)
spec = SpecTree("flask")


@app.route("/api/user", methods=["POST"])
@spec.validate(resp=Response(HTTP_200=Message, HTTP_403=None), tags=["api"])
def user_profile(json: Profile):
    """
    verify user profile (summary of this endpoint)

    user's name, user's age, ... (long description)
    """
    print(json)  # or `request.json`
    return jsonify(text="it works")  # or `Message(text='it works')`


if __name__ == "__main__":
    spec.register(app)  # if you don't register in api init step
    app.run(port=8000)
```

### Quart

```py
from pydantic import BaseModel, Field
from quart import Quart, jsonify

from spectree import Response, SpecTree


class Profile(BaseModel):
    name: str
    age: int = Field(..., gt=0, lt=150, description="user age")

    class Config:
        schema_extra = {
            # provide an example
            "example": {
                "name": "very_important_user",
                "age": 42,
            }
        }


class Message(BaseModel):
    text: str


app = Quart(__name__)
spec = SpecTree("quart")


@app.route("/api/user", methods=["POST"])
@spec.validate(resp=Response(HTTP_200=Message, HTTP_403=None), tags=["api"])
async def user_profile(json: Profile):
    """
    verify user profile (summary of this endpoint)

    user's name, user's age, ... (long description)
    """
    print(json)  # or `request.json`
    return jsonify(text="it works")  # or `Message(text="it works")`


if __name__ == "__main__":
    spec.register(app)
    app.run(port=8000)
```

### Falcon

```py
from wsgiref import simple_server

import falcon
from pydantic import BaseModel, Field

from spectree import Response, SpecTree


class Profile(BaseModel):
    name: str
    age: int = Field(..., gt=0, lt=150, description="user age(Human)")


class Message(BaseModel):
    text: str


spec = SpecTree("falcon")


class UserProfile:
    @spec.validate(resp=Response(HTTP_200=Message, HTTP_403=None), tags=["api"])
    def on_post(self, req, resp, json: Profile):
        """
        verify user profile (summary of this endpoint)

        user's name, user's age, ... (long description)
        """
        print(json)  # or `req.media`
        resp.media = {"text": "it works"}  # or `resp.media = Message(text='it works')`


if __name__ == "__main__":
    app = falcon.App()
    app.add_route("/api/user", UserProfile())
    spec.register(app)

    httpd = simple_server.make_server("localhost", 8000, app)
    httpd.serve_forever()
```

### Starlette

```py
import uvicorn
from pydantic import BaseModel, Field
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route

from spectree import Response, SpecTree

# from spectree.plugins.starlette_plugin import PydanticResponse


class Profile(BaseModel):
    name: str
    age: int = Field(..., gt=0, lt=150, description="user age(Human)")


class Message(BaseModel):
    text: str


spec = SpecTree("starlette")


@spec.validate(resp=Response(HTTP_200=Message, HTTP_403=None), tags=["api"])
async def user_profile(request, json: Profile):
    """
    verify user profile (summary of this endpoint)

    user's name, user's age, ... (long description)
    """
    print(json)  # or await request.json()
    return JSONResponse(
        {"text": "it works"}
    )  # or `return PydanticResponse(Message(text='it works'))`


if __name__ == "__main__":
    app = Starlette(
        routes=[
            Mount(
                "/api",
                routes=[
                    Route("/user", user_profile, methods=["POST"]),
                ],
            )
        ]
    )
    spec.register(app)

    uvicorn.run(app)
```


## FAQ

> ValidationError: missing field for headers

The HTTP headers' keys in Flask are capitalized, in Falcon are upper cases, in Starlette are lower cases.
You can use [`pydantic.model_validator(mode="before")`](https://docs.pydantic.dev/dev/concepts/validators/#model-validators) to change all the keys into lower cases or upper cases.

> ValidationError: value is not a valid list for the query

Since there is no standard for HTTP queries with multiple values, it's hard to find a way to handle this for different web frameworks.
