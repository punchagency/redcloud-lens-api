import chromadb
from typing import List
from pydantic import BaseModel
from dotenv import load_dotenv
import os

load_dotenv()

CHROMADB_HOST = os.environ.get("CHROMADB_HOST")
CHROMADB_PORT = os.environ.get("CHROMADB_PORT")

chromadb_client = chromadb.HttpClient(host=CHROMADB_HOST, port=CHROMADB_PORT)


class EmbeddedProduct(BaseModel):
    id: str
    name: str
    country: str
    category_name: str
    brand: str
    rank: float
    sku: List[str]


class ProductCatalog:
    collection_name = "product_catalog"
    collection: chromadb.Collection

    def __init__(self):
        self.collection = chromadb_client.get_collection(self.collection_name)

    def perform_cosine_search(self, queries: List[str], country: str = "Nigeria", k: int = 10) -> List[List[EmbeddedProduct]]:
        products: List[List[EmbeddedProduct]] = []
        data = self.collection.query(
            query_texts=queries,
            n_results=k,
            where={"Country": country},

        )
        for x in range(len(queries)):
            product_group: List[EmbeddedProduct] = []
            distances = data["distances"][x]
            metadatas = data["metadatas"][x]
            documents = data["documents"][x]
            ids = data["ids"][x]
            num_results = len(metadatas)
            for i in range(num_results):
                product = EmbeddedProduct(
                    id=ids[i],
                    name=documents[i],
                    country=metadatas[i]["Country"],
                    rank=distances[i] * 100,
                    sku=metadatas[i]["SKU_STRING"].split(","),
                    brand=metadatas[i]["Brand"],
                    category_name=metadatas[i]["Category Name"],
                )
                product_group.append(product)
            product_group.sort(key=lambda x: x.rank, reverse=True)
            products.append(product_group)

        return products


if __name__ == "__main__":
    product_catalog = ProductCatalog()
    data = product_catalog.perform_cosine_search(
        ["Zora Neale Hurston WATCH THE Oprah Winfrey Presents TELEVISION EVENT STARRING HALLE BERRY ON ABC Their Eyes Were Watching God N N C A a novel"], country="Nigeria", k=10)
    print(data)
