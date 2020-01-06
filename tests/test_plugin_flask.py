from random import randint
import pytest
import json
from flask import Flask, jsonify, request

from spectree import SpecTree, Response

from .common import Query, Resp, JSON, Headers, Cookies


api = SpecTree('flask')
app = Flask(__name__)


@app.route('/ping')
@api.validate(headers=Headers, tags=['test', 'health'])
def ping():
    return jsonify(msg='pong')


@app.route('/api/user/<name>', methods=['POST'])
@api.validate(
    query=Query,
    json=JSON,
    cookies=Cookies,
    resp=Response('HTTP_401', HTTP_200=Resp),
    tags=['api', 'test'])
def user_score(name):
    score = [randint(0, request.context.json.limit) for _ in range(5)]
    score.sort(reverse=request.context.query.order)
    assert request.context.cookies.pub == 'abcdefg'
    return jsonify(name=request.context.json.name, score=score)


api.register(app)


@pytest.fixture
def client():
    with app.test_client() as client:
        yield client


def test_flask_validate(client):
    resp = client.get('/ping')
    assert resp.status_code == 422

    resp = client.get('/ping', headers={'lang': 'en-US'})
    assert resp.json == {'msg': 'pong'}

    resp = client.post('api/user/flask')
    assert resp.status_code == 422

    client.set_cookie('flask', 'pub', 'abcdefg')
    resp = client.post(
        '/api/user/flask?order=1',
        data=json.dumps(dict(name='flask', limit=10)),
        content_type='application/json',
    )
    assert resp.json['name'] == 'flask'
    assert resp.json['score'] == sorted(resp.json['score'], reverse=1)

    resp = client.post(
        '/api/user/flask?order=0',
        data=json.dumps(dict(name='flask', limit=10)),
        content_type='application/json',
    )
    assert resp.json['score'] == sorted(resp.json['score'], reverse=0)


def test_flask_doc(client):
    resp = client.get('/apidoc/openapi.json')
    assert resp.json == api.spec

    resp = client.get('/apidoc/redoc')
    assert resp.status_code == 200

    resp = client.get('/apidoc/swagger')
    assert resp.status_code == 200
