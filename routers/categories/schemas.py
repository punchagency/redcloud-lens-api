from typing import List, Optional

from pydantic import BaseModel

from routers.nlq.schemas import MarketplaceProductNigeria


class CatRequest(BaseModel):
    category: Optional[str] = None


class CatResponse(BaseModel):
    category: Optional[str] = None
    results: List[MarketplaceProductNigeria]
