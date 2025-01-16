from fastapi import APIRouter

from .nlq.nlq_router import router as nlq_router
from .categories.category_router import router as category_router

primary_router = APIRouter()

primary_router.include_router(nlq_router, tags=["nlq"])
primary_router.include_router(category_router, tags=["category"])
