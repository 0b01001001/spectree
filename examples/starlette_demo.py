import uvicorn
from pydantic import BaseModel, Field
from starlette.applications import Starlette
from starlette.endpoints import HTTPEndpoint
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route

from spectree import Response, SpecTree

# from spectree.plugins.starlette_plugin import PydanticResponse

api = SpecTree("starlette")


class Query(BaseModel):
    text: str


class Resp(BaseModel):
    label: int = Field(
        ...,
        ge=0,
        le=9,
    )
    score: float = Field(
        ...,
        gt=0,
        lt=1,
    )


class Data(BaseModel):
    uid: str
    limit: int
    vip: bool


@api.validate(query=Query, json=Data, resp=Response(HTTP_200=Resp), tags=["api"])
async def predict(request):
    """
    async api

    descriptions about this function
    """
    print(request.path_params)
    print(request.context)
    return JSONResponse({"label": 5, "score": 0.5})
    # return PydanticResponse(Resp(label=5, score=0.5))


class Ping(HTTPEndpoint):
    @api.validate(tags=["health check", "api"])
    def get(self, request):
        """
        health check
        """
        return JSONResponse({"msg": "pong"})


if __name__ == "__main__":
    """
    cmd:
        http :8000/ping
        http ':8000/api/predict/233?text=hello' vip=true uid=admin limit=1
    """
    app = Starlette(
        routes=[
            Route("/ping", Ping),
            Mount(
                "/api", routes=[Route("/predict/{luck:int}", predict, methods=["POST"])]
            ),
        ]
    )
    api.register(app)

    uvicorn.run(app, log_level="info")
