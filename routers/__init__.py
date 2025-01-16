from fastapi import APIRouter

from .nlq.nlq_router import router as nlq_router

primary_router = APIRouter()

primary_router.include_router(nlq_router, tags=["nlq"])
