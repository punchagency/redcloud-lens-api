from datetime import datetime
from typing import Any, List, Literal, Optional, Union
from pydantic import BaseModel, Field


class WhatsappWebhookGetSchema(BaseModel):
    mode: str = Field(alias="hub.mode")
    token: str = Field(alias="hub.verify_token")
    challenge: str = Field(alias="hub.challenge")


class WhatsappWebhookMessageTextSchema(BaseModel):
    body: str


class WhatsappWebhookMessageImageSchema(BaseModel):
    caption: Optional[str] = Field(default=None)
    mime_type: str
    sha256: str
    id: str


class WhatsappWebhookMessageSchema(BaseModel):
    sender: str = Field(alias="from")
    id: str
    text: Optional[WhatsappWebhookMessageTextSchema] = Field(default=None)
    type: Literal["text", "image", "audio", "video", "document", "sticker", "location", "contact", "reaction", "interactive", "system"]
    timestamp: str
    image: Optional[WhatsappWebhookMessageImageSchema] = Field(default=None)


class WhatsappWebhookContactProfileSchema(BaseModel):
    name: str


class WhatsappWebhookContactSchema(BaseModel):
    profile: WhatsappWebhookContactProfileSchema
    wa_id: str


class WhatsappWebhookMetadataSchema(BaseModel):
    phone_number_id: Optional[str] = Field(default=None)
    display_phone_number: Optional[str] = Field(default=None)


class WhatsappWebhookConversationOriginSchema(BaseModel):
    type: Literal["service", "marketing"]


class WhatsappWebhookConversationSchema(BaseModel):
    id: str
    expiration_timestamp: Optional[str] = Field(default=None)
    origin: WhatsappWebhookConversationOriginSchema


class WhatsappWebhookPricingSchema(BaseModel):
    billable: bool
    pricing_model: Any
    category: Literal["service", "marketing"]


class WhatsappWebhookStatusSchema(BaseModel):
    id: str
    status: Literal["sent", "delivered", "read"]
    timestamp: str
    recipient_id: str
    conversation: WhatsappWebhookConversationSchema
    pricing: WhatsappWebhookPricingSchema


class WhatsappWebhookValueSchema(BaseModel):
    messages: Optional[list[WhatsappWebhookMessageSchema]] = Field(default=[])
    metadata: Optional[WhatsappWebhookMetadataSchema] = Field(default=None)
    contacts: Optional[list[WhatsappWebhookContactSchema]] = Field(default=[])
    messaging_product:  Optional[Literal["whatsapp"]] = Field(default=None)
    statuses: Optional[list[WhatsappWebhookStatusSchema]] = Field(default=[])
    events: Optional[str] = Field(default=None)
    flow_id: Optional[str] = Field(default=None)
    old_status: Optional[str] = Field(default=None)
    new_status: Optional[str] = Field(default=None)
    message: Optional[str] = Field(default=None)


class WhatsappWebhookChangeSchema(BaseModel):
    value: WhatsappWebhookValueSchema
    field: Literal["messages", "flows"]


class WhatsappWebhookEntrySchema(BaseModel):
    id: str  # business account id
    changes: list[WhatsappWebhookChangeSchema]


class WhatsappWebhookPostSchema(BaseModel):
    entry: list[WhatsappWebhookEntrySchema]
    object: Literal["whatsapp_business_account"]


class WhatsappEncryptionMetadata(BaseModel):
    encryption_key: str
    hmac_key: str
    hmac: str
    iv: str
    plaintext_hash: str
    encrypted_hash: str


class WhatsappProductImage(BaseModel):
    file_name: str
    media_id: str
    cdn_url: str
    encryption_metadata: WhatsappEncryptionMetadata


class WhatsappDataExchange(BaseModel):
    query: str
    limit: int
    conversation_id: Optional[str] = None
    product_image: Optional[Union[List[WhatsappProductImage], List[str], str]] = Field(
        default=[], description="Product image data that can be a list of WhatsappProductImage objects, list of base64 strings, or a single base64 string")
    country: Optional[str] = "Nigeria"


class WhatsappBaseModel(BaseModel):
    action: Literal["send_message", "send_image", "send_product_image", "ping", 'data_exchange']
    data: Optional[WhatsappDataExchange] = None
    screen_name: Optional[str] = None
    flow_token: Optional[str] = None


class WhatsappPayload(BaseModel):
    decrypted_body: WhatsappBaseModel
    aes_key_buffer: Optional[bytes] = None
    initial_vector_buffer: Optional[bytes] = None


class WhatsappNLQRequest(BaseModel):
    encrypted_flow_data: Optional[str] = None
    encrypted_aes_key: Optional[str] = None
    initial_vector: Optional[str] = None


class NLQRequest(BaseModel):
    query: Optional[str] = None
    conversation_id: Optional[str] = None
    product_image: Optional[str] = None
    country: Optional[str] = "Nigeria"


class CategoryRequest(BaseModel):
    category: str


class MarketplaceProductNigeria(BaseModel):
    brand_or_manufacturer: Optional[str] = Field(None, alias="Brand or Manufacturer")
    product_id: Optional[int] = Field(None, alias="Product ID")
    country: Optional[str] = Field(None, alias="Country")
    sku: Optional[str] = Field(None, alias="SKU")
    brand: Optional[str] = Field(None, alias="Brand")
    manufacturer: Optional[str] = Field(None, alias="Manufacturer")
    product_creation_date: Optional[datetime] = Field(
        None, alias="Product Creation Date"
    )
    product_status: Optional[str] = Field(None, alias="Product Status")
    product_name: Optional[str] = Field(None, alias="Product Name")
    product_price: Optional[float] = Field(None, alias="Product Price")
    quantity: Optional[float] = Field(None, alias="Quantity")
    stock_status: Optional[str] = Field(None, alias="Stock Status")
    salable_quantity: Optional[float] = Field(None, alias="Salable Quantity")
    category_name: Optional[str] = Field(None, alias="Category Name")
    top_category: Optional[str] = Field(None, alias="Top Category")
    seller_id: Optional[int] = Field(None, alias="Seller ID")
    seller_group: Optional[str] = Field(None, alias="Seller Group")
    seller_name: Optional[str] = Field(None, alias="Seller Name")
    hs_record_id: Optional[str] = Field(None, alias="HS Record ID")
    last_price_update_at: Optional[datetime] = Field(None, alias="Last Price Update At")


class WhatsappFlowChipSelector(BaseModel):
    id: str
    title: str
    enabled: bool


class WhatsappNLQResponse(BaseModel):
    conversation_id: Optional[str] = None
    message: str = "success"
    query: Optional[str] = None
    sql_query: Optional[str] = None
    suggested_queries: Optional[List[WhatsappFlowChipSelector]] = []
    result_analysis: Optional[str] = None
    analytics_queries: Optional[List[WhatsappFlowChipSelector]] = []
    results: List[MarketplaceProductNigeria] = None


class WhatsappResponse(BaseModel):
    status: Optional[str] = "success"
    data: Optional[WhatsappNLQResponse] = None


if __name__ == "__main__":
    test_1 = {'object': 'whatsapp_business_account', 'entry': [{'id': '377250852134646', 'changes': [{'value': {'messaging_product': 'whatsapp', 'metadata': {'display_phone_number': '15556233417', 'phone_number_id': '403715826147338'}, 'statuses': [{'id': 'wamid.HBgMNDQ3ODQzNzQxODkxFQIAERgSNjRFNzhDRUM4NEVDMjY4RUY5AA==',
                                                                                                                                                                                                                                                          'status': 'delivered', 'timestamp': '1737849441', 'recipient_id': '447843741891', 'conversation': {'id': 'dede1142449fb1c18763fb823b75793f', 'origin': {'type': 'service'}}, 'pricing': {'billable': True, 'pricing_model': 'CBP', 'category': 'service'}}]}, 'field': 'messages'}]}]}
    test_3 = {'object': 'whatsapp_business_account', 'entry': [{'id': '377250852134646', 'changes': [{'value': {'messaging_product': 'whatsapp', 'metadata': {'display_phone_number': '15556233417', 'phone_number_id': '403715826147338'}, 'statuses': [{'id': 'wamid.HBgMNDQ3ODQzNzQxODkxFQIAERgSNjRFNzhDRUM4NEVDMjY4RUY5AA==',
                                                                                                                                                                                                                                                          'status': 'sent', 'timestamp': '1737849440', 'recipient_id': '447843741891', 'conversation': {'id': 'dede1142449fb1c18763fb823b75793f', 'expiration_timestamp': '1737935700', 'origin': {'type': 'service'}}, 'pricing': {'billable': True, 'pricing_model': 'CBP', 'category': 'service'}}]}, 'field': 'messages'}]}]}
    test_4 = {'object': 'whatsapp_business_account', 'entry': [{'id': '377250852134646', 'changes': [{'value': {'messaging_product': 'whatsapp', 'metadata': {'display_phone_number': '15556233417', 'phone_number_id': '403715826147338'}, 'statuses': [{'id': 'wamid.HBgMNDQ3ODQzNzQxODkxFQIAERgSNjRFNzhDRUM4NEVDMjY4RUY5AA==',
                                                                                                                                                                                                                                                          'status': 'sent', 'timestamp': '1737849440', 'recipient_id': '447843741891', 'conversation': {'id': 'dede1142449fb1c18763fb823b75793f', 'expiration_timestamp': '1737935700', 'origin': {'type': 'service'}}, 'pricing': {'billable': True, 'pricing_model': 'CBP', 'category': 'service'}}]}, 'field': 'messages'}]}]}
    test_5 = {"entry": [{"id": "377250852134646", "time": 1737853700,
                         "changes": [
                             {"value": {
                                 "event": "FLOW_STATUS_CHANGE",
                                 "message": "Flow Red Cloud Lens clone changed status from DRAFT to PUBLISHED",
                                 "flow_id": "596022313163355",
                                 "old_status": "DRAFT",
                                 "new_status": "PUBLISHED"
                             },
                                 "field": "flows"
                             }
                         ]
                         }],
              "object": "whatsapp_business_account"
              }
    test_6 = {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "377250852134646",
                "changes": [
                    {
                        "value": {
                            "messaging_product": "whatsapp",
                            "metadata": {
                                "display_phone_number": "15556233417",
                                "phone_number_id": "403715826147338"
                            },
                            "contacts": [
                                {
                                    "profile":
                                        {
                                            "name": "Red Cloud lens test"
                                        },
                                    "wa_id": "447843741891"
                                }
                            ],
                            "messages": [
                                {
                                    "from": "447843741891",
                                            "id": "wamid.HBgMNDQ3ODQzNzQxODkxFQIAEhgUM0E4NzgyRjVBODhFQTk2ODk4NjMA",
                                            "timestamp": "1737854301",
                                            "type": "image",
                                            "image": {
                                                "caption": "Dbdb",
                                                "mime_type": "image\\/jpeg",
                                                "sha256": "G\\/4XRUmbZSwkJGFFxoqDryBJEWhGNmzBDvKhyjHS7ls=",
                                                "id": "1170207377795140"}}]},
                                            "field": "messages"}]}]}
    WhatsappWebhookPostSchema.model_validate(test_1)
    WhatsappWebhookPostSchema.model_validate(test_3)
    WhatsappWebhookPostSchema.model_validate(test_4)
    WhatsappWebhookPostSchema.model_validate(test_5)
    WhatsappWebhookPostSchema.model_validate(test_6)
