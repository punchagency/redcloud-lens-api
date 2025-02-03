import base64

import json
import logging
import os
import re
from typing import Dict, List, Optional, Union

import pandas as pd
import requests
from fastapi import UploadFile
from google.cloud import bigquery
from openai import OpenAI
from rich.console import Console

from db.helpers import create_conversation
from db.store import Conversation
from external_services.vertex import VertexAIService
from routers.nlq.schemas import DataAnalysis, Text2SQL
from settings import get_settings
import json
logger = logging.getLogger("test-logger")
logger.setLevel(logging.DEBUG)
settings = get_settings()

console = Console()
bigquery_client = bigquery.Client(project=settings.GCP_PROJECT_ID)

client = OpenAI(api_key=settings.OPENAI_API_KEY)

CATEGORIES = """
Red101 Market,
Tea & Infusions,
Mobile Phones,
Bar Soap,
Cookies,
Deodorant,
Bath & Body,
Water,
Biscuits,
Gin,
Whiskey,
Liqueurs,
Pasta & Noodles,
Feminine Sanitary Supplies,
Food,
Studio Light & Flash Accessories,
Seasonings & Spices,
Laundry Detergent,
Laundry Supplies,
Household Disinfectants,
Lotions & Moisturisers,
Rice,
Crackers,
Fizzy Drinks,
Perfume & Cologne,
Hair Extensions,
Screen Protectors,
Washing-up Detergent & Soap,
Juice,
Household Insect Repellents,
Cooking Oils,
Personal Care,
Milk,
Wine,
Household Supplies,
Cocktail Mixes,
Haircare,
Bleach,
Conditioner,
Coffee,
Skincare,
Mobile Phone Accessories,
Baby Formula,
Baby Food,
Non-Dairy Milk,
Liquor & Spirits,
Household Cleaning Supplies,
Sweets & Chocolate,
Toilet Cleaners,
Shampoo,
Mayonnaise,
Vodka,
Petroleum Jelly,
Fruit-Flavoured Drinks,
Sports & Energy Drinks,
Yoghurt,
Toiletries,
Nappies,
Pesticides,
Canned & Powdered Milk,
Feminine Pads & Protectors,
Tomato Paste,
Body Wash,
Glass & Surface Cleaners,
Prepared Food,
Herbs & Spices,
Appetisers & Snacks,
Beer,
Butter & Margarine,
Dishwasher Cleaners,
Lollipops,
Flavoured Sparkling Water,
Powdered Beverage Mixes,
Foundations & Concealers,
Tinned Seafood,
Cereals & Granola,
Hot Chocolate,
Toners & Astringents,
Medicines & Drugs,
Healthcare,
Respiratory Care,
Vitamins & Supplements,
Paper Serviettes,
Facial Tissues,
Toilet Paper,
Kitchen Paper,
Lighters & Matches,
Grain & Cereals,
Hair Removal,
Beverages,
Air Fresheners,
Wafers,
Bread & Buns,
Diapering,
Liquid Hand Soap,
Hand Sanitisers,
Adhesive Tapes,
Yeast,
Scanners,
Toner & Inkjet Cartridges,
Printers; Photocopiers & Fax Machines,
Toothpaste,
Malt,
Condoms,
Rum,
Bitters,
Salad Dressings,
Sugar & Sweeteners,
Ketchup,
Hair Colouring,
All-Purpose Cleaners,
Glass Cleaners,
Muti-surface Cleaners,
Car Wash Solutions,
Fruit and Nut Snacks,
Facial Cleansers,
Nut Butters,
Hair Permanents & Straighteners,
Candies,
Baby Bathing,
Hair Oil,
Toner & Inkjet Cartridge Refills,
Masonry Consumables,
Flavoured Alcoholic Beverages,
Mobile Phone Cases,
Headphones & Headsets,
Medical Masks,
Medical Supplies,
Popcorn,
Flour,
Pastries & Scones,
Business & Industrial,
Candles,
Perfumery,
Antiseptics & Cleaning Supplies,
Oats - Grits & Oatmeal,
Baby & Toddler Food,
Meat; Seafood & Eggs,
Cooking & Baking Ingredients,
Body Oil,
USB Flash Drives,
Conductivity Gels & Lotions,
Baby Gift Sets,
Baby Wipes,
Salt,
Baking Powder,
Skin Insect Repellent,
Headphones,
Adult Diaper,
Cream,
USB Adapters,
False Eyelashes,
Body Powder,
Face Powders,
Spirits,
Baby Cereal,
Toothbrushes,
Fabric Refreshers,
Cement, Mortar & Concrete Mixes,
Cement,
Mortar & Concrete Mixes,
Adult Hygienic Wipes,
Baby and Toddler,
Towels,
Contact Lenses,
Brandy,
Cheese Puffs,
LED Light Bulbs,
Alcoholic Beverages,
Kitchen Appliance Accessories,
Wireless Routers,
Hubs & Switches,
Razors & Razor Blades,
Crisps,
Powdered Hand Soap,
Crafting Adhesives & Magnets,
Tequila,
Corn,
Dairy Products,
Wart Removers,
Mouthwash,
Condiments & Sauces,
Tub & Tile Cleaners,
Baby Health,
Tissue Paper,
Sugar & Sweetener,
Paint,
Snacks,
Peas,
Tinned Beans,
Couscous,
Cosmetics,
Batteries,
Lip Liner,
Compressed Skincare-Mask Sheets,
"""

SQL_REFINEMENT_RULES = """
        **General Refinement Instructions:**

        1. **Leverage Category Information:** Utilize `Category Name` and `Top Category` to filter results and improve accuracy. If searching for a specific product type (e.g., "biscuit"), filter results based on relevant categories (e.g., "Biscuits").
        2. **Handle Ambiguity:** If the `product_name` is ambiguous (e.g., "Apple"), consider different interpretations (e.g., "Apple (fruit)," "Apple (company)").
        3. **Prioritize Similar Matches:** If possible, prioritize queries that include similar matches for the product name in fields like `Product Name`, `Brand`, or `Manufacturer`.
        4. **Moderate Search Queries:** If the searching for a product, search only for that product. Do not include similar products/categories in the query.
        """
SKU_REFINEMENT_RULES = """
        **General Refinement Instructions:**


        1. **Exact Field Matching:** `Quantity`,`Product Price` are the only fields you can filter/search on. Dont use = operator unless it is explicitly mentioned in the query. Instead use >, <, >=, <= operators.
        2. **Do not search product names:** Do not search for `Product Name` or product names in the query.
        3. **Never include product names:** Do not include product names in the query.eg `Product Name` should not be in the query at any point.It is prohibited.
        4. **Do not search for brand names:** Do not search for `Brand` in the query.Eg `Brand` should not be in the query at any point.It is prohibited.
        5. **Do not search for category names:** Do not search for `Category Name` in the query.Eg `Category Name` should not be in the query at any point.It is prohibited.
        6. **Do not search for top category names:** Do not search for `Top Category` in the query.Eg `Top Category` should not be in the query at any point.It is prohibited.
        7. **Remember allowed fields:** `Quantity`,`Product Price` are the only fields you can filter/search on.Every other field is prohibited.
        8. **Do not add limits:** Do not add a limit to the query.
        """

NIGERIA_PRODUCT_TABLE = """
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
"""

NON_NIGERIA_PRODUCT_TABLE = """
`marketplace_product_except_nigeria` (
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
"""
SKU_TABLE_NG = "market_place_product_nigeria_mapping_table"
SKU_TABLE_NON_NG = "marketplace_product_except_nigeria_sku_aggregate_2"


def split_on_multiple_separators(text, separators):
    """
    Splits a string on multiple separators.

    Args:
        text: The string to split.
        separators: A list of separators to split on.

    Returns:
        A list of the split strings.
    """
    pattern = "|".join(re.escape(sep) for sep in separators)
    return re.split(pattern, text)


def extract_code(input_string: str) -> str:
    """Extracts the code portion from a given string.

    Args:
        input_string: The input string in the format "Prefix_Code".

    Returns:
        The extracted code portion.
    """

    parts = input_string.split("_")

    return f"'{parts[1]}"


def generate_product_name_sql(product_name: str, country: str, limit=10) -> str:
    """Generates a BigQuery SQL query to search for products with at least one word from the given product name.

    Args:
        product_name: The product name to search for.
        country: The country to search for.

    Returns:
        A string containing the BigQuery SQL query.
    """
    separators = [",", ";", ":", "-", " "]

    words = split_on_multiple_separators(product_name, separators)
    # print(words)  # Output: ['This', 'is', 'a', 'string', 'with', 'multiple', 'separators', '']

    conditions = [f"LOWER(`Product Name`) LIKE '%{word.lower()}%'" for word in words]
    where_clause = " OR ".join(conditions)

    query = f"""
      SELECT *
        FROM `{SKU_TABLE_NG if country == 'Nigeria' else SKU_TABLE_NON_NG}`
        WHERE {where_clause}
        LIMIT {limit}
    """
    return query


def generate_gtin_sql(gtin: str, country: str, limit=10) -> str:
    """Generates a BigQuery SQL query from a string of SKUs.

    Args:
        gtin: A gtin string.
        country: The country to search for.
        limit: limit for result.

    Returns:
        A string containing the BigQuery SQL query.
    """

    query = f"""
        SELECT *
        FROM `{SKU_TABLE_NG if country == 'Nigeria' else SKU_TABLE_NON_NG}`
        WHERE Mapping = "{gtin}"
        LIMIT {limit}
    """

    return query


def build_context_nlq(
    product_name: Optional[str],
    country: Optional[str] = None,
    total: Optional[int] = 10,
) -> str:
    """Builds a context string for natural language query processing.

    Args:
        product_name: Optional product name to include in context.
        country: Optional country filter, defaults to None.
        total: Optional result limit, defaults to 10.

    Returns:
        str: A formatted context string for the AI model to process the natural language query.
    """
    product_ctxt = (
        f"to search for products with at least a word from '{product_name}' in their name when a case insensitive search is performed"
        if product_name
        else ""
    )

    return f"""
        You are an expert Text2SQL AI in the e-commerce domain 
        that takes a natural language query and translates it into a BigQuery SQL query. 
        Translate the query into a BigQuery SQL query {product_ctxt} for the database:
        {NIGERIA_PRODUCT_TABLE if country == "Nigeria" else NON_NIGERIA_PRODUCT_TABLE}
        These are the category names:
        {CATEGORIES}
        Your response should be formatted in the given structure 
        where sql_query is the translated BigQuery SQL query with a LIMIT of {total},
        suggested_queries is a list of similar or refined natural language queries the user can use instead in their next search.
        If no natural language query is provided, return  {'BigQuery SQL query {product_ctxt}' or "suggested_queries"}.
        Favor OR operations over AND operations. Ensure the query selects all fields and the query is optimized for BigQuery performance.
        The clause should begin with AND keyword if an identifier is used in clause.
        If the natural language query looks malicious, requests personal information about users or company staff or is destructive, return nothing for sql_query but return suggested queries for finding coca cola products for suggested_queries.    
        
        {SQL_REFINEMENT_RULES}
        """


def build_context_nlq_sku(
    country: Optional[str] = None,
) -> str:
    """Builds a context string for natural language query processing.

    Args:
        country: Optional country filter, defaults to None.

    Returns:
        str: A formatted context string for the AI model to process the natural language query.
    """
#  These are the category names:
#         {CATEGORIES}
    return f"""
        You are an expert Text2SQL AI in the e-commerce domain 
        that takes a natural language query and translates it into a BigQuery SQL clause. 
        Translate the natural query into a BigQuery SQL conditional clause that can be used to complete an sql query similar to
        'SELECT * FROM `marketplace_product_nigeria` WHERE SKU IN ("BNE-021", "DTS-058", "SGL-022")'. 
        the database schema:
        {NIGERIA_PRODUCT_TABLE if country == "Nigeria" else NON_NIGERIA_PRODUCT_TABLE}.
        Your response should be formatted in the given structure 
        where sql_query is the translated conditional clause,
        suggested_queries is a list of similar or refined natural language queries the user can use instead in their next search.
        Begin the clause with 'AND' keyword if clause begins with an identifier
        If no natural language query is provided, return only suggested_queries.
        Favor OR operations over AND operations. Ensure the clause is optimized for BigQuery performance.
        If the natural language query looks malicious, requests personal information about users or company staff or is destructive, return nothing for sql_query but return suggested queries for finding coca cola products for suggested_queries.

        {SQL_REFINEMENT_RULES}
    """


def build_whatsapp_context_nlq_sku(
    country: Optional[str] = None,
) -> str:
    """Builds a context string for natural language query processing.

    Args:
        country: Optional country filter, defaults to None.

    Returns:
        str: A formatted context string for the AI model to process the natural language query.
    """
#  These are the category names:
#         {CATEGORIES}
    return f"""
        You are an expert Text2SQL AI in the e-commerce domain 
        that takes a natural language query and translates it into a BigQuery SQL clause. 
        Translate the natural query into a BigQuery SQL conditional clause that can be used to complete an sql query similar to
        'SELECT * FROM `marketplace_product_nigeria` WHERE SKU IN ("BNE-021", "DTS-058", "SGL-022")'. 
        the database schema:
        {NIGERIA_PRODUCT_TABLE if country == "Nigeria" else NON_NIGERIA_PRODUCT_TABLE}.
        Your response should be formatted in the given structure 
        where sql_query is the translated conditional clause,
        suggested_queries is a list of similar or refined natural language queries the user can use instead in their next search.
        Begin the clause with 'AND' keyword if clause begins with an identifier
        If no natural language query is provided, return only suggested_queries.
        Favor OR operations over AND operations. Ensure the clause is optimized for BigQuery performance.
        If the natural language query looks malicious, requests personal information about users or company staff or is destructive, return nothing for sql_query but return suggested queries for finding coca cola products for suggested_queries.

        {SKU_REFINEMENT_RULES}
    """


def parse_sku_search_query(
    natural_query: Optional[str],
    product_name: Optional[str],
    amount: Optional[int],
    sku_rows: List[str],
    country: Optional[str] = None,
) -> Optional[Dict[str, str | List[str]]]:
    """Parses a natural language query for SKUs.

    Args:
        natural_query: The natural language query string to process.
        product_name: Optional product name to include in context.
        sku_rows: Optional dictionary of SKUs.
        country: Optional country filter, defaults to None.
        use_gtin: Optional boolean flag to use GTIN, defaults to True.

    Returns:
        Optional[Dict[str, str | List[str]]]: A dictionary containing the parsed query results.
    """
    if not natural_query and not product_name:
        return None
    sql = None
    if sku_rows:
        skus_formatted = ", ".join([f'"{sku}"' for sku in sku_rows])
        sql = f"SELECT * FROM `{'marketplace_product_nigeria' if country == 'Nigeria' else 'marketplace_product_except_nigeria_sku_aggregate'}` WHERE SKU IN ({skus_formatted}) "

        context = build_context_nlq_sku(country=country)
    else:
        context = build_context_nlq(product_name, country=country, total=amount)

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
        if sku_rows:
            extracted_data["sql"] = sql
        return extracted_data
    except (KeyError, json.JSONDecodeError) as e:
        console.log(f"Error parsing query: {e}")
        return None


def parse_whatsapp_sku_search_query(
    natural_query: Optional[str],
    product_name: Optional[str],
    amount: Optional[int],
    sku_rows: Dict[str, str | List[str]],
    country: Optional[str] = None,
) -> Optional[Dict[str, str | List[str]]]:
    """Parses a natural language query for SKUs.

    Args:
        natural_query: The natural language query string to process.
        product_name: Optional product name to include in context.
        sku_rows: Optional dictionary of SKUs.
        country: Optional country filter, defaults to None.
        use_gtin: Optional boolean flag to use GTIN, defaults to True.

    Returns:
        Optional[Dict[str, str | List[str]]]: A dictionary containing the parsed query results.
    """
    if not natural_query and not product_name:
        return None
    sql = None
    if sku_rows:
        # Convert external mapping to SQL-friendly format
        cte_values = " UNION ALL ".join(
            [f"SELECT '{group}' AS external_id, '{sku}' AS SKU" for group, skus in sku_rows.items() for sku in skus]
        )

        # List of SKUs to filter in the query
        skus_formatted = ", ".join([f"'{sku}'" for skus in sku_rows.values() for sku in skus])

        # Final SQL Query
        sql = f"""
        WITH external_mapping AS ({cte_values})
        SELECT em.external_id, p.*
        FROM `{'marketplace_product_nigeria' if country == 'Nigeria' else 'marketplace_product_except_nigeria_sku_aggregate'}` p
        JOIN external_mapping em ON p.SKU = em.SKU
        WHERE p.SKU IN ({skus_formatted})
        ORDER BY em.external_id;
        """
        context = build_whatsapp_context_nlq_sku(country=country)
    else:
        context = build_context_nlq(product_name, country=country, total=amount)

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
        if sku_rows:
            extracted_data["sql"] = sql
        return extracted_data
    except (KeyError, json.JSONDecodeError) as e:
        console.log(f"Error parsing query: {e}")
        return None


def parse_nlq_search_query(
    natural_query: Optional[str],
    product_name: Optional[str],
    amount: Optional[int],
    country: Optional[str] = None,
) -> Optional[Dict[str, str | List[str]]]:
    """Parses a natural language query for search.

    Args:
        natural_query: The natural language query string to process.
        product_name: Optional product name to include in context.
        amount: Optional result limit, defaults to 10.
        country: Optional country filter, defaults to None.
        use_gtin: Optional boolean flag to use GTIN, defaults to True.

    Returns:
        Optional[Dict[str, str | List[str]]]: A dictionary containing the parsed query results.
    """
    if not natural_query and not product_name:
        return None

    context = build_context_nlq(product_name, country=country, total=amount)

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
        return extracted_data
    except (KeyError, json.JSONDecodeError) as e:
        console.log(f"Error parsing query: {e}")
        return None


def process_product_image(image: Union[str, UploadFile]) -> Optional[str]:
    """Processes a product image.

    Args:
        image: The image to process.

    Returns:
        Optional[str]: A base64 encoded image.
    """
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
    """Detects text in a base64 encoded image using Google Cloud Vision API.

    Args:
        base64_encoded_image (str): The base64 encoded image to analyze.

    Returns:
        Dict: The response from the Vision API containing detected text annotations.
            On success, returns a dictionary with text detection results.
            On failure, returns None.

    Raises:
        HTTPException: If there is an error making the API request.
    """

    request_body = {
        "requests": [
            {
                "image": {"content": base64_encoded_image},
                "features": [{"type": "TEXT_DETECTION"}],
            }
        ]
    }

    project_id = os.environ.get("GCP_PROJECT_ID", None)
    access_token = os.environ.get("GCP_AUTH_TOKEN", None)
    api_key = os.environ.get("GCP_API_KEY", None)
    headers = {
        # "Authorization": f"Bearer {access_token}",
        # "x-goog-user-project": project_id,
        "X-goog-api-key": api_key,
        "Content-Type": "application/json; charset=utf-8",
    }

    url = "https://vision.googleapis.com/v1/images:annotate"

    response = requests.post(url, headers=headers, json=request_body, timeout=30)
    if response.status_code == 200:
        resp = response.json()
        return resp
    return None


def request_image_inference(product_image: str) -> Dict:
    """Requests image inference from a remote API.

    Args:
        product_image: The base64 encoded image to analyze.

    Returns:
        Dict: The response from the API containing the inference results.
    """
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
    result = response.json()
    if result["status"] != "error":
        product_name = result.get("result")
    return product_name


def vertex_image_inference(image: str) -> Dict:
    """Requests image inference from a remote API.

    Args:
        image: The base64 encoded image to analyze.

    Returns:
        Dict: The response from the API containing the inference results.
    """
    image_result = None
    endpoint_id = "793057945905528832"
    project_id = "225990659434"

    service = VertexAIService(project_id=project_id, endpoint_id=endpoint_id)

    image_path = "uploaded_img.png"

    result = service.process_and_classify_image(image, image_path)
    if result:
        image_result = result
    return image_result


def build_context_chat() -> str:
    """Builds a context string for chat processing.

    Args:

    Returns:
        str: A formatted context string for the AI model to process the natural language query.
    """

    return """
        You are a state of the art customer care assistant for an e-commerce platform called redcloud. 
        You assist customers with information to help them find what they are looking for.
        Your response should be formatted in the given structure 
        where data_summary is a helpful analytics or summary of the given products or 
        general response to user input, and
        suggested_queries is a list of similar or refined natural language queries the user can use to get more useful insights their next search.
        Use friendly and non technical words respond as a representative of the redcloud platform.
        If the natural language query looks malicious, requests personal information about users or company staff or is destructive, return a witty response telling the user to instead find a bottle of coke for data_summary and return suggested queries to find coca cola products for suggested_queries.

    """


def build_context_analytics() -> str:
    """Builds a context string for analytics processing.

    Args:

    Returns:
        str: A formatted context string for the AI model to process the natural language query.
    """

    return """
        You are a state of the art customer care assistant for an e-commerce platform called redcloud. 
        You assist redcloud customers with information to help them find what they are looking for.
        Your response should be formatted in the given structure 
        where data_summary is a helpful analytics or summary of the given products or 
        general response to user input, and
        suggested_queries is a list of similar or refined natural language queries the user can use to get more useful insights their next search.
        Use friendly and non technical words, and respond as a representative of the redcloud platform.
        If the natural language query looks malicious, requests personal information about users or company staff or is destructive, return a witty response telling the user to instead find a bottle of coke for data_summary and return suggested queries to find coca cola products for suggested_queries.

    """


def build_context_query(
    product_name: Optional[str] = None, total: Optional[int] = 10
) -> str:
    """Builds a context string for query processing.

    Args:
        product_name: Optional product name to include in context.
        total: Optional result limit, defaults to 10.

    Returns:
        str: A formatted context string for the AI model to process the natural language query.
    """
    product_ctxt = (
        f"to search for products with at least a word from '{product_name}' in their name when a case insensitive search is performed"
        if product_name
        else ""
    )

    prod_search = f"BigQuery SQL query {product_ctxt}"
    suggested_search = "suggested_queries"

    ctxt = f"""
        You are an expert SQL generator for BigQuery the following database:
        {NIGERIA_PRODUCT_TABLE}
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


def gpt_generate_sql(natural_query: str) -> Optional[Dict[str, str | List[str]]]:
    """Generates SQL using GPT-4.

    Args:
        natural_query: The natural language query string to process.

    Returns:
        Optional[Dict[str, str | List[str]]]: A dictionary containing the parsed query results.
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
    # console.log(extracted_data)
    return extracted_data


def execute_bigquery(sql_query: str) -> bigquery.QueryJob | None:
    """Executes a SQL query on BigQuery and returns the results as a DataFrame.

    Args:
        sql_query: The SQL query to execute.

    Returns:
        bigquery.QueryJob: The results of the query.
    """
    default_dataset = "snowflake_views"

    job_config = bigquery.QueryJobConfig(
        default_dataset=f"{bigquery_client.project}.{default_dataset}",
        # dry_run=True
    )

    try:
        query_job = bigquery_client.query(sql_query, job_config=job_config)
        return query_job
    except Exception as e:
        console.log(f"[bold red]BigQuery error: {e}")
        return None


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
    """Processes and summarizes results using GPT-4.

    Args:
        dataframe: The DataFrame containing the results to summarize.
        natural_query: The natural language query string to process.
        conversations: Optional list of Conversation objects.

    Returns:
        Optional[Dict[str, str | List[str]]]: A dictionary containing the summarized results.
    """
    ctxt = build_context_analytics()
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

    response = client.beta.chat.completions.parse(
        model="gpt-4o-2024-08-06",
        messages=messages,
        response_format=DataAnalysis,
    )
    extracted_data = json.loads(response.choices[0].message.content)
    extracted_data["ai_context"] = messages[-1]
    extracted_data["user_message"] = messages[-2]
    # console.log(extracted_data)
    return extracted_data


# Helper function to process and continue chat without sql
def regular_chat(
    natural_query: str,
    conversations: Optional[List[Conversation]] = None,
) -> Optional[Dict[str, str | List[str]]]:
    """Chats with ctxt using GPT-4.

    Args:
        natural_query: The natural language query string to process.
        conversations: Optional list of Conversation objects.

    Returns:
        Optional[Dict[str, str | List[str]]]: A dictionary containing the chat results.
    """
    ctxt = build_context_chat()
    formatted_convos = None

    messages = [
        {"role": "system", "content": ctxt},
        {
            "role": "user",
            "content": natural_query,
        },
    ]
    if conversations:
        formatted_convos = format_conversations(conversations)
    if formatted_convos:
        messages.extend(formatted_convos)

    response = client.beta.chat.completions.parse(
        model="gpt-4o-2024-08-06",
        messages=messages,
        response_format=DataAnalysis,
    )
    extracted_data = json.loads(response.choices[0].message.content)
    extracted_data["ai_context"] = messages[-1]
    extracted_data["user_message"] = messages[-2]
    return extracted_data


def start_conversation(user_content: str, ai_content: str) -> Conversation:
    """Starts a conversation.

    Args:
        user_content: The user's message.
        ai_content: The AI's response.

    Returns:
        Conversation: The conversation object.
    """
    conversation = create_conversation(user_content, ai_content)
    return conversation


def azure_vision_service(
    base64_image: str,
):
    """Processes an image using Azure Vision API.

    Args:
        base64_image: The base64 encoded image to process.

    Returns:
        Dict: The response from the Azure Vision API containing the inference results.
    """
    from external_services.azure_vision import AzureVisionService

    service = AzureVisionService(
        prediction_key=settings.VISION_PREDICTION_KEY,
        endpoint=settings.VISION_PREDICTION_ENDPOINT,
        project_id=settings.VISION_PROJECT_ID,
        publish_iteration_name=settings.VISION_ITERATION_NAME,
    )

    result = service.process_and_classify_image(base64_image=base64_image)
    if result:
        return result
    return None
