from typing import List, Optional

from pydantic import BaseModel

from routers.nlq.schemas import MarketplaceProductNigeria


class CategoryRequest(BaseModel):
    category: Optional[str] = None
    country: Optional[str] = "Nigeria"


class CategoryResponse(BaseModel):
    category: Optional[str] = None
    results: List[MarketplaceProductNigeria]
