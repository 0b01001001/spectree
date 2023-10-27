from typing import List, Union

from flask import Flask, jsonify, request
from pydantic.v1 import BaseModel, Field

from spectree import SpecTree


class SampleQueryParams(BaseModel):
    id_list: Union[int, List[int]] = Field(..., description="List of IDs")


app = Flask(__name__)
spec = SpecTree("flask")


@app.route("/api/v1/samples", methods=["GET"])
@spec.validate(query=SampleQueryParams)
def get_samples():
    return jsonify(text=f"it works: {request.context.query}")


if __name__ == "__main__":
    spec.register(app)  # if you don't register in api init step
    app.run(port=8000)
