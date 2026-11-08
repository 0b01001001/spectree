"""Annotation injection must not resolve annotations other than the request ones.

The handlers return a type imported only under ``TYPE_CHECKING``; resolving every
annotation of the handler on each request used to answer valid requests with a
500 ``NameError``.
"""

import asyncio

import pytest
from falcon import App as FalconApp, testing as falcon_testing
from falcon.asgi import App as FalconAsgiApp
from flask import Flask
from quart import Quart
from starlette.applications import Starlette
from starlette.routing import Route
from starlette.testclient import TestClient

from spectree import SpecTree
from tests import type_checking_annotation_case as case

VALID = {"uid": 1, "limit": 2, "name": "spectree"}
INVALID = {"uid": "not a number", "limit": 2, "name": "spectree"}


def _run(coroutine):
    # A private loop leaves the global event loop state alone: `asyncio.run()`
    # unsets the current event loop, which other tests' clients may rely on.
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coroutine)
    finally:
        loop.close()


def _post_flask(model_case, payload):
    app = Flask(__name__)
    api = SpecTree("flask", model_adapter=model_case.adapter)
    view = api.validate()(case.sync_view)
    app.add_url_rule("/view", view_func=view, methods=["POST"])
    response = app.test_client().post("/view", json=payload)
    return response.status_code, response.get_json()


def _post_quart(model_case, payload):
    app = Quart(__name__)
    api = SpecTree("quart", model_adapter=model_case.adapter)
    view = api.validate()(case.async_view)
    app.add_url_rule("/view", view_func=view, methods=["POST"])

    async def post():
        response = await app.test_client().post("/view", json=payload)
        return response.status_code, await response.get_json()

    return _run(post())


def _post_falcon(model_case, payload):
    api = SpecTree("falcon", model_adapter=model_case.adapter)

    class Resource:
        on_post = api.validate()(case.FalconResource.on_post)

    app = FalconApp()
    app.add_route("/view", Resource())
    response = falcon_testing.TestClient(app).simulate_post("/view", json=payload)
    return response.status_code, response.json


def _post_falcon_asgi(model_case, payload):
    api = SpecTree("falcon-asgi", model_adapter=model_case.adapter)

    class Resource:
        on_post = api.validate()(case.FalconAsgiResource.on_post)

    app = FalconAsgiApp()
    app.add_route("/view", Resource())

    async def post():
        async with falcon_testing.ASGIConductor(app) as conductor:
            response = await conductor.simulate_post("/view", json=payload)
        return response.status_code, response.json

    return _run(post())


def _post_starlette(model_case, payload):
    api = SpecTree("starlette", model_adapter=model_case.adapter)
    view = api.validate()(case.starlette_view)
    app = Starlette(routes=[Route("/view", view, methods=["POST"])])
    response = TestClient(app).post("/view", json=payload)
    return response.status_code, response.json()


@pytest.mark.parametrize(
    "post",
    [
        pytest.param(_post_flask, id="flask"),
        pytest.param(_post_quart, id="quart"),
        pytest.param(_post_falcon, id="falcon"),
        pytest.param(_post_falcon_asgi, id="falcon-asgi"),
        pytest.param(_post_starlette, id="starlette"),
    ],
)
def test_injection_ignores_unresolvable_return_annotation(post, model_case):
    assert post(model_case, VALID) == (200, {"name": "spectree"})

    status, _ = post(model_case, INVALID)
    assert status == 422
