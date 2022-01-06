.. spectree documentation master file, created by
   sphinx-quickstart on Sun Dec  1 16:11:49 2019.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to spectree's documentation!
====================================

|GitHub Actions| |pypi| |versions| |Language grade: Python|
|Documentation Status|

Yet another library to generate OpenAPI document and validate request &
response with Python annotations.

Features
--------

-  Less boilerplate code, annotations are really easy-to-use
-  Generate API document with `Redoc UI`_ or `Swagger UI`_
-  Validate query, JSON data, response data with `pydantic`_
-  Current support:

   -  Flask
   -  Falcon (including Falcon ASGI)
   -  Starlette

Quick Start
-----------

install with pip: ``pip install spectree``

Examples
~~~~~~~~

Check the `examples`_ folder.

Step by Step
~~~~~~~~~~~~

1. Define your data structure used in (query, json, headers, cookies,
   resp) with ``pydantic.BaseModel``
2. create ``spectree.SpecTree`` instance with the web framework name you
   are using, like ``api = SpecTree('flask')``
3. ``api.validate`` decorate the route with

   -  ``query``
   -  ``json``
   -  ``headers``
   -  ``cookies``
   -  ``resp``
   -  ``tags``

4. access these data with ``context(query, json, headers, cookies)`` (of
   course, you can access these from the original place where the
   framework offered)

   -  flask: ``request.context``
   -  falcon: ``req.context``
   -  starlette: ``request.context``

5. register to the web application ``api.register(app)``
6. check the document at URL location ``/apidoc/redoc`` or
   ``/apidoc/swagger``

FAQ
---

   ValidationError: missing field for headers

The HTTP headers’ keys in Flask are capitalized, in Falcon are upper
cases, in Starlette are lower cases.

.. _Redoc UI: https://github.com/Redocly/redoc
.. _Swagger UI: https://github.com/swagger-api/swagger-ui
.. _pydantic: https://github.com/samuelcolvin/pydantic/
.. _examples: https://github.com/0b01001001/spectree/blob/master/examples

.. |GitHub Actions| image:: https://github.com/0b01001001/spectree/workflows/Python%20package/badge.svg
   :target: https://github.com/0b01001001/spectree/actions
.. |pypi| image:: https://img.shields.io/pypi/v/spectree.svg
   :target: https://pypi.python.org/pypi/spectree
.. |versions| image:: https://img.shields.io/pypi/pyversions/spectree.svg
   :target: https://github.com/0b01001001/spectree
.. |Language grade: Python| image:: https://img.shields.io/lgtm/grade/python/g/0b01001001/spectree.svg?logo=lgtm&logoWidth=18
   :target: https://lgtm.com/projects/g/0b01001001/spectree/context:python
.. |Documentation Status| image:: https://readthedocs.org/projects/spectree/badge/?version=latest
   :target: https://spectree.readthedocs.io/en/latest/?badge=latest


.. toctree::
   :maxdepth: 2
   :caption: Contents:

   spectree
   config
   response
   plugins
   models
   utils



Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
