import base64
from dotenv import load_dotenv
from os import environ

import requests

from routers.whatsapp.schema import WhatsappWebhookEntrySchema, WhatsappWebhookMessageSchema
load_dotenv()

WEBHOOK_VERIFY_TOKEN = environ.get("WEBHOOK_VERIFY_TOKEN")
ACCESS_TOKEN = environ.get("GRAPH_API_ACCESS_TOKEN")


class WhatsappService:
    def __init__(
            self,
            webhook_verify_token=WEBHOOK_VERIFY_TOKEN,
            access_token=ACCESS_TOKEN,
            whitelisted_phone_number_ids: list[str] = [],
            whitelisted_business_account_ids: list[str] = [],
            whitelisted_user_numbers: list[str] = []
    ):
        self.webhook_verify_token = webhook_verify_token
        self.access_token = access_token
        self.whitelisted_phone_number_ids = whitelisted_phone_number_ids
        self.whitelisted_business_account_ids = whitelisted_business_account_ids
        self.whitelisted_user_numbers = whitelisted_user_numbers

    @staticmethod
    def get_business_account_id(entry: list[WhatsappWebhookEntrySchema]):
        if len(entry) == 0:
            return None
        return entry[0].id

    @staticmethod
    def get_user_number(entry: list[WhatsappWebhookEntrySchema]):
        if not entry or not entry[0].changes or len(entry[0].changes) == 0:
            return None
        statuses = entry[0].changes[0].value.statuses
        if not statuses or len(statuses) == 0:
            return None
        return statuses[0].recipient_id

    @staticmethod
    def get_phone_number_id(entry: list[WhatsappWebhookEntrySchema]):
        if not entry or not entry[0].changes or len(entry[0].changes) == 0:
            return None

        metadata = entry[0].changes[0].value.metadata
        print(metadata, 'metadata')
        if not metadata or not metadata.phone_number_id:
            return None

        return metadata.phone_number_id

    @staticmethod
    def get_message(entry: list[WhatsappWebhookEntrySchema]):
        if len(entry) == 0 or len(entry[0].changes) == 0 or len(entry[0].changes[0].value.messages) == 0:
            return None
        return entry[0].changes[0].value.messages[0]

    def retrieve_media(self, media_id: str):
        try:
            response = requests.get(f"https://graph.facebook.com/v21.0/{media_id}", headers={
                "Authorization": f"Bearer {self.access_token}",
            })
            return response.json()

        except Exception as e:
            print(e)
            return None

    def download_media(self, media_id: str) -> bytes:
        media = self.retrieve_media(media_id)
        if media:
            url = media.get("url", None)
            response = requests.get(url, headers={
                "Authorization": f"Bearer {self.access_token}",
            })
            return response.content
        return None

    def handle_image_message(self, message: WhatsappWebhookMessageSchema):
        media_id = message.image.id
        media = self.download_media(media_id)
        if media:
            base64_image = base64.b64encode(media).decode("utf-8")
            text = message.image.caption or ""
            return base64_image, text
        return None, ""

    def handle_text_message(self, message: WhatsappWebhookMessageSchema):
        text = message.text.body
        return text

    def is_phone_number_whitelisted(self, phone_number_id: str):
        return phone_number_id in self.whitelisted_phone_number_ids

    def is_business_account_whitelisted(self, business_account_id: str):
        return business_account_id in self.whitelisted_business_account_ids

    def is_user_number_whitelisted(self, user_number: str):
        return user_number in self.whitelisted_user_numbers

    def is_whitelisted(self, business_account_id: str, phone_number_id: str, user_number: str):
        return (
            self.is_business_account_whitelisted(business_account_id) and
            self.is_phone_number_whitelisted(phone_number_id) and
            self.is_user_number_whitelisted(user_number)
        )

    def verify_webhook(self, mode, token, challenge):
        if mode == "subscribe" and token == self.webhook_verify_token:
            return {
                "content": challenge,
                "status_code": 200
            }
        else:
            return {
                "content": "Unauthorized",
                "status_code": 403
            }

    def mark_message_as_read(self, business_phone_number_id, message_id):
        try:
            response = requests.post(f"https://graph.facebook.com/v21.0/{business_phone_number_id}/messages", headers={
                "Authorization": f"Bearer {self.access_token}",
            }, data={
                "messaging_product": "whatsapp",
                "status": "read",
                "message_id": message_id
            })
            print(response.json())
            return response.json()
        except Exception as e:
            print(e)
            return None

    def send_text_message(self, business_phone_number_id,  to: str, message: str, message_id: str):
        try:
            response = requests.post(f"https://graph.facebook.com/v18.0/{business_phone_number_id}/messages", headers={
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json"
            }, json={
                "messaging_product": "whatsapp",
                "to": to,
                "text": {
                    "body": message
                },
                "context": {
                    "message_id": message_id
                }
            })
            return response.json()
        except Exception as e:
            print(e)
            return None

    def send_message(self, business_phone_number_id, to: str, is_template: bool, name: str, language: str):
        try:
            response = requests.post(f"https://graph.facebook.com/v21.0/{business_phone_number_id}/messages", headers={
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json"
            }, json={
                "messaging_product": "whatsapp",
                "to": to,
                "type": "template",
                "access_token": self.access_token,
                "template": {
                    "name": name,
                    "language": {"code": language},
                    "components": [
                        {
                            "type": "button",
                            "sub_type": "flow",
                            "index": "0",
                            "parameters": [
                                {
                                    "type": "action",
                                    "action": {
                                        "flow_token": "1234"
                                    }
                                }
                            ]
                        }
                    ]
                }
            })
            return response.json()
        except Exception as e:
            print(e)
            return None
