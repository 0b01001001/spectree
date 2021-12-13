import json
import logging
from random import random
from wsgiref import simple_server

import falcon
from pydantic import BaseModel, Field

from spectree import Response, SpecTree, Tag, models

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger()


api = SpecTree(
    "falcon",
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
    content_length: int


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

    @api.validate(form_data=File, resp=Response(HTTP_200=FileResp), tags=["file-upload"])
    def on_post(self, req, resp):
        """
        post multipart/form-data demo

        demo for 'form_data'
        """
        file_data = req.context.form_data.file
        resp.media = {"filename": file_data.filename, "content_length": file_data.content_length}


if __name__ == "__main__":
    app = falcon.API()
    app.add_route("/ping", Ping())
    app.add_route("/api/{source}/{target}", Classification())
    app.add_route("/api/upload-file", FileUpload())
    api.register(app)

    httpd = simple_server.make_server("localhost", 8000, app)
    print("Swagger documentation: http://localhost:8000/apidoc/swagger\n"
          "Redoc documentation: http://localhost:8000/apidoc/redoc")
    httpd.serve_forever()
    """
    Привет!
    Попытался сделать поддержку загрузки файлов через Swagger, и у меня даже кое-как получилось, но в силу своей
    неопытности у меня появилось много проблем и вопросов:
    Проблемы:
    Поменять тип поля в pydantic получилось только с помощью Field(type='file').
    
    Вопросы:
    1. Как динамически понять тип данных ожидаемого запроса в функции "parse_request" (для генерации соответсвующей формы в Swagger/Redoc)?
    К примеру, в модуле 'drf-yasg' они парсят объекты класса if view explicitly sets its parser classes to include only form parsers
    [Ссылка](https://github.com/axnsan12/drf-yasg/blob/master/src/drf_yasg/utils.py#L366)
    2. Возможно ли понять "content_length" потока данных без его считывания? Нужен ли вообще этот параметр ?
    3. Если файл слишком большой, куда его сохранять во время валидации? BufferIO, TemporaryFile ?
    """
