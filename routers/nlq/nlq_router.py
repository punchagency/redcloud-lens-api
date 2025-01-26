import logging
import os
import traceback
from typing import Any

from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException, Response
from google.cloud import bigquery
from openai import OpenAI
from rich.console import Console
from pandas import DataFrame
from db.helpers import create_conversation, get_conversation, save_message
from routers.categories.schemas import CategoryRequest, CategoryResponse
from routers.nlq.helpers import (
    azure_vision_service,
    convert_to_base64,
    detect_text,
    execute_bigquery,
    extract_code,
    generate_gtin_sql,
    generate_product_name_sql,
    handle_whatsapp_data,
    parse_nlq_search_query,
    parse_sku_search_query,
    process_product_image,
    process_whatsapp_image_data,
    regular_chat,
    request_image_inference,
    summarize_results,
    decrypt_request,
    encrypt_response,
)
from routers.nlq.schemas import (
    MarketplaceProductNigeria,
    NLQRequest,
    NLQResponse,

)
from routers.whatsapp.schema import (
    WhatsappNLQRequest,
)


logger = logging.getLogger("test-logger")
logger.setLevel(logging.DEBUG)

load_dotenv()

bigquery_client = bigquery.Client(project=os.environ.get("GCP_PROJECT_ID", None))

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY", None))

console = Console()


router = APIRouter()


@router.get("/nlq")
async def index():
    return {"message": "Hello World"}


@router.post(
    "/nlq",
    responses={
        200: {"description": "Query processed successfully."},
        400: {"description": "Bad request, invalid or empty query."},
        500: {"description": "Internal server error."},
    },
    # response_model=Base64EncodedResponse,
    # response_model_by_alias=False,
    summary="API for whatsapp",
    description="Process a natural language query to fetch matching products from the database.",
)
async def nlq_endpoint(request: WhatsappNLQRequest):
    response: Any = None
    try:
        private_key = open("whatsapp_private_key.pem", "r").read()
        data = decrypt_request(request, private_key, os.environ.get("WHATSAPP_PASSPHRASE", None))
        match data.decrypted_body.action:
            case "send_message":
                print(data.decrypted_body)
            case "send_image":
                print(data.decrypted_body)
            case "send_product_image":
                print(data.decrypted_body)
            case "ping":
                print("pong")
                response = {
                    "data": {
                        "status": "active"
                    }
                }
            case "data_exchange":
                response = handle_whatsapp_data(data.decrypted_body.data).model_dump(mode="json")
                print(response)

            case _:
                print(data.decrypted_body)
                print("Invalid action")

    except Exception as e:
        print(e)
    finally:
        final_response = encrypt_response(response, data.aes_key_buffer, data.initial_vector_buffer)
    return Response(content=final_response, status_code=200)


@router.post(
    "/web",
    responses={
        200: {"description": "Query processed successfully."},
        400: {"description": "Bad request, invalid or empty query."},
        500: {"description": "Internal server error."},
    },
    response_model=NLQResponse,
    response_model_by_alias=False,
    summary="API for web app",
    description="Process a natural language query to fetch matching products from the database.",
)
async def web_endpoint(request: NLQRequest, limit: int = 10):
    if limit <= 0:
        raise HTTPException(status_code=400, detail="Limit must be greater than zero.")

    response = NLQResponse()

    chat = None
    chat_id: str = None

    conversation_id = request.conversation_id or None
    country = request.country or "Nigeria"
    natural_query = request.query.strip() if request.query else None

    response.query = natural_query

    product_name = None
    use_gtin = False
    product_image = (
        process_product_image(request.product_image) if request.product_image else None
    )

    if not natural_query and not product_image:
        raise HTTPException(status_code=400, detail="No image or query submitted.")

    if conversation_id:
        chat = get_conversation(conversation_id)
        if chat is None:
            raise HTTPException(status_code=404, detail="Conversation not found.")

    if product_image:
        steps = [azure_vision_service, detect_text]

        for function in steps:
            try:
                result = function(product_image)
                if result:
                    if function is azure_vision_service:
                        product_name: str = extract_code(result["label"])
                        use_gtin = True

                    if function is request_image_inference:
                        product_name: str = result["label"]
                        use_gtin = False

                    if function is detect_text:
                        possible_name: str = result["responses"][0][
                            "fullTextAnnotation"
                        ]["text"]
                        product_name = possible_name.replace("\n", " ")
                        use_gtin = False

                    break
            except Exception:
                logger.error("Error in processing image: %s", traceback.format_exc())
    try:
        if not natural_query and not product_name:
            response.message = "Sorry, we could not recognize the product or brand in your image. Please try again with another picture."
            response.results = []
            response.analytics_queries = []
            response.suggested_queries = []

            return response

        if not product_name:
            nlq_sql_queries = parse_nlq_search_query(
                natural_query, product_name, limit, country=country
            )

            if not nlq_sql_queries:
                regular_summary = regular_chat(natural_query, conversations=chat)
                if not regular_summary:
                    response.message = "Sorry, we did not understand your search request. Please refine your search and try again"
                    response.results = []
                    response.analytics_queries = []
                    response.suggested_queries = []

                    return response

                result_analysis = regular_summary.get("data_summary", None)
                analytics_queries = regular_summary.get("suggested_queries", None)
                user_message = regular_summary.get("user_message", None)

                ai_content = result_analysis
                user_content = user_message["content"]

                if chat:
                    chat_id = chat[0].chat_id
                    save_message(chat_id, user_content, ai_content)
                else:
                    saved = create_conversation(user_content, ai_content)
                    chat_id = saved.chat_id

                response.result_analysis = result_analysis
                response.analytics_queries = analytics_queries
                response.conversation_id = chat_id
                response.results = []

                return response

            nlq_sql_query = nlq_sql_queries.get("sql_query", None)
            nlq_suggested_queries = nlq_sql_queries.get("suggested_queries", [])

            response.sql_query = nlq_sql_query
            response.suggested_queries = nlq_suggested_queries

            if not nlq_sql_query:
                regular_summary = regular_chat(natural_query, conversations=chat)
                if not regular_summary:
                    response.message = "Sorry, we did not understand your search request. Please refine your search and try again"
                    response.results = []
                    response.analytics_queries = []

                    return response

                result_analysis = regular_summary.get("data_summary", None)
                analytics_queries = regular_summary.get("suggested_queries", None)
                user_message = regular_summary.get("user_message", None)

                ai_content = result_analysis
                user_content = user_message["content"]

                if chat:
                    chat_id = chat[0].chat_id
                    save_message(chat_id, user_content, ai_content)
                else:
                    saved = create_conversation(user_content, ai_content)
                    chat_id = saved.chat_id

                response.result_analysis = result_analysis
                response.analytics_queries = analytics_queries
                response.conversation_id = chat_id
                response.results = []

                return response

            nlq_sql_query_job = execute_bigquery(nlq_sql_query)
            if not nlq_sql_query_job:
                response.message = "Sorry, we could not access the data you requested. Please try again later."
                response.results = []
                response.analytics_queries = []

                return response

            results = [dict(row) for row in nlq_sql_query_job.result()]
            dataframe = nlq_sql_query_job.to_dataframe()

            response.results = [
                MarketplaceProductNigeria(**product) for product in results
            ]

            if dataframe.empty:
                regular_summary = regular_chat(natural_query, conversations=chat)
                if not regular_summary:
                    response.message = "Sorry! Could not generate appropriate response due to lack of data"
                    response.results = []
                    response.analytics_queries = []
                    return response

                result_analysis = regular_summary.get("data_summary", None)
                analytics_queries = regular_summary.get("suggested_queries", None)
                user_message = regular_summary.get("user_message", None)

                ai_content = result_analysis
                user_content = user_message["content"]

                if chat:
                    chat_id = chat[0].chat_id
                    save_message(chat_id, user_content, ai_content)
                else:
                    saved = create_conversation(user_content, ai_content)
                    chat_id = saved.chat_id

                response.result_analysis = result_analysis
                response.analytics_queries = analytics_queries
                response.conversation_id = chat_id
                response.results = []
                return response

            summary = summarize_results(dataframe, natural_query)
            if not summary:
                response.message = "Sorry! Could not generate appropriate response to summarize results"
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

        if use_gtin:
            sql_query = generate_gtin_sql(product_name, country)

        else:
            sql_query = generate_product_name_sql(product_name, country)

        response.sql_query = sql_query

        if not sql_query:
            regular_summary = regular_chat(natural_query, conversations=chat)
            if not regular_summary:
                response.message = "Sorry, we could not understand your request. Please refine your input and try again"
                response.results = []
                response.analytics_queries = []
                response.suggested_queries = []
                return response

            result_analysis = regular_summary.get("data_summary", None)
            analytics_queries = regular_summary.get("suggested_queries", None)
            user_message = regular_summary.get("user_message", None)

            ai_content = result_analysis
            user_content = user_message["content"]

            if chat:
                chat_id = chat[0].chat_id
                save_message(chat_id, user_content, ai_content)
            else:
                saved = create_conversation(user_content, ai_content)
                chat_id = saved.chat_id

            response.result_analysis = result_analysis
            response.analytics_queries = analytics_queries
            response.conversation_id = chat_id

            return response

        nlq_query_job = execute_bigquery(sql_query)

        sku_rows = [dict(row) for row in nlq_query_job.result()]

        if len(sku_rows) < 1:
            response.message = (
                "No data relating to your product/query was found in our catalog"
            )
            response.results = []
            response.analytics_queries = []
            response.suggested_queries = []

            return response

        sku_sql_queries = parse_sku_search_query(
            natural_query,
            product_name,
            limit,
            sku_rows,
            country=country,
        )

        if not sku_sql_queries:
            response.message = "Sorry, we did not understand your search request. Please refine your search input and try again"
            response.results = []
            response.analytics_queries = []
            response.suggested_queries = []

            return response

        sku_sql_in = sku_sql_queries.get("sql", None)
        sku_sql_where = sku_sql_queries.get("sql_query", None)
        if sku_sql_where:
            sku_sql_query = (
                f"{sku_sql_in} {sku_sql_where.replace('WHERE', '')} LIMIT {limit};"
            )
        else:
            sku_sql_query = f"{sku_sql_in} LIMIT {limit};"

        sku_suggested_queries = sku_sql_queries.get("suggested_queries", None)

        response.sql_query = sku_sql_query
        response.suggested_queries = sku_suggested_queries

        if not sku_sql_query:
            response.message = "Sorry, we did not understand your search request. Please refine your search input and try again"
            response.results = []
            response.analytics_queries = []

            return response

        sku_sql_query_job = execute_bigquery(sku_sql_query)
        if not sku_sql_query_job:
            response.message = "Sorry, we could not access the data you requested. Please try again later."
            response.results = []
            response.analytics_queries = []

            return response

        results = [dict(row) for row in sku_sql_query_job.result()]
        dataframe = sku_sql_query_job.to_dataframe()

        response.results = [MarketplaceProductNigeria(**product) for product in results]

        if dataframe.empty:
            regular_summary = regular_chat(natural_query, conversations=chat)
            if not regular_summary:
                response.message = (
                    "Sorry! Could not generate report needed for analysis"
                )
                return response
            result_analysis = regular_summary.get("data_summary", None)
            analytics_queries = regular_summary.get("suggested_queries", None)
            user_message = regular_summary.get("user_message", None)

            ai_content = result_analysis
            user_content = user_message["content"]

            if chat:
                chat_id = chat[0].chat_id
                save_message(chat_id, user_content, ai_content)
            else:
                saved = create_conversation(user_content, ai_content)
                chat_id = saved.chat_id

            response.result_analysis = result_analysis
            response.analytics_queries = analytics_queries
            response.conversation_id = chat_id

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
        raise HTTPException(status_code=400, detail=str(e)) from e


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
    country = request.country.strip() if request.country else "Nigeria"
    if not category:
        raise HTTPException(status_code=400, detail="No category submitted.")

    try:
        sql_query = f"""
            SELECT *
            FROM `{'marketplace_product_nigeria' if country == 'Nigeria' else 'marketplace_product_except_nigeria'}`
            WHERE LOWER(`Category Name`) = @category
            LIMIT @limit
        """
        default_dataset = "snowflake_views"

        job_config = bigquery.QueryJobConfig(
            default_dataset=f"{bigquery_client.project}.{default_dataset}",
            query_parameters=[
                bigquery.ScalarQueryParameter("category", "STRING", category.lower()),
                bigquery.ScalarQueryParameter("limit", "INT64", limit),
            ],
            # dry_run=True
        )

        category_query_job = bigquery_client.query(sql_query, job_config=job_config)

        rows = [dict(row) for row in category_query_job.result()]
        return {"category": category, "results": rows}
    except Exception as e:
        logger.error("Error in category endpoint: %s", traceback.format_exc())
        raise HTTPException(status_code=400, detail=str(e)) from e
