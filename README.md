# Spectree


[![GitHub Actions](https://github.com/0b01001001/spectree/workflows/Python%20package/badge.svg)](https://github.com/0b01001001/spectree/actions)
[![pypi](https://img.shields.io/pypi/v/spectree.svg)](https://pypi.python.org/pypi/spectree)
[![downloads](https://img.shields.io/pypi/dm/spectree.svg)](https://pypistats.org/packages/spectree)
[![versions](https://img.shields.io/pypi/pyversions/spectree.svg)](https://github.com/0b01001001/spectree)
[![Language grade: Python](https://img.shields.io/lgtm/grade/python/g/0b01001001/spectree.svg?logo=lgtm&logoWidth=18)](https://lgtm.com/projects/g/0b01001001/spectree/context:python)

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

### Demo

```py
```

### Step by Step

1. Define your data structure with `pydantic.BaseModel`
2. create `spectree.SpecTree` instance with the web framework name you are using `api = SpecTree('flask')`
3. `validate` the route
   * `query`
   * `json`
   * `headers`
   * `cookies`
   * `resp`
   * `tags`
4. access these data with `context(query, json, headers, cookies)`
   * flask: `request.context`
   * falcon: `req.context`
   * starlette: `request.context`
5. register to the web application `api.register(app)`
6. check the document at URL location `/apidoc/redoc` or `/apidoc/swagger`

### Examples

Check the [examples](/examples) folder.
