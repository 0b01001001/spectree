from flask import Flask
from pydantic import BaseModel

from spectree import (
    SecurityScheme,
    SecuritySchemeData,
    SpecTree,
    get_pydantic_model_adapter,
)

model_adapter = get_pydantic_model_adapter()


class Req(BaseModel):
    name: str


security_schemes = [
    SecurityScheme(
        name="PartnerID",
        data=SecuritySchemeData.model_validate(
            {"type": "apiKey", "name": "partner-id", "in": "header"},
            model_adapter=model_adapter,
        ),
    ),
    SecurityScheme(
        name="PartnerToken",
        data=SecuritySchemeData.model_validate(
            {"type": "apiKey", "name": "partner-access-token", "in": "header"},
            model_adapter=model_adapter,
        ),
    ),
    SecurityScheme(
        name="test_secure",
        data=SecuritySchemeData.model_validate(
            {
                "type": "http",
                "scheme": "bearer",
            },
            model_adapter=model_adapter,
        ),
    ),
    SecurityScheme(
        name="auth_oauth2",
        data=SecuritySchemeData.model_validate(
            {
                "type": "oauth2",
                "flows": {
                    "authorizationCode": {
                        "authorizationUrl": (
                            "https://accounts.google.com/o/oauth2/v2/auth"
                        ),
                        "tokenUrl": "https://sts.googleapis.com",
                        "scopes": {
                            "https://www.googleapis.com/auth/tasks.readonly": "tasks",
                        },
                    },
                },
            },
            model_adapter=model_adapter,
        ),
    ),
]

app = Flask(__name__)
spec = SpecTree(
    "flask",
    security_schemes=security_schemes,
    SECURITY=[
        {"test_secure": []},
        {"PartnerID": [], "PartnerToken": []},
    ],
    client_id="client_id",
)


@app.route("/ping", methods=["POST"])
@spec.validate()
def ping(json: Req):
    return "pong"


@app.route("/ping/oauth", methods=["POST"])
@spec.validate(security=[{"auth_oauth2": ["read"]}])
def oauth_only(json: Req):
    return "pong"


@app.route("/")
def index():
    return "hello"


if __name__ == "__main__":
    spec.register(app)
    app.run(port=8000)
