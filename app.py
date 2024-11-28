import json
import os
from datetime import datetime
from typing import List, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
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


# Initialize FastAPI app
# app = FastAPI()
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


# Load Flair NER model
# tagger = SequenceTagger.load("ner")


# Request payload schema
class NLQRequest(BaseModel):
    query: str


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


class Text2SQL(BaseModel):
    sql_query: str
    # natural_query: str


class NLQResponse(BaseModel):
    query: str
    results: List[Product]


# Helper function to parse natural language query
def parse_query(natural_query: str):

    context = """
    You are an expert Text2SQL AI in the e-commerce domain 
    that takes a natural language query and translates it into a MYSQL query. 
    You will be given a Natural Language Query and 
    should translate it into MYSQL query for the following database schema:
    `Products` (
    `ProductID` int NOT NULL,
    `Country` varchar(50) DEFAULT NULL,
    `ProductCreationDate` date DEFAULT NULL,
    `ProductStatus` varchar(50) DEFAULT NULL,
    `ProductName` varchar(150) DEFAULT NULL,
    `ProductPrice` decimal(10, 2) DEFAULT NULL,
    `Quantity` int DEFAULT NULL,
    `CategoryName` varchar(100) DEFAULT NULL,
    PRIMARY KEY (`ProductID`)
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
@app.post(
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
async def nlq_endpoint(request: NLQRequest):
    natural_query = request.query.strip()
    if not natural_query:
        raise HTTPException(status_code=400, detail="Query cannot be empty.")

    # Parse query and construct SQL
    try:
        sql_filters = parse_query(natural_query)
        if not sql_filters:
            raise HTTPException(
                status_code=400, detail="No valid filters identified from query."
            )

        sql_query = sql_filters

        # Execute SQL query
        with engine.connect() as connection:
            result = connection.execute(text(sql_query))
            rows = [dict(row._mapping) for row in result]

        # Return results
        return {"query": natural_query, "results": rows}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/")
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
