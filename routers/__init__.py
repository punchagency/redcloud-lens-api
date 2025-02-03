from fastapi import APIRouter

from .nlq.nlq_router import router as nlq_router
from .whatsapp.whatsapp_router import router as whatsapp_router

primary_router = APIRouter()

primary_router.include_router(nlq_router, tags=["nlq"])
primary_router.include_router(whatsapp_router, tags=["whatsapp"])
