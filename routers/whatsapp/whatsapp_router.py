
from typing import Dict, List
from fastapi import APIRouter, Request, Response
from external_services.whatsapp import WhatsappService
from dotenv import load_dotenv
from os import environ
from routers.whatsapp.helpers import format_product_message, handle_whatsapp_data
from routers.whatsapp.schema import (
    MarketplaceProductNigeria,
    WhatsappDataExchange,
    WhatsappWebhookGetSchema,
    WhatsappWebhookPostSchema,
)
from settings import get_settings

load_dotenv()

router = APIRouter()
WHITELISTED_PHONE_NUMBER_IDS = ["403715826147338"]  # Phone number ids of the whitelisted phone numbers not actual phone numbers
WHITELISTED_BUSINESS_ACCOUNT_IDS = ["377250852134646"]  # Business account ids of the whitelisted business accounts
WHITELISTED_USER_NUMBERS = ["447843741891"]  # User numbers of the whitelisted users not actual phone numbers
WEBHOOK_VERIFY_TOKEN = environ.get("WEBHOOK_VERIFY_TOKEN")
settings = get_settings()
ACCESS_TOKEN = settings.GRAPH_API_ACCESS_TOKEN

whatsapp_service = WhatsappService(
    whitelisted_business_account_ids=WHITELISTED_BUSINESS_ACCOUNT_IDS,
    whitelisted_user_numbers=WHITELISTED_USER_NUMBERS,
    whitelisted_phone_number_ids=WHITELISTED_PHONE_NUMBER_IDS,
    webhook_verify_token=WEBHOOK_VERIFY_TOKEN,
    access_token=ACCESS_TOKEN
)


@router.post("/webhook")
async def whatsapp_webhook(request: Request):
    LIMIT = 10
    base64_image = None
    text = ""
    is_keyword_found = False
    request_json = await request.json()
    print(request_json, 'request_json')
    try:
        data = WhatsappWebhookPostSchema(**request_json)
        # print(data, 'data')
    except Exception as e:
        print('Invalid request', e)
        return Response(status_code=400, content="Invalid request")
    business_account_id = whatsapp_service.get_business_account_id(data.entry)
    phone_number_id = whatsapp_service.get_phone_number_id(data.entry)
    message = whatsapp_service.get_message(data.entry)
    if not message:
        return Response(status_code=400, content="No message found")
    if not whatsapp_service.is_whitelisted(business_account_id, phone_number_id, message.sender):
        return Response(status_code=403, content="Unauthorized business account or phone number")

    match message.type:
        case "image":
            base64_image, text = whatsapp_service.handle_image_message(message)

        case "text":
            keywords = ["help", "hello"]
            if any(keyword in message.text.body.lower() for keyword in keywords):
                whatsapp_service.send_message(
                    business_phone_number_id=phone_number_id,
                    to=message.sender,
                    is_template=True,
                    name="red_cloud_lens",
                    language="en"
                )
                is_keyword_found = True
            else:
                text = message.text.body
        case _:
            pass

    # Mark message as read
    whatsapp_service.mark_message_as_read(business_phone_number_id=phone_number_id, message_id=message.id)
    if not is_keyword_found:
        input_data = WhatsappDataExchange(
            query=text,
            limit=LIMIT,
            conversation_id=None,
            product_image=[base64_image] if base64_image else None
        )
        try:
            response = handle_whatsapp_data(input_data)
        except Exception as e:
            print(e, 'error')
            return Response(status_code=400, content="Error in processing: %s" % e)
        grouped_results: Dict[str, List[MarketplaceProductNigeria]] = {}
        for result in response.data.results:
            if result.external_id not in grouped_results:
                grouped_results[result.external_id] = []
            grouped_results[result.external_id].append(result)
        print(grouped_results.keys(), 'grouped_results')
        for result_id, results in grouped_results.items():
            whatsapp_service.send_text_message(
                business_phone_number_id=phone_number_id,
                to=message.sender,
                message=format_product_message(result_id, results),
                message_id=message.id)

        # Send result analysis
        whatsapp_service.send_text_message(
            business_phone_number_id=phone_number_id,
            to=message.sender,
            message=response.data.result_analysis or response.data.message,
            message_id=message.id)

    else:
        print("No message found")

    return Response(status_code=200, content="Message received")


@router.get("/webhook")
async def whatsapp_webhook_verification(request: Request):
    try:
        params = request.query_params._dict
        data = WhatsappWebhookGetSchema(
            **params
        )
        print(request, request.body)
    except Exception as e:
        print(e)
        return Response(status_code=400, content="Invalid request")
    verification = whatsapp_service.verify_webhook(data.mode, data.token, data.challenge)
    return Response(status_code=verification["status_code"], content=verification["content"])
