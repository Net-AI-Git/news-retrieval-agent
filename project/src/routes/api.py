from fastapi import APIRouter

from . import chroma_index, example_feature, ping


api_router = APIRouter()

api_router.include_router(ping.router)
api_router.include_router(chroma_index.corpus_chroma_index_router)
api_router.include_router(chroma_index.facts_chroma_index_router)
api_router.include_router(example_feature.example_router)
api_router.include_router(example_feature.secondary_router)
