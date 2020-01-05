from random import randint
import pytest
import falcon
from falcon import testing

from spectree import SpecTree, Response

from .common import Query, Resp, JSON, UpperHeaders, Cookies


api = SpecTree('falcon')


class Ping:
    @api.validate(headers=UpperHeaders, tags=['test', 'health'])
    def on_get(self, req, resp):
        resp.media = {'msg': 'pong'}


class UserScore:
    @api.validate(
        query=Query,
        json=JSON,
        cookies=Cookies,
        resp=Response('HTTP_401', HTTP_200=Resp),
        tags=['api', 'test'])
    def on_post(self, req, resp, name):
        score = [randint(0, req.context.json.limit) for _ in range(5)]
        score.sort(reverse=req.context.query.order)
        assert req.context.cookies.pub == 'abcdefg'
        resp.media = {'name': req.context.json.name, 'score': score}


app = falcon.API()
app.add_route('/ping', Ping())
app.add_route('/api/user/{name}', UserScore())
api.register(app)


@pytest.fixture
def client():
    return testing.TestClient(app)


def test_falcon_validate(client):
    resp = client.simulate_request('GET', '/ping')
    assert resp.status_code == 422

    resp = client.simulate_request('GET', '/ping', headers={'LANG': 'en-US'})
    assert resp.json == {'msg': 'pong'}

    resp = client.simulate_request('POST', '/api/user/falcon')
    assert resp.status_code == 422

    resp = client.simulate_request(
        'POST',
        '/api/user/falcon?order=1',
        json=dict(name='falcon', limit=10),
        headers={'Cookie': 'pub=abcdefg'},
    )
    assert resp.json['name'] == 'falcon'
    assert resp.json['score'] == sorted(resp.json['score'], reverse=1)

    resp = client.simulate_request(
        'POST',
        '/api/user/falcon?order=0',
        json=dict(name='falcon', limit=10),
        headers={'Cookie': 'pub=abcdefg'},
    )
    assert resp.json['name'] == 'falcon'
    assert resp.json['score'] == sorted(resp.json['score'], reverse=0)


def test_falcon_doc(client):
    resp = client.simulate_get('/apidoc/openapi.json')
    assert resp.json == api.spec

    resp = client.simulate_get('/apidoc/redoc')
    assert resp.status_code == 200

    resp = client.simulate_get('/apidoc/swagger')
    assert resp.status_code == 200
