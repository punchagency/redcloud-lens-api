import logging
import os
import traceback

from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException
from google.cloud import bigquery
from openai import OpenAI
from rich.console import Console

from db.helpers import create_conversation, get_conversation, save_message
from db.store import Conversation
from routers.nlq.helpers import (
    detect_text,
    execute_bigquery,
    extract_code,
    generate_product_name_sql,
    generate_gtin_sql,
    gpt_generate_sql,
    parse_nlq_search_query,
    parse_sku_search_query,
    process_product_image,
    request_image_inference,
    summarize_results,
    vertex_image_inference,
)
from routers.nlq.schemas import (
    MarketplaceProductNigeria,
    NLQRequest,
    NLQResponse,
    QueryRequest,
    QueryResponse,
)

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

    response = NLQResponse()
    conversation_id = request.conversation_id or None
    chat: Conversation = None
    chat_id: str = None

    if conversation_id:
        chat = get_conversation(conversation_id)
        if chat is None:
            raise HTTPException(status_code=404, detail="Conversation not found.")

    natural_query = request.query.strip() if request.query else None
    product_name = None
    USE_GTIN = False
    product_image = (
        process_product_image(request.product_image) if request.product_image else None
    )

    if not natural_query and not product_image:
        raise HTTPException(status_code=400, detail="No image or query submitted.")

    response.query = natural_query

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
        if not natural_query and not product_name:
            response.message = "Sorry, we could not recognize the product or brand in your image. Please try again with another picture."
            response.results = []
            response.analytics_queries = []
            response.suggested_queries = []

            return response

        default_dataset = "snowflake_views"

        job_config = bigquery.QueryJobConfig(
            default_dataset=f"{bigquery_client.project}.{default_dataset}",
            # dry_run=True
        )

        if not product_name:

            nlq_sql_queries = parse_nlq_search_query(
                natural_query, product_name, limit, use_gtin=False
            )

            if not nlq_sql_queries:
                response.message = "Sorry, we did not understand your search request and therefore cannot process it. Please refine your search and try again"
                response.results = []
                response.analytics_queries = []
                response.suggested_queries = []

                return response

            nlq_sql_query = nlq_sql_queries.get("sql_query", None)
            nlq_suggested_queries = nlq_sql_queries.get("suggested_queries", [])

            response.sql_query = nlq_sql_query
            response.suggested_queries = nlq_suggested_queries

            if not nlq_sql_query:
                response.message = "Sorry, we did not understand your search request and therefore cannot process it. Please refine your search and try again"
                response.results = []
                response.analytics_queries = []

                return response

            # nlq_query_job = bigquery_client.query(nlq_sql_query, job_config=job_config)

            packed_data = execute_bigquery(nlq_sql_query)

            if not packed_data:
                response.message = "No results found for your query"
                response.results = []
                response.analytics_queries = []

                return response

            dataframe, results = packed_data

            response.results = [
                MarketplaceProductNigeria(**product) for product in results
            ]

            # Step 3: Process and summarize the results
            if dataframe.empty:
                response.message = (
                    "Sorry! Could not generate report needed for analysis"
                )
                return response

            summary = summarize_results(dataframe, natural_query)
            if not summary:
                response.message = "Sorry! Could not generate analysis"
                return response

            result_analysis = summary.get("data_summary", None)
            analytics_queries = summary.get("suggested_queries", None)
            user_message = summary.get("user_message", None)

            ai_content = result_analysis
            user_content = user_message["content"]

            if chat:
                chat_id = chat[0].chat_id
                save_message(chat[0].chat_id, user_content, ai_content)
            else:
                saved = create_conversation(user_content, ai_content)
                chat_id = saved.chat_id

            response.result_analysis = result_analysis
            response.analytics_queries = analytics_queries
            response.conversation_id = chat_id

            return response

        if USE_GTIN:
            sql_query = generate_gtin_sql(product_name)

        else:
            sql_query = generate_product_name_sql(product_name)

        response.sql_query = sql_query

        if not sql_query:
            response.message = "Sorry, we could not understand your request and therefore cannot process it. Please refine your query and try again"
            return response

        nlq_query_job = bigquery_client.query(sql_query, job_config=job_config)
        # for row in query_job.result():
        #     console.log(row)

        sku_rows = [dict(row) for row in nlq_query_job.result()]

        if len(sku_rows) < 1:
            response.message = (
                "No data relating to your product/query found in our catalog"
            )
            return response

        sku_sql_queries = parse_sku_search_query(
            natural_query, product_name, limit, sku_rows, use_gtin=USE_GTIN
        )

        if not sku_sql_queries:
            response.message = "Sorry, we did not understand your search request and therefore cannot process it. Please refine your search and try again"
            return response

        sku_sql_query = sku_sql_queries.get("sql_query", None)
        sku_suggested_queries = sku_sql_queries.get("suggested_queries", None)

        response.sql_query = sku_sql_query
        response.suggested_queries = sku_suggested_queries

        if not sku_sql_query:
            response.message = "Sorry, we did not understand your search request and therefore cannot process it. Please refine your search and try again"
            response.results = []
            response.analytics_queries = []

            return response

        # product_query_job = bigquery_client.query(sku_sql_query, job_config=job_config)
        packed_data = execute_bigquery(sku_sql_query)

        if not packed_data:
            response.message = "No results found for your query"
            response.results = []
            response.analytics_queries = []

            return response

        # rows = [dict(row) for row in product_query_job.result()]

        dataframe, results = packed_data

        response.results = [MarketplaceProductNigeria(**product) for product in results]

        if dataframe.empty:
            response.message = "Sorry! Could not generate report needed for analysis"
            return response

        summary = summarize_results(dataframe, natural_query)
        if not summary:
            response.message = "Sorry! Could not generate analysis"
            return response

        result_analysis = summary.get("data_summary", None)
        analytics_queries = summary.get("suggested_queries", None)
        user_message = summary.get("user_message", None)

        ai_content = result_analysis
        user_content = user_message["content"]

        if chat:
            chat_id = chat[0].chat_id
            save_message(chat[0].chat_id, user_content, ai_content)
        else:
            saved = create_conversation(user_content, ai_content)
            chat_id = saved.chat_id

        response.result_analysis = result_analysis
        response.analytics_queries = analytics_queries
        response.conversation_id = chat_id

        return response

    except Exception as e:
        logger.error(f"Error in nlq_endpoint: {traceback.format_exc()}")
        raise HTTPException(status_code=400, detail=str(e))


# Endpoint for querying the database
@router.post("/nlq-test", response_model=QueryResponse)
async def handle_nlq(query_request: QueryRequest):
    """
    Handle natural language query requests.
    """
    natural_query = query_request.query
    conversation_id = query_request.conversation_id or None
    chat: Conversation = None
    chat_id: str = None

    if conversation_id:
        chat = get_conversation(conversation_id)
        if chat is None:
            raise HTTPException(status_code=404, detail="Conversation not found.")

    # Step 1: Convert natural language to SQL
    queries = gpt_generate_sql(natural_query)

    sql_query = queries.get("sql_query", None)
    suggested_queries = queries.get("suggested_queries", None)

    # Step 2: Execute SQL on BigQuery
    packed_data = execute_bigquery(sql_query)
    if not packed_data:
        return {"result": "No results found for your query."}

    dataframe, result = packed_data

    # Step 3: Process and summarize the results
    if dataframe.empty:
        return {"result": "No results found for your query."}

    summary = summarize_results(dataframe, natural_query, conversations=chat)
    if not summary:
        return {"result": None}

    result_analysis = summary.get("data_summary", None)
    analytics_queries = summary.get("suggested_queries", None)
    user_message = summary.get("user_message", None)

    ai_content = result_analysis
    user_content = user_message["content"]

    if chat:
        chat_id = chat[0].chat_id
        save_message(chat[0].chat_id, user_content, ai_content)
    else:
        saved = create_conversation(user_content, ai_content)
        chat_id = saved.chat_id

    return {
        "result": result,
        "result_analysis": result_analysis,
        "conversation_id": chat_id,
        "analytics_queries": analytics_queries,
        "suggested_queries": suggested_queries,
    }
