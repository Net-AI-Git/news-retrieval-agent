import json
from uuid import uuid4

from fastapi import APIRouter

from ..conts import CORPUS_CHROMA_PATH, FACTS_CHROMA_PATH
from ..orchestration.grounded_answering_workflow import run_grounded_answering
from ..schemas.request import Request
from ..schemas.response import Response


grounded_answering_router = APIRouter(prefix="/grounded-answering", tags=["grounded-answering"])


@grounded_answering_router.post("/run", summary="Grounded Answering", response_model=Response)
def grounded_answering(body: Request):
    flow_id = str(uuid4())
    task_data = {"question": body.content, "facts_chroma_path": FACTS_CHROMA_PATH, "corpus_chroma_path": CORPUS_CHROMA_PATH}
    return Response(content=json.dumps(run_grounded_answering(task_data, flow_id), ensure_ascii=False), flow_id=flow_id, trace_id=task_data.get("trace_id"))
