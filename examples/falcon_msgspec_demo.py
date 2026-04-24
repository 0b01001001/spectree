import logging
from random import random
from wsgiref import simple_server

import falcon
import msgspec

from spectree import ExternalDocs, Response, SpecTree, Tag
from spectree.model_adapter import get_msgspec_model_adapter

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger()

spec = SpecTree(
    "falcon",
    annotations=True,
    model_adapter=get_msgspec_model_adapter(),
    title="Demo Service",
    version="0.1.2",
    description="This is a demo service using msgspec models.",
    terms_of_service="https://github.io",
    contact={"name": "John", "email": "hello@github.com", "url": "https://github.com"},
    license={"name": "MIT", "url": "https://opensource.org/licenses/MIT"},
)

demo = Tag(
    name="demo", description="😊", externalDocs=ExternalDocs(url="https://github.com")
)


class Resp(msgspec.Struct):
    label: int
    score: float


class BadLuck(msgspec.Struct):
    loc: str
    msg: str
    typ: str


class Query(msgspec.Struct):
    text: str


class Data(msgspec.Struct):
    uid: str
    limit: int
    vip: bool


class Ping:
    @spec.validate(tags=[demo])
    def on_get(self, req, resp):
        resp.media = {"msg": "pong"}


class Classification:
    @spec.validate(resp=Response(HTTP_200=Resp, HTTP_403=BadLuck))
    def on_post(self, req, resp, source, target, query: Query, json: Data):
        logger.debug("%s => %s", source, target)
        logger.info(query)
        logger.info(json)
        if random() < 0.5:
            resp.status = falcon.HTTP_403
            resp.media = {"loc": "unknown", "msg": "bad luck", "typ": "random"}
            return

        resp.media = {"label": int(10 * random()), "score": random()}


def create_app():
    app = falcon.App()
    app.add_route("/ping", Ping())
    app.add_route("/api/{source}/{target}", Classification())
    spec.register(app)
    return app


if __name__ == "__main__":
    app = create_app()
    httpd = simple_server.make_server("localhost", 8000, app)
    httpd.serve_forever()
