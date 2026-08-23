from fastapi import APIRouter

from . import example_feature, ping


api_router = APIRouter()

api_router.include_router(ping.router)
api_router.include_router(example_feature.example_router)
api_router.include_router(example_feature.secondary_router)
