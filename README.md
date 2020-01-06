# Spectree


[![GitHub Actions](https://github.com/0b01001001/spectree/workflows/Python%20package/badge.svg)](https://github.com/0b01001001/spectree/actions)
[![pypi](https://img.shields.io/pypi/v/spectree.svg)](https://pypi.python.org/pypi/spectree)
[![downloads](https://img.shields.io/pypi/dm/spectree.svg)](https://pypistats.org/packages/spectree)
[![versions](https://img.shields.io/pypi/pyversions/spectree.svg)](https://github.com/0b01001001/spectree)
[![Language grade: Python](https://img.shields.io/lgtm/grade/python/g/0b01001001/spectree.svg?logo=lgtm&logoWidth=18)](https://lgtm.com/projects/g/0b01001001/spectree/context:python)
[![Documentation Status](https://readthedocs.org/projects/spectree/badge/?version=latest)](https://spectree.readthedocs.io/en/latest/?badge=latest)

Yet another library to generate OpenAPI document and validate request & response with Python annotations.

## Features

* Less boilerplate code, annotations are really easy-to-use :sparkles:
* Generate API document with [Redoc UI](https://github.com/Redocly/redoc) or [Swagger UI](https://github.com/swagger-api/swagger-ui) :yum:
* Validate query, JSON data, response data with [pydantic](https://github.com/samuelcolvin/pydantic/) :wink:
* Current support:
  * Flask
  * Falcon
  * Starlette

## Quick Start

install with pip: `pip install spectree`

### Examples

Check the [examples](/examples) folder.

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
4. access these data with `context(query, json, headers, cookies)` (of course, you can access these from the original place where the framework offered)
   * flask: `request.context`
   * falcon: `req.context`
   * starlette: `request.context`
5. register to the web application `api.register(app)`
6. check the document at URL location `/apidoc/redoc` or `/apidoc/swagger`

## Demo

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


class Message(BaseModel):
    text: str


app = Flask(__name__)
api = SpecTree('flask')


@app.route('/api/user', methods=['POST'])
@api.validate(json=Profile, resp=Response('HTTP_404', HTTP_200=Message), tags=['api'])
def user_profile():
    """
    verify user profile (summary of this endpoint)

    user's name, user'age, ... (long description)
    """
    print(request.context.json) # or `request.json`
    return jsonify(text='it works')


if __name__ == "__main__":
    api.register(app) # if you don't register in api init step
    app.run()

```

## FAQ

> ValidationError: missing field for headers

The HTTP headers' keys in Flask are capitalized, in Falcon are upper cases, in Starlette are lower cases.
You can use [`pydantic.root_validators(pre=True)`](https://pydantic-docs.helpmanual.io/usage/validators/#root-validators) to change all the keys into lower cases or upper cases.
