from uuid import uuid4

from fastapi import APIRouter

from ..conts import CORPUS_CHROMA_PATH, DATA_DIR, FACTS_CHROMA_PATH
from ..schemas.response import Response
from ..services.corpus_chroma_index_service import run_corpus_chroma_index
from ..services.facts_chroma_index_service import run_facts_chroma_index


corpus_chroma_index_router = APIRouter(prefix="/corpus-chroma-index", tags=["corpus-chroma-index"])
facts_chroma_index_router = APIRouter(prefix="/facts-chroma-index", tags=["facts-chroma-index"])


@corpus_chroma_index_router.post("/run", summary="Corpus Chroma Index", response_model=Response)
def corpus_chroma_index():
    flow_id = str(uuid4())
    return Response(content=run_corpus_chroma_index({"data_dir": DATA_DIR, "chroma_path": CORPUS_CHROMA_PATH}, flow_id) or "")


@facts_chroma_index_router.post("/run", summary="Facts Chroma Index", response_model=Response)
def facts_chroma_index():
    flow_id = str(uuid4())
    return Response(content=run_facts_chroma_index({"data_dir": DATA_DIR, "chroma_path": FACTS_CHROMA_PATH}, flow_id) or "")
