from flask import Flask
from pydantic import BaseModel

from spectree import SpecTree


class Query(BaseModel):
    name: str
    limit: int

    class Config:
        schema_extra = {
            "examples": {
                "test1": {
                    "name": "hello",
                    "limit": 1,
                },
                "test2": {
                    "name": "world",
                    "limit": 2,
                },
            },
            "example": {
                "name": "hello",
                "limit": 5,
            },
        }


app = Flask(__name__)
spec = SpecTree("flask", annotations=True)


@app.route("/", methods=["POST"])
@spec.validate()
def index(json: Query):
    print(json)
    return "msg: ok"


if __name__ == "__main__":
    spec.register(app)
    app.run()
