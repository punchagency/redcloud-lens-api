import traceback
from typing import Any, Callable, Dict, List, Tuple

from fastapi import HTTPException
from pandas import DataFrame
import requests
from db.chromadb_store import ProductCatalog
from routers.nlq.helpers import azure_vision_service, detect_text, execute_bigquery, extract_code, generate_gtin_sql, generate_product_name_sql, parse_nlq_search_query, parse_sku_search_query, parse_whatsapp_sku_search_query, regular_chat, request_image_inference, summarize_results
from routers.nlq.schemas import MarketplaceProductNigeria
from routers.whatsapp.schema import FlowEndpointException, WhatsappFlowChipSelector, WhatsappNLQRequest
from routers.whatsapp.constants import country_currency_code
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
from cryptography.exceptions import InvalidTag
from base64 import b64encode, b64decode
import hmac
import hashlib
import json
from rich.console import Console
import logging
from typing import Optional
from routers.nlq.schemas import MarketplaceProductNigeria, NLQRequest
from db.helpers import create_conversation, get_conversation, save_message
from routers.whatsapp.schema import WhatsappDataExchange, WhatsappFlowChipSelector, WhatsappNLQResponse, WhatsappPayload, WhatsappProductImage, WhatsappResponse
console = Console()
logger = logging.getLogger("test-logger")
logger.setLevel(logging.DEBUG)
embedded_product_client = ProductCatalog()


def currency_formatter(price: float, country: str):
    return f"{country_currency_code.get(country, 'USD')}{'{:,.0f}'.format(price)}"


def format_product_message(id: str, products: List[MarketplaceProductNigeria]):
    available_quantity = sum(int(p.salable_quantity or 0) for p in products)
    product_prices = [p.product_price for p in products]
    result_string = f"""
    Product: {products[0].product_name}
Manufacturer: {products[0].manufacturer} 
Brand: {products[0].brand}
Available: {available_quantity if available_quantity else "No"} unit(s) available
Minimum Price: {currency_formatter(min(product_prices), products[0].country) if product_prices else "No price available"}
Maximum Price: {currency_formatter(max(product_prices), products[0].country) if product_prices else "No price available"}
Average Price: {currency_formatter((sum(product_prices) / len(product_prices)), products[0].country) if product_prices else "No price available"}
Sold by:
"""
    counter = 0
    for p in products:
        if (int(p.salable_quantity) > 0) and (p.seller_name != "N/A") and (p.product_price != "N/A") and (p.product_price != 0) and (p.seller_name.strip() != ""):
            counter += 1
            result_string += f"{counter}. {p.seller_name} - {currency_formatter(p.product_price, p.country)}\n"
    return result_string


def format_flow_chip_selector(query: str):
    return WhatsappFlowChipSelector(
        id='_'.join(query.lower().split(' ')),
        title=query,
        enabled=True
    )


def format_flow_chip_selector_from_list(items: List[str] | None):
    if not items:
        return []
    return [format_flow_chip_selector(item) for item in items]


def format_flow_chip_selector_from_list_of_dicts(items: List[dict]):
    return [format_flow_chip_selector(item["title"]) for item in items]


def decrypt_request(body: WhatsappNLQRequest, private_pem: str, passphrase: str):
    """
    Decrypts the request body using the provided private key and passphrase.
    """
    encrypted_aes_key = b64decode(body.encrypted_aes_key)
    encrypted_flow_data = b64decode(body.encrypted_flow_data)
    initial_vector = b64decode(body.initial_vector)

    # Load the private key
    private_key = serialization.load_pem_private_key(
        private_pem.encode(),
        password=passphrase.encode(),
        backend=default_backend()
    )

    # Decrypt the AES key
    try:
        decrypted_aes_key = private_key.decrypt(
            encrypted_aes_key,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
    except Exception as error:
        raise FlowEndpointException(
            421, "Failed to decrypt the request. Please verify your private key."
        ) from error

    # Separate flow data into body and authentication tag
    TAG_LENGTH = 16
    encrypted_flow_data_body = encrypted_flow_data[:-TAG_LENGTH]
    encrypted_flow_data_tag = encrypted_flow_data[-TAG_LENGTH:]

    # Decrypt the flow data
    try:
        cipher = Cipher(
            algorithms.AES(decrypted_aes_key),
            modes.GCM(initial_vector, encrypted_flow_data_tag),
            backend=default_backend()
        )
        decryptor = cipher.decryptor()
        decrypted_data = decryptor.update(encrypted_flow_data_body) + decryptor.finalize()
        decrypted_json = json.loads(decrypted_data.decode('utf-8'))
    except InvalidTag:
        raise FlowEndpointException(400, "Invalid authentication tag. Decryption failed.")
    print(decrypted_json, 'decrypted_json')
    return WhatsappPayload(
        decrypted_body=decrypted_json,
        aes_key_buffer=decrypted_aes_key,
        initial_vector_buffer=initial_vector
    )


def encrypt_response(response: dict, aes_key_buffer: bytes, initial_vector_buffer: bytes):
    """
    Encrypts the response using AES-GCM encryption with the provided AES key and a flipped initial vector.
    """
    # Flip the initialization vector
    flipped_iv = bytearray()
    for byte in initial_vector_buffer:
        flipped_iv.append(byte ^ 0xFF)

    # Encrypt the response data
    encryptor = Cipher(algorithms.AES(aes_key_buffer),
                       modes.GCM(flipped_iv)).encryptor()
    return b64encode(
        encryptor.update(json.dumps(response).encode("utf-8")) +
        encryptor.finalize() +
        encryptor.tag
    ).decode("utf-8")


def process_whatsapp_image_data(data: WhatsappProductImage) -> Optional[str]:
    try:
        cdn_file_response = requests.get(data.cdn_url)
        cdn_file = cdn_file_response.content
        # Step 3: Validate SHA256(cdn_file) == encrypted_hash
        if hashlib.sha256(cdn_file).digest() != b64decode(data.encryption_metadata.encrypted_hash):
            raise ValueError("Encrypted file hash validation failed!")

        # Step 4: Validate HMAC
        ciphertext, hmac10 = cdn_file[:-10], cdn_file[-10:]
        print(b64decode(data.encryption_metadata.iv))
        computed_hmac = hmac.new(
            b64decode(data.encryption_metadata.hmac_key),
            b64decode(data.encryption_metadata.iv) + ciphertext,
            hashlib.sha256,
        ).digest()
        if computed_hmac[:10] != hmac10:
            raise ValueError("HMAC validation failed!")

        # Step 5: Decrypt the media
        cipher = Cipher(
            algorithms.AES(b64decode(data.encryption_metadata.encryption_key)),
            modes.CBC(b64decode(data.encryption_metadata.iv)),
        )
        decryptor = cipher.decryptor()
        decrypted_data = decryptor.update(ciphertext) + decryptor.finalize()

        # Remove PKCS7 padding
        padding_len = decrypted_data[-1]
        decrypted_data = decrypted_data[:-padding_len]

        # Step 6: Validate decrypted media SHA256
        if hashlib.sha256(decrypted_data).digest() != b64decode(data.encryption_metadata.plaintext_hash):
            raise ValueError("Decrypted file hash validation failed!")

        base64_image = b64encode(decrypted_data).decode("utf-8")
        return base64_image
    except Exception as e:
        print(f"Error processing image: {str(e)}")

    return None


def convert_to_base64(response: WhatsappResponse) -> str:
    """Convert a WhatsappResponse object to a base64 encoded string.

    Args:
        response (WhatsappResponse): The response object to encode

    Returns:
        str: Base64 encoded string of the JSON response
    """
    try:
        json_str = response.model_dump_json()

        base64_bytes = b64encode(json_str.encode("utf-8"))
        return base64_bytes.decode("utf-8")

    except Exception as e:
        console.log(f"Error converting response to base64: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to encode response") from e


def handle_image_search(image_str: str | None) -> Tuple[str, str]:
    """
    Handle the image search process
    """

    search_text, gtin = "", ""
    if not image_str:
        return search_text, gtin
    THRESHOLD = 0.5
    steps: List[
        Tuple[Callable[[str], Any],
              Callable[[Any], Tuple[str, str]]]
    ] = [
        (detect_text,
         lambda result: (
             str(result["responses"][0]["fullTextAnnotation"]["text"]).replace("\n", " "),
             "")
         ),
        (azure_vision_service,
         lambda result: result.get("label", "_").split("_") if result.get("confidence", 0) > THRESHOLD else ("", "")),
        # (request_image_inference,
        #  lambda result: (result.get("Label", ""), ""))
    ]

    for index, (function, callback) in enumerate(steps):
        try:
            search_text, gtin = callback(function(image_str))
            if search_text or gtin:
                break
        except Exception as e:
            console.log(f"[bold red]error happened in step {index}: {e}")
    return search_text, gtin


def handle_whatsapp_data(data: WhatsappDataExchange) -> WhatsappResponse:
    chat = get_conversation(data.conversation_id)
    natural_query = data.query.strip()
    response = WhatsappNLQResponse(query=natural_query, next_screen=data.next_screen)
    product_image = data.product_image
    if isinstance(product_image, list):
        if product_image:
            product_image = product_image[0]
            if isinstance(product_image, WhatsappProductImage):
                product_image = process_whatsapp_image_data(product_image)

    if not (natural_query or product_image):
        response.message = "No query or image submitted."
        return WhatsappResponse(data=response, status="error")
    product_name, gtin = handle_image_search(product_image)
    print(product_name, gtin, 'product_name, gtin')
    limit = data.limit or 10
    try:
        # GET SKU
        skus: Dict[str, str | List[str]] = {}
        if gtin:
            sql_query = generate_gtin_sql(gtin, data.country, limit)
            nlq_query_job = execute_bigquery(sql_query)
            if nlq_query_job:
                try:
                    result_rows = nlq_query_job.result()
                    sku_rows = [dict(row) for row in result_rows]
                    for row in sku_rows:
                        skus[row["Mapping"]] = row["SKU_STRING"].split(",")
                except Exception as e:
                    console.log(f"[bold red]Error getting sku rows: {e}")
        search_text = product_name or natural_query
        if search_text and not skus:
            product_embeddings = embedded_product_client.perform_cosine_search([search_text], data.country, limit)
            for product_embedding in product_embeddings:
                for product in product_embedding:
                    skus[product.id] = product.sku

        if not skus:
            response.message = "No SKU found for your product/query in our catalog"
            return WhatsappResponse(data=response, status="error")
        sku_sql_queries = parse_whatsapp_sku_search_query(
            natural_query,
            product_name,
            limit,
            skus,
            data.country
        )
        # print(sku_sql_queries, 'sku_sql_queries')
        if not sku_sql_queries:
            response.message = "Sorry, we did not understand your search request. Please refine your search input and try again"
            return WhatsappResponse(data=response, status="error")
        sku_sql_in = sku_sql_queries.get("sql", '')
        sku_sql_where = sku_sql_queries.get("sql_query", '')
        sku_sql_query = f"{sku_sql_in}  {sku_sql_where.replace('WHERE', '')}"
        sku_suggested_queries: List[str] = sku_sql_queries.get("suggested_queries", [])
        response.sql_query = sku_sql_query
        response.suggested_queries = format_flow_chip_selector_from_list(sku_suggested_queries)
        try:
            sku_sql_query_job = execute_bigquery(sku_sql_query)
            if not sku_sql_query_job:
                response.message = "Sorry, we could not access the data you requested. Please try again later."
                return WhatsappResponse(data=response, status="error")
            dataframe: DataFrame = sku_sql_query_job.to_dataframe()

        except Exception as e:
            console.log(f"[bold red]Error getting sku rows: {e}")
            return WhatsappResponse(data=response, status="error")
        results = list(dataframe.T.to_dict().values())
        response.results = [MarketplaceProductNigeria(**product) for product in results]
        try:
            if dataframe.empty:
                summary = regular_chat(natural_query, conversations=chat)
            else:
                summary = summarize_results(dataframe[['Product Name', 'Product Price', 'Seller Name',
                                            'Manufacturer', 'Brand', 'Salable Quantity']], natural_query)
        except:
            summary = None
        if not summary:
            response.message = "Sorry! Could not generate analysis"
            return WhatsappResponse(data=response, status="error")
        else:
            result_analysis = summary.get("data_summary", None)
            analytics_queries: List[str] = summary.get("suggested_queries", [])
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
            response.analytics_queries = format_flow_chip_selector_from_list(analytics_queries)
            response.conversation_id = chat_id
            return WhatsappResponse(data=response)

    except Exception as e:
        logger.error("Error in nlq_endpoint: %s", traceback.format_exc())
        raise HTTPException(status_code=400, detail=str(e)) from e
