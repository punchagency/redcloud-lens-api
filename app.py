
from fastapi import FastAPI, HTTPException
from flair.data import Sentence
from flair.models import SequenceTagger
from pydantic import BaseModel
from sqlalchemy import text

from db import engine

description = """
ChimichangApp API helps you do awesome stuff. 🚀

## Items

You can **read items**.

## Users

You will be able to:

* **Create users** (_not implemented_).
* **Read users** (_not implemented_).
"""
# Initialize FastAPI app
# app = FastAPI()
app = FastAPI(
    swagger_ui_parameters={"syntaxHighlight": False},
    title="ChimichangApp",
    description=description,
    summary="Deadpool's favorite app. Nuff said.",
    version="0.0.1",
    terms_of_service="http://example.com/terms/",
    contact={
        "name": "Deadpoolio the Amazing",
        "url": "http://x-force.example.com/contact/",
        "email": "dp@x-force.example.com",
    },
    license_info={
        "name": "Apache 2.0",
        "url": "https://www.apache.org/licenses/LICENSE-2.0.html",
    },
)


# Load Flair NER model
tagger = SequenceTagger.load("ner")


# Request payload schema
class NLQRequest(BaseModel):
    query: str


# Helper function to parse natural language query
def parse_query(natural_query: str):
    sentence = Sentence(natural_query)
    tagger.predict(sentence)

    # Extract entities
    entities = {
        entity.get_label("ner").value: entity.text
        for entity in sentence.get_spans("ner")
    }

    # Map entities to SQL filters
    filters = []
    if "ORG" in entities or "MISC" in entities:
        filters.append(f"ProductName LIKE '{entities['MISC']}'")
        filters.append(f"ProductName LIKE '%{entities['ORG']}%'")

    return " OR ".join(filters)


# NLQ endpoint
@app.post("/nlq")
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

        sql_query = f"SELECT * FROM Products WHERE {sql_filters}"

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
