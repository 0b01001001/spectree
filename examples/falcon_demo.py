import logging
from random import random
from wsgiref import simple_server

import falcon
from pydantic import BaseModel, Field

from spectree import BaseFile, Response, SpecTree, Tag

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


class File(BaseModel):
    uid: str = None
    file: BaseFile


class FileResp(BaseModel):
    filename: str
    type: str


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


class FileUpload:
    """
    file-handling demo
    """

    @api.validate(form=File, resp=Response(HTTP_200=FileResp), tags=["file-upload"])
    def on_post(self, req, resp):
        """
        post multipart/form-data demo

        demo for 'form'
        """
        file = req.context.form.file
        resp.media = {"filename": file.filename, "type": file.type}


class JSONFormatter(logging.Formatter):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        lr = logging.LogRecord(None, None, "", 0, "", (), None, None)
        self.default_keys = [key for key in lr.__dict__]

    def extra_data(self, record):
        return {
            key: getattr(record, key)
            for key in record.__dict__
            if key not in self.default_keys
        }

    def format(self, record):
        log_data = {
            "severity": record.levelname,
            "path_name": record.pathname,
            "function_name": record.funcName,
            "message": record.msg,
            **self.extra_data(record),
        }
        return json.dumps(log_data)


logger = logging.getLogger()
handler = logging.StreamHandler()
handler.setFormatter(JSONFormatter())
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)


if __name__ == "__main__":
    """
    cmd:
        http :8000/ping
        http ':8000/api/zh/en?text=hi' uid=neo limit=1 vip=true
    """
    app = falcon.App()
    app.add_route("/ping", Ping())
    app.add_route("/api/{source}/{target}", Classification())
    app.add_route("/api/upload-file", FileUpload())
    api.register(app)

    httpd = simple_server.make_server("localhost", 8000, app)
    httpd.serve_forever()
