import logging
from random import random
from wsgiref import simple_server

import falcon
from pydantic import BaseModel, Field

from examples.common import File, FileResp, Query
from spectree import ExternalDocs, Response, SpecTree, Tag

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger()

spec = SpecTree(
    "falcon",
    annotations=True,
    title="Demo Service",
    version="0.1.2",
    description="This is a demo service.",
    terms_of_service="https://github.io",
    contact={"name": "John", "email": "hello@github.com", "url": "https://github.com"},
    license={"name": "MIT", "url": "https://opensource.org/licenses/MIT"},
)

demo = Tag(
    name="demo", description="😊", externalDocs=ExternalDocs(url="https://github.com")
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

    @spec.validate(tags=[demo])
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

    @spec.validate(tags=[demo])
    def on_get(self, req, resp, source, target):
        """
        API summary

        description here: test information with `source` and `target`
        """
        resp.media = {"msg": f"hello from {source} to {target}"}

    @spec.validate(resp=Response(HTTP_200=Resp, HTTP_403=BadLuck))
    def on_post(self, req, resp, source, target, query: Query, json: Data):
        """
        post demo

        demo for `query`, `data`, `resp`
        """
        logger.debug("%s => %s", source, target)
        logger.info(query)
        logger.info(json)
        if random() < 0.5:
            resp.status = falcon.HTTP_403
            resp.media = {"loc": "unknown", "msg": "bad luck", "typ": "random"}
            return
        resp.media = {"label": int(10 * random()), "score": random()}


class FileUpload:
    """
    file-handling demo
    """

    @spec.validate(resp=Response(HTTP_200=FileResp), tags=["file-upload"])
    def on_post(self, req, resp, form: File):
        """
        post multipart/form-data demo

        demo for 'form'
        """
        file = form.file
        resp.media = {"filename": file.filename, "type": file.type}


def create_app():
    app = falcon.App()
    app.add_route("/ping", Ping())
    app.add_route("/api/{source}/{target}", Classification())
    app.add_route("/api/file_upload", FileUpload())
    spec.register(app)
    return app


if __name__ == "__main__":
    """
    cmd:
        http :8000/ping
        http ':8000/api/zh/en?text=hi' uid=neo limit=1 vip=true
    """
    app = create_app()
    httpd = simple_server.make_server("localhost", 8000, app)
    httpd.serve_forever()
