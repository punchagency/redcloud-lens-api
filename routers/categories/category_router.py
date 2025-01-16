import logging
import os
import traceback

from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException
from google.cloud import bigquery
from rich.console import Console

from routers.categories.schemas import CategoryRequest, CategoryResponse

logger = logging.getLogger("test-logger")
logger.setLevel(logging.DEBUG)

load_dotenv()

# credentials = service_account.Credentials.from_service_account_file("gcp_conf.json")

bigquery_client = bigquery.Client(project=os.environ.get("GCP_PROJECT_ID", None))

console = Console()

router = APIRouter()


@router.post(
    "/categories",
    responses={
        200: {"description": "Query processed successfully."},
        400: {"description": "Bad request, invalid or empty query."},
        500: {"description": "Internal server error."},
    },
    response_model=CategoryResponse,
    response_model_by_alias=False,
    summary="Search by category",
    description="Exactly what it says on the tin",
)
async def category_endpoint(request: CategoryRequest, limit: int = 10):
    if limit <= 0:
        raise HTTPException(status_code=400, detail="Limit must be greater than zero.")

    category = request.category.strip() if request.category else None

    if not category:
        raise HTTPException(status_code=400, detail="No category submitted.")

    try:
        sql_query = f"""
            SELECT *
            FROM `marketplace_product_nigeria`
            WHERE LOWER(`Category Name`) = '{category.lower()}'
            LIMIT {limit}
        """
        default_dataset = "snowflake_views"

        job_config = bigquery.QueryJobConfig(
            default_dataset=f"{bigquery_client.project}.{default_dataset}",
            # dry_run=True
        )

        category_query_job = bigquery_client.query(sql_query, job_config=job_config)

        rows = [dict(row) for row in category_query_job.result()]
        return {"category": category, "results": rows}
    except Exception as e:
        logger.error("Error in category endpoint: %s", traceback.format_exc())
        raise HTTPException(status_code=400, detail=str(e)) from e
