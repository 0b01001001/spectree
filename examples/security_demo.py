from flask import Flask
from pydantic import BaseModel

from spectree import SecurityScheme, SpecTree


class Req(BaseModel):
    name: str


security_schemes = [
    SecurityScheme(
        name="PartnerID",
        data={"type": "apiKey", "name": "partner-id", "in": "header"},
    ),
    SecurityScheme(
        name="PartnerToken",
        data={"type": "apiKey", "name": "partner-access-token", "in": "header"},
    ),
    SecurityScheme(
        name="test_secure",
        data={
            "type": "http",
            "scheme": "bearer",
        },
    ),
    SecurityScheme(
        name="auth_oauth2",
        data={
            "type": "oauth2",
            "flows": {
                "authorizationCode": {
                    "authorizationUrl": "https://example.com/oauth/authorize",
                    "tokenUrl": "https://example.com/oauth/token",
                    "scopes": {
                        "read": "Grants read access",
                        "write": "Grants write access",
                        "admin": "Grants access to admin operations",
                    },
                },
            },
        },
    ),
]

app = Flask(__name__)
api = SpecTree(
    "flask",
    security_schemes=security_schemes,
    SECURITY={"test_secure": []},
)


@app.route("/ping", methods=["POST"])
@api.validate(
    json=Req,
    security=[{"PartnerID": [], "PartnerToken": []}, {"auth_oauth2": ["read"]}],
)
def ping():
    return "pong"


@app.route("/")
def index():
    return "hello"


if __name__ == "__main__":
    api.register(app)
    app.run(port=8000)
