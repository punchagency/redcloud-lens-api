import logging
import os

from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException
from google.cloud import bigquery
from openai import OpenAI
from rich.console import Console

from routers.nlq.helpers import (
    detect_text,
    extract_code,
    generate_bigquery_for_products,
    generate_gtin_sql,
    parse_bigquery,
    parse_query,
    process_product_image,
    request_image_inference,
    vertex_image_inference,
)
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
    USE_GTIN = False
    product_image = (
        process_product_image(request.product_image) if request.product_image else None
    )

    if not natural_query and not product_image:
        raise HTTPException(status_code=400, detail="No image or query submitted.")

    if product_image:
        steps = [vertex_image_inference, request_image_inference, detect_text]

        for function in steps:
            try:
                result = function(product_image)
                console.log(f"[bold yellow]fn: {function.__name__}")
                console.log(f"[bold yellow]result: {result}")
                if result:
                    if function is vertex_image_inference:
                        product_name: str = extract_code(result["label"])
                        USE_GTIN = True

                    if function is request_image_inference:
                        product_name: str = result["label"]
                        USE_GTIN = False

                    if function is detect_text:
                        possible_name: str = result["responses"][0][
                            "fullTextAnnotation"
                        ]["text"]
                        product_name = possible_name.replace("\n", " ")
                        USE_GTIN = False

                    break
            except Exception as e:
                console.log(f"[bold red]error happen: {e}")
                pass

    try:
        default_dataset = "snowflake_views"

        job_config = bigquery.QueryJobConfig(
            default_dataset=f"{bigquery_client.project}.{default_dataset}",
            # dry_run=True
        )

        if not product_name and not USE_GTIN:
            sql_query = parse_query(natural_query, product_name, limit, use_gtin=False)

            if not sql_query:
                raise HTTPException(
                    status_code=400, detail="No valid filters identified from query."
                )

            nlq_query_job = bigquery_client.query(sql_query, job_config=job_config)

            rows = [dict(row) for row in nlq_query_job.result()]
            return {"query": natural_query, "results": rows, "sql_query": sql_query}

        if USE_GTIN:
            sql_query = generate_gtin_sql(product_name)

        else:
            sql_query = generate_bigquery_for_products(product_name)

        if not sql_query:
            raise HTTPException(
                status_code=400, detail="No valid filters identified from query."
            )

        nlq_query_job = bigquery_client.query(sql_query, job_config=job_config)
        # for row in query_job.result():
        #     console.log(row)

        sku_rows = [dict(row) for row in nlq_query_job.result()]

        if len(sku_rows) < 1:
            return {"query": natural_query, "results": []}

        bigquery_sql = parse_bigquery(
            natural_query, product_name, limit, sku_rows, use_gtin=USE_GTIN
        )

        product_query_job = bigquery_client.query(bigquery_sql, job_config=job_config)

        rows = [dict(row) for row in product_query_job.result()]
        return {"query": natural_query, "results": rows, "sql_query": bigquery_sql}
    except Exception as e:
        logger.error(f"Error in nlq_endpoint: {e}")
        raise HTTPException(status_code=400, detail=str(e))
