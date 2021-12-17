import logging
from random import random

import falcon.asgi
from pydantic import BaseModel, Field

from spectree import Response, SpecTree, Tag, models

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger()


api = SpecTree(
    "falcon-asgi",
    title="Demo Service",
    version="0.1.2",
    unknown="test",
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


class File(BaseModel):
    uid: str
    file: models.BaseFile


class FileResp(BaseModel):
    filename: str


class Ping:
    def check(self):
        pass

    @api.validate(tags=[demo])
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

    @api.validate(tags=[demo])
    async def on_get(self, req, resp, source, target):
        """
        API summary

        description here: test information with `source` and `target`
        """
        resp.media = {"msg": f"hello from {source} to {target}"}

    @api.validate(
        query=Query, json=Data, resp=Response(HTTP_200=Resp, HTTP_403=BadLuck)
    )
    async def on_post(self, req, resp, source, target):
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


class FileUpload:
    """
    file-handling demo
    """

    @api.validate(form=File, resp=Response(HTTP_200=FileResp), tags=["file-upload"])
    async def on_post(self, req, resp):
        """
        post multipart/form-data demo

        demo for 'form'
        """
        file = req.context.form.file
        resp.media = {"filename": file.filename}


app = falcon.asgi.App()
app.add_route("/ping", Ping())
app.add_route("/api/{source}/{target}", Classification())
app.add_route("/api/upload-file", FileUpload())
api.register(app)
