# Spectree

[![GitHub Actions](https://github.com/0b01001001/spectree/workflows/Python%20package/badge.svg)](https://github.com/0b01001001/spectree/actions)
[![pypi](https://img.shields.io/pypi/v/spectree.svg)](https://pypi.python.org/pypi/spectree)
[![versions](https://img.shields.io/pypi/pyversions/spectree.svg)](https://github.com/0b01001001/spectree)
[![Language grade: Python](https://img.shields.io/lgtm/grade/python/g/0b01001001/spectree.svg?logo=lgtm&logoWidth=18)](https://lgtm.com/projects/g/0b01001001/spectree/context:python)
[![Documentation Status](https://readthedocs.org/projects/spectree/badge/?version=latest)](https://spectree.readthedocs.io/en/latest/?badge=latest)

Yet another library to generate OpenAPI document and validate request & response with Python annotations.

## Features

* Less boilerplate code, only annotations, no need for YAML :sparkles:
* Generate API document with [Redoc UI](https://github.com/Redocly/redoc) or [Swagger UI](https://github.com/swagger-api/swagger-ui) :yum:
* Validate query, JSON data, response data with [pydantic](https://github.com/samuelcolvin/pydantic/) :wink:
* Current support:
  * Flask [demo](#flask)
  * Falcon [demo](#falcon)
  * Starlette [demo](#starlette)

## Quick Start

install with pip: pip install git+git://github.com/oscfrayle/spectree.git@v0.3.4

### Examples

'''python
import falcon
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


from constants import PAGES

api = SpecTree('falcon', title='Demo API', version='v1.0', path="api/v1/docs", page=PAGES["swagger"])


class UserProfile:
    @api.validate(json=Profile, resp=Response(HTTP_200=Message, HTTP_403=None), tags=['api'])
    def on_post(self, req, resp):
        """
        verify user profile (summary of this endpoint)

        user's name, user's age, ... (long description)
        """
        print(req.context.json)  # or `req.media`
        resp.media = {'text': 'it works'}

    @api.validate(json=Profile, resp=Response(HTTP_200=Message, HTTP_403=None), tags=['api'])
    def on_get(self, req, resp):
        """
        verify user profile (summary of this endpoinzzzt)

        user's name, user's age, ... (long description)
        """
        print(req.context.json)  # or `req.media`
        resp.media = {'text': 'it works'}


app = falcon.API()
app.add_route('/api/user', UserProfile())
api.register(app)

'''

### Run

gunicorn app:app -b :8009


