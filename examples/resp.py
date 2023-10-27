from typing import List, Union

from flask import Flask, make_response
from pydantic import BaseModel

from spectree import Response, SpecTree


class AppError(BaseModel):
    message: str


class User(BaseModel):
    user_id: int


class UserResponse(BaseModel):
    __root__: Union[List[User], AppError]


class StrDict(BaseModel):
    __root__: dict[str, str]


spec = SpecTree("flask")
# spec = SpecTree("falcon")
app = Flask(__name__)


@app.route("/ping")
@spec.validate(resp=Response(HTTP_200=StrDict))
def ping():
    resp = make_response({"msg": "pong"}, 203)
    resp.set_cookie(key="pub", value="abcdefg")
    return resp


@app.route("/users")
@spec.validate(resp=Response(HTTP_200=UserResponse))
def get_users():
    return [User(user_id=1), User(user_id=2)]


class UserResource:
    @spec.validate(resp=Response(HTTP_200=UserResponse))
    def on_get(self, req, resp):
        resp.media = [User(user_id=0)]


if __name__ == "__main__":
    spec.register(app)
    app.run()

    # app = falcon.App()
    # app.add_route("/users", UserResource())
    # spec.register(app)

    # httpd = simple_server.make_server("localhost", 8000, app)
    # httpd.serve_forever()
