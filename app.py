import base64
import json
import os
from datetime import datetime
from typing import List, Optional, Union

from dotenv import load_dotenv
from fastapi import APIRouter, FastAPI, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from google.cloud import bigquery
from openai import OpenAI
from pydantic import BaseModel, Field
from rich.console import Console

# Load environment variables
load_dotenv()

# credentials = service_account.Credentials.from_service_account_file("gcp_conf.json")

bigquery_client = bigquery.Client(project=os.environ.get("GCP_PROJECT_ID", None))

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY", None))

# Logger
console = Console()

# FastAPI App Configuration
app = FastAPI(
    swagger_ui_parameters={"syntaxHighlight": False},
    title="RedCloud Lens Natural Lang Query API",
    description="RedCloud Lens Natural Lang Query API helps you do awesome stuff. 🚀",
    summary="Deadpool's favorite app. Nuff said.",
    version="0.0.2",
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
    product_image: Optional[Union[str, UploadFile]] = None


class ProductCat(BaseModel):
    Column1: Optional[int] = None
    SKU: Optional[str] = None
    ProductName: Optional[str] = None
    TopCategory: Optional[str] = None
    CategoryName: Optional[str] = None
    Country: Optional[str] = None
    Brand: Optional[str] = None
    ProductPrice: Optional[float] = None


class MarketplaceProductNigeria(BaseModel):
    brand_or_manufacturer: Optional[str] = Field(None, alias="Brand or Manufacturer")
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

    class Config:
        populate_by_name = True  # Allow using snake_case in code
        by_alias = False


class NLQResponse(BaseModel):
    query: Optional[str] = None
    results: List[MarketplaceProductNigeria]


class Text2SQL(BaseModel):
    sql_query: str


# Helper: Build query context
def build_context(
    natural_query: str, product_name: Optional[str], total: Optional[int] = 10
) -> str:
    product_ctxt = (
        f"for product with at least a word from '{product_name}' in their name (case insensitive)"
        if product_name
        else ""
    )
    return f"""
        You are an expert Text2SQL AI in the e-commerce domain 
        that takes a natural language query and translates it into a BigQuery SQL query. 
        Translate the query into a BigQuery SQL query {product_ctxt} in the database schema:
        `marketplace_product_nigeria` (
            `Brand or Manufacturer` STRING,
            `Product ID` INTEGER,
            `Country` STRING,
            `SKU` STRING,
            `Brand` STRING,
            `Manufacturer` STRING,
            `Product Creation Date` TIMESTAMP,
            `Product Status` STRING,
            `Product Name` STRING,
            `Product Price` FLOAT,
            `Quantity` FLOAT,
            `Stock Status` STRING,
            `Salable Quantity` FLOAT,
            `Category Name` STRING,
            `Top Category` STRING,
            `Seller ID` INTEGER,
            `Seller Group` STRING,
            `Seller Name` STRING,
            `HS Record ID` STRING,
            `Last Price Update At` TIMESTAMP
        )
        Your response should be formatted in the given structure 
        where sql_query is the translated BigQuery SQL query with a LIMIT of {total}. 
        Favor OR operations over AND operations. Ensure the query select all fields and the query is optimized for BigQuery performance.
    """


# Helper: Parse natural language query
def parse_query(
    natural_query: Optional[str], product_name: Optional[str], amount: Optional[int]
) -> Optional[str]:
    if not natural_query and not product_name:
        return None

    context = build_context(
        natural_query or f"find {product_name}", product_name, total=amount
    )

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


# Helper: Process product image
def process_product_image(image: Union[str, UploadFile]) -> Optional[str]:
    try:
        if isinstance(image, UploadFile):
            content = image.file.read()
            base64_image = base64.b64encode(content).decode("utf-8")
        else:
            base64_image = image  # Assuming it's already a base64 string
        console.log(f"Processed product image: {base64_image[:30]}...")  # Log a snippet
        return base64_image
    except Exception as e:
        console.log(f"Error processing product image: {e}")
        return None


# Endpoint: Natural Language Query
@router.post(
    "/nlq",
    responses={
        200: {"description": "Query processed successfully."},
        400: {"description": "Bad request, invalid or empty query."},
        500: {"description": "Internal server error."},
    },
    response_model=NLQResponse,
    response_model_by_alias=False,
    summary="Natural Language Query",
    description="Process a natural language query to fetch matching products from the database.",
    tags=["Natural Language Query"],
)
async def nlq_endpoint(request: NLQRequest, limit: int = 10):
    if limit <= 0:
        raise HTTPException(status_code=400, detail="Limit must be greater than zero.")

    natural_query = request.query.strip() if request.query else None
    product_name = request.product_name.strip() if request.product_name else None
    product_image = (
        process_product_image(request.product_image) if request.product_image else None
    )

    try:
        sql_query = parse_query(natural_query, product_name, limit)
        if not sql_query:
            raise HTTPException(
                status_code=400, detail="No valid filters identified from query."
            )
        # Configure default dataset in the QueryJobConfig
        default_dataset = "snowflake_views"  # Specify your dataset

        job_config = bigquery.QueryJobConfig(
            default_dataset=f"{bigquery_client.project}.{default_dataset}",
            # dry_run=True
        )
        query_job = bigquery_client.query(sql_query, job_config=job_config)
        # for row in query_job.result():
        #     console.log(row)

        rows = [dict(row) for row in query_job.result()]

        return {"query": natural_query, "results": rows}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Include router
app.include_router(router, prefix="/api")
