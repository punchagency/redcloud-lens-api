import json
import logging
import os

import requests
from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException
from google.cloud import bigquery
from openai import OpenAI
from rich.console import Console

from routers.nlq.helpers import (detect_text, parse_query,
                                 process_product_image,
                                 request_image_inference,
                                 vertex_image_inference)
from routers.nlq.schemas import NLQRequest, NLQResponse

logger = logging.getLogger("test-logger")
logger.setLevel(logging.DEBUG)

load_dotenv()

# credentials = service_account.Credentials.from_service_account_file("gcp_conf.json")

bigquery_client = bigquery.Client(project=os.environ.get("GCP_PROJECT_ID", None))

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY", None))

console = Console()


router = APIRouter()


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
    product_name = None
    product_image = (
        process_product_image(request.product_image) if request.product_image else None
    )

    if not natural_query and not product_image:
        raise HTTPException(status_code=400, detail="No image or query submitted.")

    if product_image:
        steps = [request_image_inference, detect_text]

        for function in steps:
            try:
                result = function(product_image)
                console.log(f"[bold yellow]fn: {function.__name__}")
                console.log(f"[bold yellow]result: {result}")
                if result:
                    if function is vertex_image_inference:
                        product_name: str = result["label"]

                    if function is request_image_inference:
                        product_name: str = result["label"]

                    if function is detect_text:
                        possible_name: str = result["responses"][0][
                            "fullTextAnnotation"
                        ]["text"]
                        product_name = possible_name.replace("\n", " ")
                    break
            except Exception as e:
                console.log(f"[bold red]error happen: {e}")
                pass

    try:
        sql_query = parse_query(natural_query, product_name, limit)
        if not sql_query:
            raise HTTPException(
                status_code=400, detail="No valid filters identified from query."
            )
        default_dataset = "snowflake_views"

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
        logger.error(f"Error in nlq_endpoint: {e}")
        raise HTTPException(status_code=400, detail=str(e))
