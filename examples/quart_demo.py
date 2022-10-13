from enum import Enum
from random import random

from pydantic import BaseModel, Field
from quart import Quart, abort, jsonify, request
from quart.views import MethodView

from spectree import Response, SpecTree

app = Quart(__name__)
api = SpecTree("quart")


class Query(BaseModel):
    text: str = "default query strings"


class Resp(BaseModel):
    label: int
    score: float = Field(
        ...,
        gt=0,
        lt=1,
    )


class Data(BaseModel):
    uid: str
    limit: int = 5
    vip: bool

    class Config:
        schema_extra = {
            "example": {
                "uid": "very_important_user",
                "limit": 10,
                "vip": True,
            }
        }


class Language(str, Enum):
    en = "en-US"
    zh = "zh-CN"


class Header(BaseModel):
    Lang: Language


class Cookie(BaseModel):
    key: str


@app.route(
    "/api/predict/<string(length=2):source>/<string(length=2):target>", methods=["POST"]
)
@api.validate(
    query=Query, json=Data, resp=Response("HTTP_403", HTTP_200=Resp), tags=["model"]
)
def predict(source, target):
    """
    predict demo

    demo for `query`, `data`, `resp`, `x`

    query with
    ``http POST ':8000/api/predict/zh/en?text=hello' uid=xxx limit=5 vip=false ``
    """
    print(f"=> from {source} to {target}")  # path
    print(f"JSON: {request.json}")  # Data
    print(f"Query: {request.args}")  # Query
    if random() < 0.5:
        abort(403)

    return jsonify(label=int(10 * random()), score=random())


@app.route("/api/header", methods=["POST"])
@api.validate(
    headers=Header, cookies=Cookie, resp=Response("HTTP_203"), tags=["test", "demo"]
)
async def with_code_header():
    """
    demo for JSON with status code and header

    query with ``http POST :8000/api/header Lang:zh-CN Cookie:key=hello``
    """
    return jsonify(language=request.headers.get("Lang")), 203, {"X": 233}


class UserAPI(MethodView):
    @api.validate(json=Data, resp=Response(HTTP_200=Resp), tags=["test"])
    async def post(self):
        return jsonify(label=int(10 * random()), score=random())
        # return Resp(label=int(10 * random()), score=random())


if __name__ == "__main__":
    """
    cmd:
        http :8000/api/user uid=12 limit=1 vip=false
        http ':8000/api/predict/zh/en?text=hello' vip=true uid=aa limit=1
        http POST :8000/api/header Lang:zh-CN Cookie:key=hello
    """
    app.add_url_rule("/api/user", view_func=UserAPI.as_view("user_id"))
    api.register(app)
    app.run(port=8000)
