import json
import os
from datetime import datetime
from typing import List, Optional

from dotenv import load_dotenv
from fastapi import APIRouter, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
from pydantic import BaseModel
from rich.console import Console
from sqlalchemy import text

from db import engine

description = """
RedCloud Lens Natural Lang Query API helps you do awesome stuff. 🚀

"""

load_dotenv()

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY", None))

console = Console()


origins = [
    "http://localhost.tiangolo.com",
    "https://localhost.tiangolo.com",
    "http://localhost",
    "http://localhost:8080",
]


# Initialize FastAPI app
app = FastAPI(
    swagger_ui_parameters={"syntaxHighlight": False},
    title="RedCloud Lens Natural Lang Query API",
    description=description,
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

router = APIRouter()


# Request payload schema
class NLQRequest(BaseModel):
    query: Optional[str] = None
    product_name: Optional[str] = None


class Product(BaseModel):
    ProductID: int
    Country: Optional[str] = None
    SKU: Optional[str] = None
    Brand: Optional[str] = None
    Manufacturer: Optional[str] = None
    Brand_Manufacturer: Optional[str] = None
    ProductCreationDate: Optional[datetime] = None
    ProductStatus: Optional[str] = None
    ProductName: Optional[str] = None
    ProductPrice: Optional[float] = None
    Quantity: Optional[int] = None
    StockStatus: Optional[str] = None
    SalableQuantity: Optional[int] = None
    CategoryName: Optional[str] = None
    TopCategory: Optional[str] = None
    SellerID: Optional[int] = None
    SellerGroup: Optional[str] = None
    SellerName: Optional[str] = None
    HSRecordID: Optional[int] = None
    LastPriceUpdateAt: Optional[datetime] = None


class ProductCat(BaseModel):
    ProductName: Optional[str] = None
    TopCategory: Optional[str] = None
    Category: Optional[str] = None
    Country: Optional[str] = None
    Brand: Optional[str] = None


class Text2SQL(BaseModel):
    sql_query: str
    # natural_query: str


class NLQResponse(BaseModel):
    query: Optional[str] = None
    results: List[ProductCat]


# Helper function to parse natural language query
def parse_query(natural_query: str = None, product_name: str = None):
    if not natural_query and not product_name:
        return None

    if natural_query and product_name:

        product_ctxt = (
            f"for product with at least a word from '{product_name}' in their name (case insensitive)"
        )
        context = f"""
        You are an expert Text2SQL AI in the e-commerce domain 
        that takes a natural language query and translates it into a MYSQL query. 
        You will be given a Natural Language Query and 
        should translate it into MYSQL query {product_ctxt if product_name else ''} in the following database schema:
        `products_cats` (
            `ProductName` text,
            `TopCategory` text,
            `Category Name` text,
            `Country` text,
            `Brand` text
        ) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci
        
        Your response should be formatted in the given structure 
        where sql_query is the translated mysql query. 
        Favor OR operations over AND operations.
        """

    if natural_query and not product_name:

        product_ctxt = (
            f"for product with at least a word from '{product_name}' in their name (case insensitive)"
        )
        context = f"""
        You are an expert Text2SQL AI in the e-commerce domain 
        that takes a natural language query and translates it into a MYSQL query. 
        You will be given a Natural Language Query and 
        should translate it into MYSQL query {product_ctxt if product_name else ''} in the following database schema:
        `products_cats` (
            `ProductName` text,
            `TopCategory` text,
            `Category Name` text,
            `Country` text,
            `Brand` text
        ) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci
        
        Your response should be formatted in the given structure 
        where sql_query is the translated mysql query. 
        Favor OR operations over AND operations.
        """

    if not natural_query and product_name:

        product_ctxt = (
            f"for product with at least a word from '{product_name}' in their name (case insensitive)"
        )
        natural_query = (
            f"find product with at least a word from {product_name} in their name (case insensitive)"
        )
        context = f"""
        You are an expert Text2SQL AI in the e-commerce domain 
        that takes a natural language query and translates it into a MYSQL query. 
        You will be given a Natural Language Query and 
        should translate it into MYSQL query {product_ctxt if product_name else ''} in the following database schema:
        `products_cats` (
            `ProductName` text,
            `TopCategory` text,
            `Category Name` text,
            `Country` text,
            `Brand` text
        ) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci
        
        Your response should be formatted in the given structure 
        where sql_query is the translated mysql query. 
        Favor OR operations over AND operations.
        """

    # Get gender prediction for each name
    completion = client.beta.chat.completions.parse(
        model="gpt-4o-2024-08-06",
        messages=[
            {
                "role": "system",
                "content": context,
            },
            {"role": "user", "content": natural_query},
        ],
        response_format=Text2SQL,
    )

    extracted_data = completion.choices[0].message.content
    extracted_data = json.loads(extracted_data)

    console.log(extracted_data)
    return extracted_data.get("sql_query", None)


# NLQ endpoint
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
async def nlq_endpoint(request: NLQRequest, limit: Optional[int] = 10):

    natural_query = request.query.strip() if request.query else None
    product_name = request.product_name.strip() if request.product_name else None
    # if not natural_query:
    #     raise HTTPException(status_code=400, detail="Query cannot be empty.")
    if limit <= 0:
        raise HTTPException(status_code=400, detail="Limit must be greater than zero.")

    # Parse query and construct SQL
    try:
        sql_filters = parse_query(natural_query, product_name=product_name)
        if not sql_filters:
            raise HTTPException(
                status_code=400, detail="No valid filters identified from query."
            )

        # Add LIMIT as a parameterized value in the SQL query
        sql_filters = sql_filters.rstrip(";")
        sql_query = f"{sql_filters} LIMIT :limit"

        # Execute the SQL query with the `limit` parameter passed explicitly
        with engine.connect() as connection:
            result = connection.execute(text(sql_query), {"limit": limit})
            rows = [dict(row._mapping) for row in result]

        # Return results
        return {"query": natural_query, "results": rows}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/")
async def nlq():
    try:
        sql_query = "SELECT ProductName FROM Products LIMIT 10"

        # Execute SQL query
        with engine.connect() as connection:
            result = connection.execute(text(sql_query))
            rows = [dict(row._mapping) for row in result]

        # Return results
        return {"results": rows}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


app.include_router(router, prefix="/api")
