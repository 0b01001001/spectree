import uvicorn
from starlette.applications import Starlette
from starlette.routing import Route
from starlette.responses import JSONResponse
from pydantic import BaseModel, Field

from spectree import SpecTree, Response


api = SpecTree('starlette')


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


@api.validate(query=Query, json=Data, resp=Response(HTTP_200=Resp), tags=['api'])
async def predict(request):
    """
    async api

    descriptions about this function
    """
    print(request.path_params)
    print(request.context)
    return JSONResponse({'label': 5, 'score': 0.5})


@api.validate(tags=['health check', 'api'])
def ping(request):
    """
    health check
    """
    return JSONResponse({'msg': 'pong'})


if __name__ == "__main__":
    app = Starlette(routes=[
        Route('/ping', ping),
        Route('/api/predict/{luck:int}', predict),
    ])
    api.register(app)

    uvicorn.run(app, log_level='info')
