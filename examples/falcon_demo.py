import logging
from random import random
from wsgiref import simple_server

import falcon
from pydantic import BaseModel, Field

from spectree import Response, SpecTree, Tag

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger()


api = SpecTree(
    "falcon",
    title="Demo Service",
    version="0.1.2",
    description="This is a demo service.",
    terms_of_service="https://github.io",
    contact={"name": "John", "email": "hello@github.com", "url": "https://github.com"},
    license={"name": "MIT", "url": "https://opensource.org/licenses/MIT"},
)

demo = Tag(name="demo", description="😊", externalDocs={"url": "https://github.com"})


class Query(BaseModel):
    text: str = Field(
        ...,
        max_length=100,
    )


class Resp(BaseModel):
    label: int = Field(
        ...,
        ge=0,
        le=9,
    )
    score: float = Field(
        ...,
        gt=0,
        lt=1,
    )


class BadLuck(BaseModel):
    loc: str
    msg: str
    typ: str


class Data(BaseModel):
    uid: str
    limit: int
    vip: bool


class Ping:
    def check(self):
        pass

    @api.validate(tags=[demo])
    def on_get(self, req, resp):
        """
        health check
        """
        self.check()
        logger.debug("ping <> pong")
        resp.media = {"msg": "pong"}


class Classification:
    """
    classification demo
    """

    @api.validate(tags=[demo])
    def on_get(self, req, resp, source, target):
        """
        API summary

        description here: test information with `source` and `target`
        """
        resp.media = {"msg": f"hello from {source} to {target}"}

    @api.validate(
        query=Query, json=Data, resp=Response(HTTP_200=Resp, HTTP_403=BadLuck)
    )
    def on_post(self, req, resp, source, target):
        """
        post demo

        demo for `query`, `data`, `resp`, `x`
        """
        logger.debug(f"{source} => {target}")
        logger.info(req.context.query)
        logger.info(req.context.json)
        if random() < 0.5:
            resp.status = falcon.HTTP_403
            resp.media = {"loc": "unknown", "msg": "bad luck", "typ": "random"}
            return
        resp.media = {"label": int(10 * random()), "score": random()}
        # resp.media = Resp(label=int(10 * random()), score=random())


if __name__ == "__main__":
    """
    cmd:
        http :8000/ping
        http ':8000/api/zh/en?text=hi' uid=neo limit=1 vip=true
    """
    app = falcon.API()
    app.add_route("/ping", Ping())
    app.add_route("/api/{source}/{target}", Classification())
    api.register(app)

    httpd = simple_server.make_server("localhost", 8000, app)
    httpd.serve_forever()
