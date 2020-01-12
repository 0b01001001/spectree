import falcon
from wsgiref import simple_server
from pydantic import BaseModel, Field
from random import random

from spectree import SpecTree, Response


api = SpecTree(
    'falcon',
    title='Demo Service',
    version='0.1.2',
)


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

    @api.validate(tags=['demo'])
    def on_get(self, req, resp):
        """
        health check
        """
        self.check()
        resp.media = {'msg': 'pong'}


class Classification:
    """
    classification demo
    """
    @api.validate(tags=['demo'])
    def on_get(self, req, resp, source, target):
        """
        API summary

        description here: test information with `source` and `target`
        """
        resp.media = {'msg': f'hello from {source} to {target}'}

    @api.validate(query=Query, json=Data, resp=Response(HTTP_200=Resp, HTTP_403=BadLuck))
    def on_post(self, req, resp, source, target):
        """
        post demo

        demo for `query`, `data`, `resp`, `x`
        """
        print(f'{source} => {target}')
        print(req.context.query)
        print(req.context.media)
        if random() < 0.5:
            resp.status = falcon.HTTP_403
            resp.media = {'loc': 'unknown', 'msg': 'bad luck', 'typ': 'random'}
            return
        resp.media = {'label': int(10 * random()), 'score': random()}


if __name__ == '__main__':
    app = falcon.API()
    app.add_route('/ping', Ping())
    app.add_route('/api/{source}/{target}', Classification())
    api.register(app)

    httpd = simple_server.make_server('localhost', 8000, app)
    httpd.serve_forever()
