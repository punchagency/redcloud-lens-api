from typing import List
from routers.nlq.schemas import MarketplaceProductNigeria
from routers.whatsapp.schema import WhatsappFlowChipSelector


def format_product_message(product: MarketplaceProductNigeria):
    return f"""
    Product: {product.product_name}
    \nPrice: {
    product.country == "Nigeria" and "NGN" or "$"
    } {'{:,.2f}'.format(product.product_price)}
    \nSeller: {product.seller_name}
    \nManufacturer: {product.manufacturer} 
    \nBrand: {product.brand}
    \nAvailable: {int(product.salable_quantity) if product.salable_quantity else "No available"} unit(s)
    """
# "₦"


def format_flow_chip_selector(query: str):
    return WhatsappFlowChipSelector(
        id='_'.join(query.lower().split(' ')),
        title=query,
        enabled=True
    )


def format_flow_chip_selector_from_list(items: List[str]):
    return [format_flow_chip_selector(item) for item in items]


def format_flow_chip_selector_from_list_of_dicts(items: List[dict]):
    return [format_flow_chip_selector(item["title"]) for item in items]
