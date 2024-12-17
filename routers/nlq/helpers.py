import base64
import json
import os
from typing import Optional, Union

import requests
from dotenv import load_dotenv
from fastapi import UploadFile
from google.cloud import bigquery
from openai import OpenAI
from rich.console import Console

from external_services.vertex import VertexAIService
from routers.nlq.schemas import Text2SQL

load_dotenv()

console = Console()
bigquery_client = bigquery.Client(project=os.environ.get("GCP_PROJECT_ID", None))

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY", None))


def generate_bigquery_for_products(product_name):
    """Generates a BigQuery SQL query to search for products with at least one word from the given product name.

    Args:
        product_name: The product name to search for.

    Returns:
        A string containing the BigQuery SQL query.
    """

    words = product_name.split()
    conditions = [f"'Product Name' LIKE '%{word}%'" for word in words]
    where_clause = " OR ".join(conditions)

    query = f"""
      SELECT *
        FROM `marketplace_product_nigeria`
        WHERE {where_clause}
    """

    print(query)

    return query


def extract_code(input_string):
    """Extracts the code portion from a given string.

    Args:
        input_string: The input string in the format "Prefix_Code".

    Returns:
        The extracted code portion.
    """

    # Split the string by the underscore
    parts = input_string.split("_")

    # Return the second part, which is the code, enclosed in single quotes
    return f"'{parts[1]}"


def generate_gtin_sql(gtin, limit=10):
    """Generates a BigQuery SQL query from a string of SKUs.

    Args:
        skus_string: A List of Dict's with an SKU key.
        limit: limit for result.

    Returns:
        A string containing the BigQuery SQL query.
    """

    query = f"""
        SELECT *
        FROM `market_place_product_nigeria_mapping_table`
        WHERE 'GTIN' = "{gtin}" OR 'EAN' = "{gtin}"
        LIMIT {limit}
    """

    return query


def generate_bigquery_sql(sku_rows, limit=10):
    """Generates a BigQuery SQL query from a string of SKUs.

    Args:
        skus_string: A List of Dict's with an SKU key.
        limit: limit for result.

    Returns:
        A string containing the BigQuery SQL query.
    """

    all_skus = []

    for row in sku_rows:
        skus = row["SKU_STRING"].split(",")
        all_skus.extend(skus)

    print(all_skus)
    skus_formatted = ", ".join([f'"{sku}"' for sku in all_skus])
    print(skus_formatted)

    query = f"""
        SELECT *
        FROM `marketplace_product_nigeria`
        WHERE SKU IN ({skus_formatted})
        LIMIT {limit}
    """

    return query


def build_context_gtin(
    natural_query: str, product_name: Optional[str], total: Optional[int] = 10
) -> str:
    product_ctxt = (
        f"for product with a GTIN or an EAN '{product_name}' " if product_name else ""
    )
    return f"""
        You are an expert Text2SQL AI in the e-commerce domain 
        that takes a natural language query and translates it into a BigQuery SQL query. 
        Translate the query into a BigQuery SQL query {product_ctxt} in the database schema:
        `market_place_product_nigeria_mapping_table` (
            `Product Name` STRING NOT NULL,  
            `Top Category` STRING,  
            `Category Name` STRING,  
            `Country` STRING,  
            `Brand` STRING,  
            `SKU_STRING` STRING,  
            `GTIN` STRING,  
            `EAN` STRING,  
            `Mapping` STRING NOT NULL,  
            `Mapping Type` STRING NOT NULL
        )
        Your response should be formatted in the given structure 
        where sql_query is the translated BigQuery SQL query with a LIMIT of {total}. 
        If no natural language query is provided, return BigQuery SQL query {product_ctxt}.
        Favor OR operations over AND operations. Ensure the query selects all fields and the query is optimized for BigQuery performance.
    """


def build_context_nlq(
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
        where sql_query is the translated BigQuery SQL query with a LIMIT of {total}. 
        If no natural language query is provided, return BigQuery SQL query {product_ctxt}.
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
        where sql_query is the translated BigQuery SQL query with a LIMIT of {total}. 
        If no natural language query is provided, return BigQuery SQL query {product_ctxt}.
        Favor OR operations over AND operations. Ensure the query selects all fields and the query is optimized for BigQuery performance.
    """


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
        `market_place_product_nigeria_mapping_table` (
            `Product Name` STRING NOT NULL,  
            `Top Category` STRING,  
            `Category Name` STRING,  
            `Country` STRING,  
            `Brand` STRING,  
            `SKU_STRING` STRING,  
            `GTIN` STRING,  
            `EAN` STRING,  
            `Mapping` STRING NOT NULL,  
            `Mapping Type` STRING NOT NULL
        )
        Your response should be formatted in the given structure 
        where sql_query is the translated BigQuery SQL query with a LIMIT of {total}. 
        If no natural language query is provided, return BigQuery SQL query {product_ctxt}.
        Favor OR operations over AND operations. Ensure the query selects all fields and the query is optimized for BigQuery performance.
    """


# Helper: Parse natural language query
def parse_bigquery(
    natural_query: Optional[str],
    product_name: Optional[str],
    amount: Optional[int],
    sku_rows: Optional[dict],
    use_gtin: bool = True,
) -> Optional[str]:
    if not natural_query and not product_name:
        return None
    all_skus = []
    if sku_rows:
        for row in sku_rows:
            skus = row["SKU_STRING"].split(",")
            all_skus.extend(skus)

        print(all_skus)
        skus_formatted = ", ".join([f'"{sku}"' for sku in all_skus])
        print(skus_formatted)

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
        return extracted_data.get("sql_query")
    except (KeyError, json.JSONDecodeError) as e:
        console.log(f"Error parsing query: {e}")
        return None


def parse_query(
    natural_query: Optional[str],
    product_name: Optional[str],
    amount: Optional[int],
    use_gtin: bool = True,
) -> Optional[str]:
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


def detect_text(base64_encoded_image):
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


def request_image_inference(product_image: str):
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


def vertex_image_inference(image):
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
