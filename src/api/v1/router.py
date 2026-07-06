from fastapi import APIRouter
from src.api.v1.auth import router as auth_router
from src.api.v1.review import router as review_router
from src.api.v1.config import router as config_router

api_v1_router = APIRouter(prefix="/api/v1")
api_v1_router.include_router(auth_router)
api_v1_router.include_router(review_router)
api_v1_router.include_router(config_router)
