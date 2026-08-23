from uuid import uuid4

from fastapi import APIRouter

from ..schemas.request import Request
from ..schemas.response import Response
from ..services.example_feature_service import run_example_feature


example_router = APIRouter(prefix="/example", tags=["Example"])
secondary_router = APIRouter(prefix="/secondary", tags=["Secondary"])


@example_router.post("/run", summary="Example Feature", response_model=Response)
def example_feature(body: Request):
    flow_id = str(uuid4())
    return Response(content=run_example_feature({"content": body.content}, flow_id))


@secondary_router.post("/run", summary="Secondary Feature", response_model=Response)
def secondary_feature(body: Request):
    flow_id = str(uuid4())
    return Response(content=run_example_feature({"content": body.content}, flow_id))
