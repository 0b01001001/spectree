from http import HTTPStatus
from io import BytesIO

import msgspec
import pytest
from flask import Flask
from flask.testing import FlaskClient

from spectree import Response as SpecResponse
from spectree import SpecTree
from spectree.model_adapter import get_msgspec_model_adapter
from spectree.model_adapter.msgspec_adapter import BaseFile

pytestmark = pytest.mark.msgspec

model_adapter = get_msgspec_model_adapter()
spec = SpecTree("flask", model_adapter=model_adapter)
app = Flask(__name__)


class Query(msgspec.Struct):
    text: str


class Resp(msgspec.Struct):
    num: int


class FormFileUpload(msgspec.Struct):
    file: BaseFile
    other: str


@app.route("/query", methods=["POST"])
@spec.validate()
def query(json: Query, form: Query):
    src = json or form
    return {"input": src.text}


@app.route("/resp")
@spec.validate(resp=SpecResponse(HTTP_200=Resp))
def resp(query: Query):
    if not query.text:
        return {}
    return {"num": len(query.text)}


@app.route("/file", methods=["POST"])
@spec.validate()
def file_upload(form: FormFileUpload):
    upload = form.file
    return {"content": upload.stream.read().decode("utf-8"), "other": form.other}


with app.app_context():
    _ = spec.spec
spec.register(app)


@pytest.fixture
def client():
    with app.test_client() as client:
        yield client


def test_post_with_json_and_form(client: FlaskClient):
    # json
    resp = client.post("/query", json={"text": "hi"}, content_type="application/json")
    assert resp.status_code == HTTPStatus.OK
    assert resp.json["input"] == "hi"  # type: ignore

    # form
    resp = client.post(
        "/query", data={"text": "hi"}, content_type="application/x-www-form-urlencoded"
    )
    assert resp.status_code == HTTPStatus.OK
    assert resp.json["input"] == "hi"  # type: ignore


def test_resp_validation(client: FlaskClient):
    resp = client.get("/resp?text=1")
    assert resp.status_code == HTTPStatus.OK
    assert resp.json["num"] == 1  # type: ignore

    resp = client.get("/resp?text=")
    assert resp.status_code == HTTPStatus.INTERNAL_SERVER_ERROR


def test_upload_file(client: FlaskClient):
    content = "abcdef"
    other = "test"
    data = {
        "file": (BytesIO(content.encode("utf-8")), "test.txt"),
        "other": other,
    }
    resp = client.post("/file", data=data, content_type="multipart/form-data")
    assert resp.status_code == HTTPStatus.OK
    assert resp.json["content"] == content  # type: ignore
    assert resp.json["other"] == other  # type: ignore
