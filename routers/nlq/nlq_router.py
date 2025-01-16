import logging
import os
import traceback

from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException
from google.cloud import bigquery
from openai import OpenAI
from rich.console import Console

from db.helpers import create_conversation, get_conversation, save_message
from routers.nlq.helpers import (
    azure_vision_service,
    convert_to_base64,
    detect_text,
    execute_bigquery,
    extract_code,
    generate_gtin_sql,
    generate_product_name_sql,
    parse_nlq_search_query,
    parse_sku_search_query,
    process_product_image,
    regular_chat,
    request_image_inference,
    summarize_results,
)
from routers.nlq.schemas import (
    MarketplaceProductNigeria,
    NLQRequest,
    NLQResponse,
    WhatsappResponse,
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
    # response_model=Base64EncodedResponse,
    # response_model_by_alias=False,
    summary="Natural Language Query",
    description="Process a natural language query to fetch matching products from the database.",
)
async def nlq_endpoint(request: NLQRequest, limit: int = 10):
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
        response.message = "No query or image submitted."
        response.results = []
        response.analytics_queries = []
        response.suggested_queries = []

        return convert_to_base64(WhatsappResponse(data=response, status="error"))

        # raise HTTPException(status_code=400, detail="No image or query submitted.")

    if conversation_id:
        chat = get_conversation(conversation_id)
        if chat is None:
            raise HTTPException(status_code=404, detail="Conversation not found.")

    if product_image:
        steps = [azure_vision_service, detect_text]

        for function in steps:
            try:
                result = function(product_image)
                # console.log(f"[bold yellow]fn: {function.__name__}")
                # console.log(f"[bold yellow]result: {result}")
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
            except Exception as e:
                console.log(f"[bold red]Error processing image: {e}")

    try:
        if not natural_query and not product_name:
            response.message = "Sorry, we could not recognize the product or brand in your image. Please try again with another picture."
            response.results = []
            response.analytics_queries = []
            response.suggested_queries = []

            return convert_to_base64(WhatsappResponse(data=response, status="error"))

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

                    return WhatsappResponse(data=response, status="success")

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

                return convert_to_base64(WhatsappResponse(data=response))

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

                    return WhatsappResponse(data=response, status="error")

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

                return convert_to_base64(WhatsappResponse(data=response))

            nlq_sql_query_job = execute_bigquery(nlq_sql_query)
            if not nlq_sql_query_job:
                response.message = "Sorry, we could not access the data you requested. Please try again later."
                response.results = []
                response.analytics_queries = []

                return convert_to_base64(
                    WhatsappResponse(data=response, status="error")
                )

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
                    return convert_to_base64(
                        WhatsappResponse(data=response, status="error")
                    )

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
                return convert_to_base64(WhatsappResponse(data=response))

            summary = summarize_results(dataframe, natural_query)
            if not summary:
                response.message = "Sorry! Could not generate appropriate response to summarize results"
                return convert_to_base64(
                    WhatsappResponse(data=response, status="error")
                )

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

            return convert_to_base64(WhatsappResponse(data=response))

        if use_gtin:
            sql_query = generate_gtin_sql(product_name)

        else:
            sql_query = generate_product_name_sql(product_name)

        response.sql_query = sql_query

        if not sql_query:
            regular_summary = regular_chat(natural_query, conversations=chat)
            if not regular_summary:
                response.message = "Sorry, we could not understand your request. Please refine your input and try again"
                response.results = []
                response.analytics_queries = []
                response.suggested_queries = []
                return convert_to_base64(
                    WhatsappResponse(data=response, status="error")
                )

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

            return convert_to_base64(WhatsappResponse(data=response))

        nlq_query_job = execute_bigquery(sql_query)

        sku_rows = [dict(row) for row in nlq_query_job.result()]

        if len(sku_rows) < 1:
            response.message = (
                "No data relating to your product/query was found in our catalog"
            )
            response.results = []
            response.analytics_queries = []
            response.suggested_queries = []

            return convert_to_base64(WhatsappResponse(data=response, status="error"))

        sku_sql_queries = parse_sku_search_query(
            natural_query, product_name, limit, sku_rows, country=country
        )

        if not sku_sql_queries:
            response.message = "Sorry, we did not understand your search request. Please refine your search input and try again"
            response.results = []
            response.analytics_queries = []
            response.suggested_queries = []

            return convert_to_base64(WhatsappResponse(data=response, status="error"))

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

            return convert_to_base64(WhatsappResponse(data=response, status="error"))

        sku_sql_query_job = execute_bigquery(sku_sql_query)
        if not sku_sql_query_job:
            response.message = "Sorry, we could not access the data you requested. Please try again later."
            response.results = []
            response.analytics_queries = []

            return convert_to_base64(WhatsappResponse(data=response, status="error"))

        results = [dict(row) for row in sku_sql_query_job.result()]
        dataframe = sku_sql_query_job.to_dataframe()

        response.results = [MarketplaceProductNigeria(**product) for product in results]

        if dataframe.empty:
            regular_summary = regular_chat(natural_query, conversations=chat)
            if not regular_summary:
                response.message = (
                    "Sorry! Could not generate report needed for analysis"
                )
                return convert_to_base64(
                    WhatsappResponse(data=response, status="error")
                )
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

            return convert_to_base64(WhatsappResponse(data=response))

        summary = summarize_results(dataframe, natural_query)
        if not summary:
            response.message = "Sorry! Could not generate analysis"
            return convert_to_base64(WhatsappResponse(data=response, status="error"))

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

        return convert_to_base64(WhatsappResponse(data=response))

    except Exception as e:
        logger.error("Error in nlq_endpoint: %s", traceback.format_exc())
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post(
    "/web",
    responses={
        200: {"description": "Query processed successfully."},
        400: {"description": "Bad request, invalid or empty query."},
        500: {"description": "Internal server error."},
    },
    response_model=NLQResponse,
    response_model_by_alias=False,
    summary="Natural Language Query",
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
            sql_query = generate_gtin_sql(product_name)

        else:
            sql_query = generate_product_name_sql(product_name)

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
        logger.error("Error in nlq_endpoint: %s", traceback.format_exc())
        raise HTTPException(status_code=400, detail=str(e)) from e
