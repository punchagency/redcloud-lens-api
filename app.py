# File: main.py

import json
import os
from typing import List, Optional

from dotenv import load_dotenv
from fastapi import APIRouter, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
from pydantic import BaseModel
from rich.console import Console
from sqlalchemy import text

from db import engine

# Load environment variables
load_dotenv()

# Initialize OpenAI client
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY", None))

# Logger
console = Console()

# FastAPI App Configuration
app = FastAPI(
    swagger_ui_parameters={"syntaxHighlight": False},
    title="RedCloud Lens Natural Lang Query API",
    description="RedCloud Lens Natural Lang Query API helps you do awesome stuff. 🚀",
    summary="Deadpool's favorite app. Nuff said.",
    version="0.0.1",
    terms_of_service="http://example.com/terms/",
    contact={
        "name": "RedCloud Lens Natural Lang Query API",
        "url": "http://x-force.example.com/contact/",
        "email": "dp@x-force.example.com",
    },
    license_info={
        "name": "Apache 2.0",
        "url": "https://www.apache.org/licenses/LICENSE-2.0.html",
    },
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Router
router = APIRouter()


# Models
class NLQRequest(BaseModel):
    query: Optional[str] = None
    product_name: Optional[str] = None


class ProductCat(BaseModel):
    Column1: Optional[int] = None
    SKU: Optional[str] = None
    ProductName: Optional[str] = None
    TopCategory: Optional[str] = None
    CategoryName: Optional[str] = None
    Country: Optional[str] = None
    Brand: Optional[str] = None
    ProductPrice: Optional[float] = None


class NLQResponse(BaseModel):
    query: Optional[str] = None
    results: List[ProductCat]


class Text2SQL(BaseModel):
    sql_query: str
    # natural_query: str


# Helper: Build query context
def build_context(natural_query: str, product_name: Optional[str]) -> str:
    product_ctxt = (
        f"for product with at least a word from '{product_name}' in their name (case insensitive)"
        if product_name
        else ""
    )
    return f"""
        You are an expert Text2SQL AI in the e-commerce domain 
        that takes a natural language query and translates it into a MYSQL query. 
        Translate the query into a MYSQL query {product_ctxt} in the database schema:
        `products_cats_v2` (
            `Column1` int DEFAULT NULL,
            `SKU` varchar(50) DEFAULT NULL,
            `ProductName` text,
            `TopCategory` varchar(50) DEFAULT NULL,
            `CategoryName` varchar(50) DEFAULT NULL,
            `Country` varchar(50) DEFAULT NULL,
            `Brand` varchar(50) DEFAULT NULL,
            `ProductPrice` double DEFAULT NULL
        ) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci
        Your response should be formatted in the given structure 
        where sql_query is the translated mysql query. 
        Favor OR operations over AND operations.
    """


# Helper: Parse natural language query
def parse_query(
    natural_query: Optional[str], product_name: Optional[str]
) -> Optional[str]:
    if not natural_query and not product_name:
        return None

    context = build_context(natural_query or f"find {product_name}", product_name)

    completion = client.beta.chat.completions.parse(
        model="gpt-4o-2024-08-06",
        messages=[
            {"role": "system", "content": context},
            {"role": "user", "content": natural_query or ""},
        ],
        response_format=Text2SQL,
    )

    try:
        extracted_data = json.loads(completion.choices[0].message.content)
        console.log(extracted_data)
        return extracted_data.get("sql_query")
    except (KeyError, json.JSONDecodeError) as e:
        console.log(f"Error parsing query: {e}")
        return None


# Endpoint: Natural Language Query
@router.post(
    "/nlq",
    response_model=NLQResponse,
    responses={
        200: {"description": "Query processed successfully."},
        400: {"description": "Bad request, invalid or empty query."},
        500: {"description": "Internal server error."},
    },
    summary="Natural Language Query",
    description="Process a natural language query to fetch matching products from the database.",
    tags=["Natural Language Query"],
)
async def nlq_endpoint(request: NLQRequest, limit: int = 10):
    if limit <= 0:
        raise HTTPException(status_code=400, detail="Limit must be greater than zero.")

    natural_query = request.query.strip() if request.query else None
    product_name = request.product_name.strip() if request.product_name else None

    try:
        sql_query = parse_query(natural_query, product_name)
        if not sql_query:
            raise HTTPException(
                status_code=400, detail="No valid filters identified from query."
            )

        sql_query = f"{sql_query.rstrip(';')} LIMIT :limit"
        with engine.connect() as connection:
            result = connection.execute(text(sql_query), {"limit": limit})
            rows = [dict(row._mapping) for row in result]

        return {"query": natural_query, "results": rows}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Endpoint: Fetch sample products
@router.get("/")
async def fetch_products():
    try:
        sql_query = "SELECT ProductName FROM Products LIMIT 10"
        with engine.connect() as connection:
            result = connection.execute(text(sql_query))
            rows = [dict(row._mapping) for row in result]

        return {"results": rows}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Include router
app.include_router(router, prefix="/api")
