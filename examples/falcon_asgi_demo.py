import logging
from random import random

import falcon.asgi
import uvicorn
from pydantic import BaseModel, Field

from examples.common import File, FileResp, Query
from spectree import ExternalDocs, Response, SpecTree, Tag

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger()

spec = SpecTree(
    "falcon-asgi",
    title="Demo Service",
    version="0.1.2",
    annotations=True,
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
    async def on_get(self, req, resp):
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
    async def on_get(self, req, resp, source, target):
        """
        API summary

        description here: test information with `source` and `target`
        """
        resp.media = {"msg": f"hello from {source} to {target}"}

    @spec.validate(resp=Response(HTTP_200=Resp, HTTP_403=BadLuck))
    async def on_post(self, req, resp, source, target, query: Query, json: Data):
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
    async def on_post(self, req, resp, form: File):
        """
        post multipart/form-data demo

        demo for 'form'
        """
        file = req.context.form.file
        resp.media = {"filename": file.filename, "type": file.type}


if __name__ == "__main__":
    app = falcon.asgi.App()
    app.add_route("/ping", Ping())
    app.add_route("/api/{source}/{target}", Classification())
    app.add_route("/api/file_upload", FileUpload())
    spec.register(app)

    uvicorn.run(app, log_level="info")
