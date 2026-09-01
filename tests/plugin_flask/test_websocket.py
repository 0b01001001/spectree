import pytest
from flask import Flask

from spectree import SpecTree
from spectree.model_adapter import get_pydantic_model_adapter
from tests.common_dataclass import RequiredLimitQuery


@pytest.mark.pydantic
def test_flask_websocket_route_bypasses_http_validation():
    app = Flask(__name__)
    hook_calls = []
    api = SpecTree(
        "flask",
        before=lambda *_args: hook_calls.append("before"),
        after=lambda *_args: hook_calls.append("after"),
        model_adapter=get_pydantic_model_adapter(),
    )

    @app.route("/socket", websocket=True)
    @api.validate(query=RequiredLimitQuery)
    def socket():
        return "socket"

    with app.test_client() as client:
        response = client.get("/socket", base_url="ws://localhost")

    assert response.status_code == 200
    assert response.text == "socket"
    assert hook_calls == []
