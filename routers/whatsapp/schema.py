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
    next_screen: Optional[str] = "final_screen"
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
    next_screen: Optional[str] = "final_screen"
    message: str = "success"
    query: Optional[str] = None
    sql_query: Optional[str] = None
    suggested_queries: Optional[List[WhatsappFlowChipSelector]] = []
    result_analysis: Optional[str] = None
    analytics_queries: Optional[List[WhatsappFlowChipSelector]] = []
    results: List[MarketplaceProductNigeria] = []


class FlowEndpointException(Exception):
    """Custom exception for Flow endpoint errors."""

    def __init__(self, status_code, message):
        super().__init__(message)
        self.status_code = status_code


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


# { TODO
#     "version": "6.3",
#     "data_api_version": "3.0",
#     "routing_model": {
#         "step_one": [
#             "step_two"
#         ],
#         "step_two": [
#             "step_three"
#         ],
#         "step_three": [
#             "final_screen"
#         ]
#     },
#     "screens": [
#         {
#             "id": "step_one",
#             "title": "Choose Options",
#             "data": {
#                 "actions": {
#                     "type": "array",
#                     "description": "",
#                     "items": {
#                         "type": "object",
#                         "properties": {
#                             "id": {
#                                 "type": "string"
#                             },
#                             "title": {
#                                 "type": "string"
#                             }
#                         }
#                     },
#                     "__example__": [
#                         {
#                             "id": "a_one",
#                             "title": "Identify product & check stock"
#                         },
#                         {
#                             "id": "a_two",
#                             "title": "Ask details about a product"
#                         }
#                     ]
#                 }
#             },
#             "layout": {
#                 "type": "SingleColumnLayout",
#                 "children": [
#                     {
#                         "type": "Form",
#                         "name": "selector_form",
#                         "children": [
#                             {
#                                 "type": "RadioButtonsGroup",
#                                 "label": "What will you like to do now ?",
#                                 "name": "step_one_action",
#                                 "data-source": [
#                                     {
#                                         "id": "a_one",
#                                         "title": "Identify product & check stock",
#                                         "description": "TBD"
#                                     },
#                                     {
#                                         "id": "a_two",
#                                         "title": "Ask details about a product",
#                                         "description": "TBD"
#                                     }
#                                 ],
#                                 "required": true
#                             },
#                             {
#                                 "type": "Footer",
#                                 "label": "Continue",
#                                 "on-click-action": {
#                                     "name": "navigate",
#                                     "next": {
#                                         "type": "screen",
#                                         "name": "step_two"
#                                     },
#                                     "payload": {
#                                         "selected_action": "${form.step_one_action}",
#                                         "countries": [
#                                             {
#                                                 "id": "Nigeria",
#                                                 "title": "Nigeria",
#                                                 "description": "Nigeria",
#                                                 "metadata": "NG"
#                                             },
#                                             {
#                                                 "id": "South",
#                                                 "title": "South Africa",
#                                                 "description": "South Africa",
#                                                 "metadata": "ZA"
#                                             },
#                                             {
#                                                 "id": "Argentina",
#                                                 "title": "Argentina",
#                                                 "description": "Argentina",
#                                                 "metadata": "AR"
#                                             },
#                                             {
#                                                 "id": "Brazil",
#                                                 "title": "Brazil",
#                                                 "description": "Brazil",
#                                                 "metadata": "BR"
#                                             }
#                                         ]
#                                     }
#                                 }
#                             }
#                         ]
#                     }
#                 ]
#             }
#         },
#         {
#             "id": "step_two",
#             "title": "Product Information",
#             "terminal": true,
#             "data": {
#                 "countries": {
#                     "type": "array",
#                     "items": {
#                         "type": "object",
#                         "properties": {
#                             "id": {
#                                 "type": "string"
#                             },
#                             "title": {
#                                 "type": "string"
#                             },
#                             "description": {
#                                 "type": "string"
#                             },
#                             "metadata": {
#                                 "type": "string"
#                             }
#                         }
#                     },
#                     "__example__": [
#                         {
#                             "id": "1",
#                             "title": "Nigeria",
#                             "description": "Nigeria",
#                             "metadata": "NG"
#                         },
#                         {
#                             "id": "2",
#                             "title": "South Africa",
#                             "description": "South Africa",
#                             "metadata": "ZA"
#                         },
#                         {
#                             "id": "3",
#                             "title": "Argentina",
#                             "description": "Argentina",
#                             "metadata": "AR"
#                         },
#                         {
#                             "id": "4",
#                             "title": "Brazil",
#                             "description": "Brazil",
#                             "metadata": "BR"
#                         }
#                     ]
#                 },
#                 "actions": {
#                     "type": "array",
#                     "description": "",
#                     "items": {
#                         "type": "object",
#                         "properties": {
#                             "id": {
#                                 "type": "string"
#                             },
#                             "title": {
#                                 "type": "string"
#                             }
#                         }
#                     },
#                     "__example__": [
#                         {
#                             "id": "a_one",
#                             "title": "Identify product & check stock"
#                         },
#                         {
#                             "id": "a_two",
#                             "title": "Ask details about a product"
#                         }
#                     ]
#                 }
#             },
#             "layout": {
#                 "type": "SingleColumnLayout",
#                 "children": [
#                     {
#                         "type": "Form",
#                         "name": "flow_path",
#                         "init-values": {
#                             "text_input": ""
#                         },
#                         "children": [
#                             {
#                                 "type": "Dropdown",
#                                 "label": "Country",
#                                 "name": "country",
#                                 "data-source": "${data.countries}",
#                                 "required": true
#                             },
#                             {
#                                 "type": "TextInput",
#                                 "required": true,
#                                 "label": "Enter product info",
#                                 "name": "product_name",
#                                 "helper-text": "Information you want to know about the product"
#                             },
#                             {
#                                 "type": "PhotoPicker",
#                                 "name": "product_image",
#                                 "label": "Upload photos",
#                                 "description": "Please attach product image if available",
#                                 "photo-source": "camera_gallery",
#                                 "min-uploaded-photos": 0,
#                                 "max-uploaded-photos": 1,
#                                 "max-file-size-kb": 10240
#                             },
#                             {
#                                 "type": "Footer",
#                                 "label": "Search",
#                                 "on-click-action": {
#                                     "name": "data_exchange",
#                                     "payload": {
#                                         "query": "${form.product_name}",
#                                         "next_screen": "step_three",
#                                         "product_image": "${form.product_image}",
#                                         "country": "${form.country}",
#                                         "limit": 10
#                                     }
#                                 }
#                             }
#                         ]
#                     }
#                 ]
#             }
#         },
#         {
#             "id": "step_three",
#             "title": "Products Information",
#             "data": {
#                 "status": {
#                     "type": "string",
#                     "__example__": "success"
#                 },
#                 "data": {
#                     "type": "object",
#                     "properties": {
#                         "conversation_id": {
#                             "type": "string"
#                         },
#                         "message": {
#                             "type": "string"
#                         },
#                         "query": {
#                             "type": "string"
#                         },
#                         "sql_query": {
#                             "type": "string"
#                         },
#                         "next_screen": {
#                             "type": "string"
#                         },
#                         "suggested_queries": {
#                             "type": "array",
#                             "description": "List of Suggested Products",
#                             "items": {
#                                 "type": "object",
#                                 "properties": {
#                                     "id": {
#                                         "type": "string"
#                                     },
#                                     "title": {
#                                         "type": "string"
#                                     },
#                                     "enabled": {
#                                         "type": "boolean"
#                                     }
#                                 }
#                             }
#                         },
#                         "result_analysis": {
#                             "type": "string"
#                         },
#                         "analytics_queries": {
#                             "type": "array",
#                             "description": "List of Suggested Queries",
#                             "items": {
#                                 "type": "object",
#                                 "properties": {
#                                     "id": {
#                                         "type": "string"
#                                     },
#                                     "title": {
#                                         "type": "string"
#                                     },
#                                     "enabled": {
#                                         "type": "boolean"
#                                     }
#                                 }
#                             }
#                         },
#                         "result_navigation": {
#                             "type": "array",
#                             "items": {
#                                 "type": "object",
#                                 "properties": {
#                                     "id": {
#                                         "type": "string"
#                                     },
#                                     "main-content": {
#                                         "type": "object",
#                                         "properties": {
#                                             "title": {
#                                                 "type": "string"
#                                             },
#                                             "metadata": {
#                                                 "type": "string"
#                                             },
#                                             "description": {
#                                                 "type": "string"
#                                             }
#                                         }
#                                     },
#                                     "end": {
#                                         "type": "object",
#                                         "properties": {
#                                             "title": {
#                                                 "type": "string"
#                                             },
#                                             "metadata": {
#                                                 "type": "string"
#                                             },
#                                             "description": {
#                                                 "type": "string"
#                                             }
#                                         }
#                                     },
#                                     "badge": {
#                                         "type": "string"
#                                     },
#                                     "on-click-action": {
#                                         "type": "object",
#                                         "properties": {
#                                             "name": {
#                                                 "type": "string"
#                                             },
#                                             "next": {
#                                                 "type": "object",
#                                                 "properties": {
#                                                     "type": {
#                                                         "type": "string"
#                                                     },
#                                                     "name": {
#                                                         "type": "string"
#                                                     }
#                                                 }
#                                             },
#                                             "payload": {
#                                                 "type": "object",
#                                                 "properties": {
#                                                     "conversation_id": {
#                                                         "type": "string"
#                                                     },
#                                                     "suggested_queries": {
#                                                         "type": "array",
#                                                         "items": {
#                                                             "type": "object",
#                                                             "properties": {
#                                                                 "id": {
#                                                                     "type": "string"
#                                                                 },
#                                                                 "title": {
#                                                                     "type": "string"
#                                                                 },
#                                                                 "enabled": {
#                                                                     "type": "boolean"
#                                                                 }
#                                                             }
#                                                         }
#                                                     },
#                                                     "analytics_queries": {
#                                                         "type": "array",
#                                                         "items": {
#                                                             "type": "object",
#                                                             "properties": {
#                                                                 "id": {
#                                                                     "type": "string"
#                                                                 },
#                                                                 "title": {
#                                                                     "type": "string"
#                                                                 },
#                                                                 "enabled": {
#                                                                     "type": "boolean"
#                                                                 }
#                                                             }
#                                                         }
#                                                     }
#                                                 }
#                                             }
#                                         }
#                                     }
#                                 }
#                             }
#                         },
#                         "results": {
#                             "type": "array",
#                             "description": "Products found based on the search results",
#                             "items": {
#                                 "type": "object",
#                                 "properties": {
#                                     "product_name": {
#                                         "type": "string"
#                                     },
#                                     "sku": {
#                                         "type": "string"
#                                     },
#                                     "price": {
#                                         "type": "number"
#                                     },
#                                     "stock_status": {
#                                         "type": "string"
#                                     },
#                                     "seller": {
#                                         "type": "string"
#                                     },
#                                     "status": {
#                                         "type": "string"
#                                     }
#                                 }
#                             }
#                         }
#                     },
#                     "__example__": {
#                         "conversation_id": "0c5cbe33-f303-4066-89ca-1135296df6a8",
#                         "message": "success",
#                         "next_screen": "final_screen",
#                         "query": "",
#                         "sql_query": "SELECT * FROM marketplace_product_nigeria WHERE SKU IN (\"EBL-130\", \"CFO-060\", \"PIL-003\", \"AUE-008\", \"STS-055\", \"WTM-205\", \"IOM-011\", \"SLV-008\", \"WTM-022\") LIMIT 10;",
#                         "suggested_queries": [
#                             {
#                                 "id": "a_one",
#                                 "title": "Find Coca Cola products",
#                                 "enabled": true
#                             },
#                             {
#                                 "id": "a_two",
#                                 "title": "Show Coca Cola beverages",
#                                 "enabled": true
#                             },
#                             {
#                                 "id": "a_three",
#                                 "title": "List all Coca Cola related items",
#                                 "enabled": false
#                             },
#                             {
#                                 "id": "a_four",
#                                 "title": "Display Coca Cola drinks in stock",
#                                 "enabled": true
#                             },
#                             {
#                                 "id": "a_five",
#                                 "title": "Retrieve Coca Cola product details",
#                                 "enabled": true
#                             }
#                         ],
#                         "result_analysis": "It looks like Arla Dano Slim Skimmed Milk Powder is the hot commodity across various sellers in Nigeria! We have a mix of enabled and disabled products for different sellers, primarily independent distributors. Most products are in stock and ready to be snapped up. Prices vary widely from N3,500 to N98,962.5. Two sellers, Wabilahi Taofeeq Moboluwaduro Nig Ltd, have some products currently disabled, but others are fully stocked and selling. Whether you are stocking up for personal use or a business, there's definitely an option here for you!",
#                         "analytics_queries": [
#                             {
#                                 "id": "a_one",
#                                 "title": "Show me the top selling brands of powdered milk in Nigeria.",
#                                 "enabled": true
#                             },
#                             {
#                                 "id": "a_two",
#                                 "title": "What are the prices of Dano milk powder products?",
#                                 "enabled": true
#                             },
#                             {
#                                 "id": "a_three",
#                                 "title": "List the available Dano milk products by price.",
#                                 "enabled": false
#                             },
#                             {
#                                 "id": "a_four",
#                                 "title": "Which sellers have Dano milk products in stock?",
#                                 "enabled": true
#                             },
#                             {
#                                 "id": "a_five",
#                                 "title": "Find the top categories for food products on redcloud.",
#                                 "enabled": true
#                             }
#                         ],
#                         "result_navigation": [
#                             {
#                                 "id": "a_one",
#                                 "main-content": {
#                                     "title": "Arla Dano",
#                                     "metadata": "Arla Dano",
#                                     "description": "Arla Dano"
#                                 },
#                                 "end": {
#                                     "title": "Arla Dano",
#                                     "description": "Arla Dano"
#                                 },
#                                 "badge": "Arl",
#                                 "on-click-action": {
#                                     "name": "navigate",
#                                     "next": {
#                                         "name": "FIFTH_SCREEN",
#                                         "type": "screen"
#                                     },
#                                     "payload": {
#                                         "suggested_queries": [
#                                             {
#                                                 "id": "a_one",
#                                                 "title": "Find Coca Cola products",
#                                                 "enabled": true
#                                             }
#                                         ],
#                                         "analytics_queries": [
#                                             {
#                                                 "id": "a_one",
#                                                 "title": "Show me the top selling brands of powdered milk in Nigeria.",
#                                                 "enabled": true
#                                             }
#                                         ]
#                                     },
#                                     "conversation_id": "0c5cbe33-f303-4066-89ca-1135296df6a8"
#                                 }
#                             }
#                         ],
#                         "results": [
#                             {
#                                 "product_name": "Arla Dano Slim Skimmed Milk Powder 5 X 900g",
#                                 "sku": "EBL-130",
#                                 "price": 98962.5,
#                                 "stock_status": "In Stock",
#                                 "seller": "Emmanuel Bakeries Ltd",
#                                 "status": "Enabled"
#                             },
#                             {
#                                 "product_name": "Arla Dano Slim Skimmed Milk Powder 5 X 900g",
#                                 "sku": "AUE-008",
#                                 "price": 58000.0,
#                                 "stock_status": "In Stock",
#                                 "seller": "Austin Channy Enterprise",
#                                 "status": "Enabled"
#                             },
#                             {
#                                 "product_name": "Arla Dano Slim Skimmed Milk Powder 5 X 900g",
#                                 "sku": "WTM-205",
#                                 "price": 33000.0,
#                                 "stock_status": "In Stock",
#                                 "seller": "Wabilahi Taofeeq Moboluwaduro Nig Ltd",
#                                 "status": "Disabled"
#                             },
#                             {
#                                 "product_name": "Arla Dano Slim Skimmed Milk Powder 5 X 900g",
#                                 "sku": "WTM-022",
#                                 "price": 3500.0,
#                                 "stock_status": "In Stock",
#                                 "seller": "Wabilahi Taofeeq Moboluwaduro Nig Ltd",
#                                 "status": "Disabled"
#                             },
#                             {
#                                 "product_name": "Arla Dano Slim Skimmed Milk Powder 5 X 900g",
#                                 "sku": "STS-055",
#                                 "price": 33000.0,
#                                 "stock_status": "In Stock",
#                                 "seller": "Sodabe Trading Stores",
#                                 "status": "Enabled"
#                             },
#                             {
#                                 "product_name": "Arla Dano Slim Skimmed Milk Powder 5 X 900g",
#                                 "sku": "SLV-008",
#                                 "price": 58000.0,
#                                 "stock_status": "In Stock",
#                                 "seller": "Salt And Light Global Ventures",
#                                 "status": "Enabled"
#                             },
#                             {
#                                 "product_name": "Arla Dano Slim Skimmed Milk Powder 5 X 900g",
#                                 "sku": "IOM-011",
#                                 "price": 98000.0,
#                                 "stock_status": "In Stock",
#                                 "seller": "Iddunuore Oluwa Mega Concept",
#                                 "status": "Enabled"
#                             },
#                             {
#                                 "product_name": "Arla Dano Slim Skimmed Milk Powder 5 X 900g",
#                                 "sku": "CFO-060",
#                                 "price": 18000.0,
#                                 "stock_status": "In Stock",
#                                 "seller": "Chris F. Okenna Nig Ent",
#                                 "status": "Enabled"
#                             },
#                             {
#                                 "product_name": "Arla Dano Slim Skimmed Milk Powder 5 X 900g",
#                                 "sku": "PIL-003",
#                                 "price": 98000.0,
#                                 "stock_status": "In Stock",
#                                 "seller": "Pec Innovations Ltd",
#                                 "status": "Enabled"
#                             }
#                         ]
#                     }
#                 }
#             },
#             "layout": {
#                 "type": "SingleColumnLayout",
#                 "children": [
#                     {
#                         "type": "NavigationList",
#                         "name": "matching_products",
#                         "list-items": "${data.data.result_navigation}"
#                     }
#                 ]
#             }
#         },
#         {
#             "id": "final_screen",
#             "title": "Suggested Searches",
#             "terminal": true,
#             "data": {
#                 "conversation_id": {
#                     "type": "string",
#                     "__example__": "0c5cbe33-f303-4066-89ca-1135296df6a8"
#                 },
#                 "suggested_queries": {
#                     "type": "array",
#                     "description": "List of Suggested Products",
#                     "items": {
#                         "type": "object",
#                         "properties": {
#                             "id": {
#                                 "type": "string"
#                             },
#                             "title": {
#                                 "type": "string"
#                             },
#                             "enabled": {
#                                 "type": "boolean"
#                             }
#                         }
#                     },
#                     "__example__": [
#                         {
#                             "id": "a_one",
#                             "title": "Find Coca Cola products",
#                             "enabled": true
#                         }
#                     ]
#                 },
#                 "analytics_queries": {
#                     "type": "array",
#                     "description": "List of Suggested Queries",
#                     "items": {
#                         "type": "object",
#                         "properties": {
#                             "id": {
#                                 "type": "string"
#                             },
#                             "title": {
#                                 "type": "string"
#                             },
#                             "enabled": {
#                                 "type": "boolean"
#                             }
#                         }
#                     },
#                     "__example__": [
#                         {
#                             "id": "a_one",
#                             "title": "Show me the top selling brands of powdered milk in Nigeria.",
#                             "enabled": true
#                         }
#                     ]
#                 }
#             },
#             "layout": {
#                 "type": "SingleColumnLayout",
#                 "children": [
#                     {
#                         "type": "ChipsSelector",
#                         "name": "chips",
#                         "label": "Suggested Searches",
#                         "description": "Select any of the suggested searches to get more information about the product",
#                         "max-selected-items": 1,
#                         "data-source": "${data.suggested_queries}"
#                     },
#                     {
#                         "type": "Footer",
#                         "label": "Done",
#                         "on-click-action": {
#                             "name": "complete",
#                             "payload": {}
#                         }
#                     }
#                 ]
#             }
#         }
#     ]
# }
