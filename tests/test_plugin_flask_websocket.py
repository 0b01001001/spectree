from flask import Flask
from pydantic import BaseModel

from spectree import SpecTree


class RequiredQuery(BaseModel):
    limit: int


def test_flask_websocket_route_bypasses_http_validation():
    app = Flask(__name__)
    hook_calls = []
    api = SpecTree(
        "flask",
        before=lambda *_args: hook_calls.append("before"),
        after=lambda *_args: hook_calls.append("after"),
    )

    @app.route("/socket", websocket=True)
    @api.validate(query=RequiredQuery)
    def socket():
        return "socket"

    with app.test_client() as client:
        response = client.get("/socket", base_url="ws://localhost")

    assert response.status_code == 200
    assert response.text == "socket"
    assert hook_calls == []
