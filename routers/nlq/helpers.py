import base64
import json
import os
from typing import List, Optional, Tuple, Union, Dict

import requests
from dotenv import load_dotenv
from fastapi import UploadFile
from google.cloud import bigquery
from openai import OpenAI
import pandas as pd
from rich.console import Console

from db.helpers import create_conversation
from db.store import Conversation
from external_services.vertex import VertexAIService
from routers.nlq.schemas import DataAnalysis, Text2SQL

load_dotenv()

console = Console()
bigquery_client = bigquery.Client(project=os.environ.get("GCP_PROJECT_ID", None))

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY", None))


def extract_code(input_string: str) -> str:
    """Extracts the code portion from a given string.

    Args:
        input_string: The input string in the format "Prefix_Code".

    Returns:
        The extracted code portion.
    """

    parts = input_string.split("_")

    return f"'{parts[1]}"


def generate_product_name_sql(product_name: str, limit=10) -> str:
    """Generates a BigQuery SQL query to search for products with at least one word from the given product name.

    Args:
        product_name: The product name to search for.

    Returns:
        A string containing the BigQuery SQL query.
    """

    words = product_name.split()
    conditions = [f"LOWER('Product Name') LIKE '%{word.lower()}%'" for word in words]
    where_clause = " OR ".join(conditions)

    query = f"""
      SELECT *
        FROM `market_place_product_nigeria_mapping_table`
        WHERE {where_clause}
        LIMIT {limit}
    """

    print(query)

    return query


def generate_gtin_sql(gtin: str, limit=10) -> str:
    """Generates a BigQuery SQL query from a string of SKUs.

    Args:
        gtin: A gtin string.
        limit: limit for result.

    Returns:
        A string containing the BigQuery SQL query.
    """

    query = f"""
        SELECT *
        FROM `market_place_product_nigeria_mapping_table`
        WHERE Mapping = "{gtin}"
        LIMIT {limit}
    """

    return query


def build_context_nlq(
    natural_query: str, product_name: Optional[str], total: Optional[int] = 10
) -> str:
    product_ctxt = (
        f"to search for products with at least a word from '{product_name}' in their name when a case insensitive search is performed"
        if product_name
        else ""
    )

    return f"""
        You are an expert Text2SQL AI in the e-commerce domain 
        that takes a natural language query and translates it into a BigQuery SQL query. 
        Translate the query into a BigQuery SQL query {product_ctxt} in the database:
        `marketplace_product_nigeria` (
            `Brand or Manufacturer` STRING,  
            `Product ID` INT64,  
            `Country` STRING,  
            `SKU` STRING,  
            `Brand` STRING,  
            `Manufacturer` STRING,  
            `Product Creation Date` TIMESTAMP,  
            `Product Status` STRING,  
            `Product Name` STRING,  
            `Product Price` FLOAT64,  
            `Quantity` FLOAT64,  
            `Stock Status` STRING,  
            `Salable Quantity` FLOAT64,  
            `Category Name` STRING,  
            `Top Category` STRING,  
            `Seller ID` INT64,  
            `Seller Group` STRING,  
            `Seller Name` STRING,  
            `HS Record ID` STRING,  
            `Last Price Update At` TIMESTAMP
        )
        Your response should be formatted in the given structure 
        where sql_query is the translated BigQuery SQL query with a LIMIT of {total},
        suggested_queries is a list of similar or refined natural language queries the user can use instead in their next search.
        If no natural language query is provided, return  {'BigQuery SQL query {product_ctxt}' or "suggested_queries"}.
        Favor OR operations over AND operations. Ensure the query selects all fields and the query is optimized for BigQuery performance.
    """


def build_context_nlq_sku(
    natural_query: str,
    product_name: Optional[str],
    skus: list,
    total: Optional[int] = 10,
) -> str:
    product_ctxt = f"for products whose sku is in '{skus}' " if skus else ""

    return f"""
        You are an expert Text2SQL AI in the e-commerce domain 
        that takes a natural language query and translates it into a BigQuery SQL query. 
        Translate the query into a BigQuery SQL query {product_ctxt}. 
        the database schema:
        `marketplace_product_nigeria` (
            `Brand or Manufacturer` STRING,  
            `Product ID` INT64,  
            `Country` STRING,  
            `SKU` STRING,  
            `Brand` STRING,  
            `Manufacturer` STRING,  
            `Product Creation Date` TIMESTAMP,  
            `Product Status` STRING,  
            `Product Name` STRING,  
            `Product Price` FLOAT64,  
            `Quantity` FLOAT64,  
            `Stock Status` STRING,  
            `Salable Quantity` FLOAT64,  
            `Category Name` STRING,  
            `Top Category` STRING,  
            `Seller ID` INT64,  
            `Seller Group` STRING,  
            `Seller Name` STRING,  
            `HS Record ID` STRING,  
            `Last Price Update At` TIMESTAMP
        )
        Your response should be formatted in the given structure 
        where sql_query is the translated BigQuery SQL query with a LIMIT of {total},
        suggested_queries is a list of similar or refined natural language queries the user can use instead in their next search.
        If no natural language query is provided, return  {'BigQuery SQL query {product_ctxt}' or "suggested_queries"}.
        Favor OR operations over AND operations. Ensure the query selects all fields and the query is optimized for BigQuery performance.
    """


def parse_sku_search_query(
    natural_query: Optional[str],
    product_name: Optional[str],
    amount: Optional[int],
    sku_rows: Optional[dict],
    use_gtin: bool = True,
) -> Optional[Dict[str, str | List[str]]]:
    if not natural_query and not product_name:
        return None
    all_skus = []
    if sku_rows:
        for row in sku_rows:
            skus = row["SKU_STRING"].split(",")
            all_skus.extend(skus)

        # print(all_skus)
        skus_formatted = ", ".join([f'"{sku}"' for sku in all_skus])
        # print(skus_formatted)

        context = build_context_nlq_sku(
            natural_query, product_name, skus_formatted, total=amount
        )
    else:
        context = build_context_nlq(natural_query, product_name, total=amount)

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
        return extracted_data
    except (KeyError, json.JSONDecodeError) as e:
        console.log(f"Error parsing query: {e}")
        return None


def parse_nlq_search_query(
    natural_query: Optional[str],
    product_name: Optional[str],
    amount: Optional[int],
    use_gtin: bool = True,
) -> Optional[Dict[str, str | List[str]]]:
    if not natural_query and not product_name:
        return None

    context = build_context_nlq(natural_query, product_name, total=amount)

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
        return extracted_data
    except (KeyError, json.JSONDecodeError) as e:
        console.log(f"Error parsing query: {e}")
        return None


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


def detect_text(base64_encoded_image: str) -> Dict:
    """Detects text in the file."""

    # Request JSON body
    request_body = {
        "requests": [
            {
                "image": {"content": base64_encoded_image},
                "features": [{"type": "TEXT_DETECTION"}],
            }
        ]
    }

    # Get access token using gcloud
    PROJECT_ID = os.environ.get("GCP_PROJECT_ID", None)
    access_token = os.environ.get("GCP_AUTH_TOKEN", None)

    # Define headers
    headers = {
        "Authorization": f"Bearer {access_token}",
        "x-goog-user-project": PROJECT_ID,
        "Content-Type": "application/json; charset=utf-8",
    }

    # Endpoint URL
    url = "https://vision.googleapis.com/v1/images:annotate"

    # Send POST request
    response = requests.post(url, headers=headers, json=request_body)

    # Output the response
    console.log(f"Status Code: {response.status_code}")
    if response.status_code == 200:
        return response.json()


def request_image_inference(product_image: str) -> Dict:
    """image inference from red cloud inference service"""
    product_name = None
    api_token = os.environ.get("INFERENCE_API_TOKEN", None)

    url = "https://redcloud-inference-8cae8b3-v27.app.beam.cloud"
    payload = {"image": product_image}
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json",
    }

    response = requests.request(
        "POST", url, headers=headers, data=json.dumps(payload), timeout=30
    )
    console.log(response.json())
    result = response.json()
    if result["status"] != "error":
        product_name = result.get("result")
    return product_name


def vertex_image_inference(image: str) -> Dict:
    image_result = None
    ENDPOINT_ID = "793057945905528832"
    PROJECT_ID = "225990659434"

    service = VertexAIService(project_id=PROJECT_ID, endpoint_id=ENDPOINT_ID)

    # Example image to process
    image_path = "uploaded_img.png"
    # image = PIL.Image.open(image_path)
    # image_name = "sample_image.jpg"

    # Process and classify the example image
    result = service.process_and_classify_image(image, image_path)
    if result:
        image_result = result
    return image_result


def build_context_analytics(
    natural_query: str, product_name: Optional[str] = None, total: Optional[int] = 10
) -> str:
    product_ctxt = (
        f"to search for products with at least a word from '{product_name}' in their name when a case insensitive search is performed"
        if product_name
        else ""
    )
    prod_search = f"BigQuery SQL query {product_ctxt}"
    suggested_search = "suggested_queries"

    return f"""
        You are a state of the art data analyst in the e-commerce domain 

        Your response should be formatted in the given structure 
        where data_summary is the analytics of the given data or 
        general response to user input, and
        suggested_queries is a list of similar or refined natural language queries the user can use to get more useful insights their next search.
        If no natural language query is provided, return  {prod_search or suggested_search}.
        Favor OR operations over AND operations. Ensure the query selects all fields and the query is optimized for BigQuery performance.
    """


def build_context_query(
    natural_query: str, product_name: Optional[str] = None, total: Optional[int] = 10
) -> str:
    product_ctxt = (
        f"to search for products with at least a word from '{product_name}' in their name when a case insensitive search is performed"
        if product_name
        else ""
    )

    prod_search = f"BigQuery SQL query {product_ctxt}"
    suggested_search = "suggested_queries"

    ctxt = f"""
        You are an expert SQL generator for BigQuery the following database:
        `marketplace_product_nigeria` (
            `Brand or Manufacturer` STRING,  
            `Product ID` INT64,  
            `Country` STRING,  
            `SKU` STRING,  
            `Brand` STRING,  
            `Manufacturer` STRING,  
            `Product Creation Date` TIMESTAMP,  
            `Product Status` STRING,  
            `Product Name` STRING,  
            `Product Price` FLOAT64,  
            `Quantity` FLOAT64,  
            `Stock Status` STRING,  
            `Salable Quantity` FLOAT64,  
            `Category Name` STRING,  
            `Top Category` STRING,  
            `Seller ID` INT64,  
            `Seller Group` STRING,  
            `Seller Name` STRING,  
            `HS Record ID` STRING,  
            `Last Price Update At` TIMESTAMP
        )
        Your response should be formatted in the given structure 
        where sql_query is the translated BigQuery SQL query with a LIMIT of {total},
        suggested_queries is a list of similar or refined natural language queries the user can use instead in their next search.
        If no natural language query is provided, return  {prod_search or suggested_search}.
        Favor OR operations over AND operations. 
        Ensure the query selects all fields, 
        always does case insensitive text searches except specified otherwise
        and the query is optimized for BigQuery performance.
    """

    return ctxt


# Helper function to interact with GPT
def gpt_generate_sql(natural_query: str) -> Optional[Dict[str, str | List[str]]]:
    """
    Generates SQL using GPT-4.
    """
    ctxt = build_context_query(natural_query)
    response = client.beta.chat.completions.parse(
        model="gpt-4o-2024-08-06",
        messages=[
            {
                "role": "system",
                "content": ctxt,
            },
            {
                "role": "user",
                "content": f"Convert the following natural language query to SQL: {natural_query}",
            },
        ],
        response_format=Text2SQL,
    )
    extracted_data = json.loads(response.choices[0].message.content)
    console.log(extracted_data)
    return extracted_data


# Helper function to execute BigQuery SQL
def execute_bigquery(sql_query: str) -> Tuple[pd.DataFrame, List]:
    """
    Executes a SQL query on BigQuery and returns the results as a DataFrame.
    """
    default_dataset = "snowflake_views"

    job_config = bigquery.QueryJobConfig(
        default_dataset=f"{bigquery_client.project}.{default_dataset}",
        # dry_run=True
    )

    try:
        query_job = bigquery_client.query(sql_query, job_config=job_config)
        results = query_job.result()
        rows = [dict(row) for row in results]
        return query_job.to_dataframe(), rows
    except Exception as e:
        console.log(f"[bold red]BigQuery error: {e}")


def format_conversations(conversations: List[Conversation]) -> List[Dict[str, str]]:
    """
    Formats a list of Conversation models into the expected message format.

    Args:
        conversations: A list of Conversation objects.

    Returns:
        A list of dictionaries representing messages in the desired format.
    """
    formatted_messages = []
    for conversation in conversations:
        formatted_messages.append(
            {"role": "assistant", "content": conversation.ai_content}
        )
        formatted_messages.append(
            {"role": "user", "content": conversation.user_content}
        )
    return formatted_messages


# Helper function to process and summarize results
def summarize_results(
    dataframe: pd.DataFrame,
    natural_query: str,
    conversations: Optional[List[Conversation]] = None,
) -> Optional[Dict[str, str | List[str]]]:
    """
    Summarizes the query results using GPT-4.
    """
    ctxt = build_context_analytics(natural_query)
    data_dict = dataframe.to_dict(orient="records")
    formatted_convos = None

    messages = [
        {"role": "system", "content": ctxt},
        {
            "role": "user",
            "content": f"Given this query: '{natural_query}', summarize the following data: {data_dict}",
        },
    ]
    if conversations:
        formatted_convos = format_conversations(conversations)
    if formatted_convos:
        messages.extend(formatted_convos)
    # Convert dataframe to a dict for GPT consumption
    response = client.beta.chat.completions.parse(
        model="gpt-4o-2024-08-06",
        messages=messages,
        response_format=DataAnalysis,
    )
    extracted_data = json.loads(response.choices[0].message.content)
    extracted_data["ai_context"] = messages[-1]
    extracted_data["user_message"] = messages[-2]
    console.log(extracted_data)
    return extracted_data


def start_conversation(user_content: str, ai_content: str) -> Conversation:
    conversation = create_conversation(user_content, ai_content)
    return conversation
