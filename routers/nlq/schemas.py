from datetime import datetime
from typing import List, Literal, Optional, Union

from fastapi import UploadFile
from pydantic import BaseModel, Field


class NLQRequest(BaseModel):
    query: Optional[str] = None
    conversation_id: Optional[str] = None
    product_image: Optional[Union[str, UploadFile]] = None
    country: Optional[str] = "Nigeria"


class CategoryRequest(BaseModel):
    category: str


class MarketplaceProductNigeria(BaseModel):
    brand_or_manufacturer: Optional[str] = Field(None, alias="Brand or Manufacturer")
    external_id: Optional[str] = Field(None, alias="external_id")
    product_id: Optional[int] = Field(None, alias="Product ID")
    country: Optional[str] = Field(None, alias="Country")
    sku: Optional[str] = Field(None, alias="SKU")
    brand: Optional[str] = Field(None, alias="Brand")
    manufacturer: Optional[str] = Field(None, alias="Manufacturer")
    product_creation_date: Optional[datetime] = Field(
        None, alias="Product Creation Date"
    )
    product_status: Optional[str] = Field(None, alias="Product Status")
    product_name: Optional[str] = Field(None, alias="Product Name")
    product_price: Optional[float] = Field(None, alias="Product Price")
    quantity: Optional[float] = Field(None, alias="Quantity")
    stock_status: Optional[str] = Field(None, alias="Stock Status")
    salable_quantity: Optional[float] = Field(None, alias="Salable Quantity")
    category_name: Optional[str] = Field(None, alias="Category Name")
    top_category: Optional[str] = Field(None, alias="Top Category")
    seller_id: Optional[int] = Field(None, alias="Seller ID")
    seller_group: Optional[str] = Field(None, alias="Seller Group")
    seller_name: Optional[str] = Field(None, alias="Seller Name")
    hs_record_id: Optional[str] = Field(None, alias="HS Record ID")
    last_price_update_at: Optional[datetime] = Field(None, alias="Last Price Update At")


class NLQResponse(BaseModel):
    conversation_id: Optional[str] = None
    message: str = "success"
    query: Optional[str] = None
    sql_query: Optional[str] = None
    suggested_queries: Optional[List[str]] = None
    result_analysis: Optional[str] = None
    analytics_queries: Optional[List[str]] = None
    results: List[MarketplaceProductNigeria] = None


class Text2SQL(BaseModel):
    sql_query: str
    suggested_queries: Optional[List[str]]


class DataAnalysis(BaseModel):
    data_summary: str
    suggested_queries: Optional[List[str]]


class QueryRequest(BaseModel):
    query: str
    conversation_id: Optional[str] = None


class QueryResponse(BaseModel):
    conversation_id: Optional[str] = None
    result_analysis: Optional[str] = None
    analytics_queries: Optional[List[str]] = None
    suggested_queries: Optional[List[str]] = None
    result: Optional[List] = None
