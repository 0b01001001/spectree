from flask import Flask, jsonify
from flask.views import MethodView
from pydantic import BaseModel

from spectree import SpecTree

app = Flask(__name__)
spec = SpecTree("flask", annotations=True)


class User(BaseModel):
    name: str
    token: str


class Login(MethodView):
    @spec.validate()
    def post(self, json: User):
        print(json)
        return jsonify({"msg": "success"})


if __name__ == "__main__":
    app.add_url_rule("/login", view_func=Login.as_view("login"))
    app.run(debug=True)
