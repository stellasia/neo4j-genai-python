from __future__ import annotations

from random import random

from neo4j import GraphDatabase
from neo4j_graphrag.embeddings.base import Embedder
from neo4j_graphrag.indexes import create_vector_index
from neo4j_graphrag.retrievers import VectorRetriever

URI = "neo4j://localhost:7687"
AUTH = ("neo4j", "password")

INDEX_NAME = "embedding-name"
DIMENSION = 1536

# Connect to Neo4j database
driver = GraphDatabase.driver(URI, auth=AUTH)


# Create CustomEmbedder object with the required Embedder type
class CustomEmbedder(Embedder):
    def embed_query(self, text: str) -> list[float]:
        return [random() for _ in range(DIMENSION)]


embedder = CustomEmbedder()

# Creating the index
create_vector_index(
    driver,
    INDEX_NAME,
    label="Document",
    embedding_property="vectorProperty",
    dimensions=DIMENSION,
    similarity_fn="euclidean",
)

# Initialize the retriever
retriever = VectorRetriever(driver, INDEX_NAME, embedder)

# Upsert the query
vector = [random() for _ in range(DIMENSION)]
insert_query = (
    "MERGE (n:Document {id: $id})"
    "WITH n "
    "CALL db.create.setNodeVectorProperty(n, 'vectorProperty', $vector)"
    "RETURN n"
)
parameters = {
    "id": 0,
    "vector": vector,
}
driver.execute_query(insert_query, parameters)

# Perform the similarity search for a text query
query_text = "Find me a book about Fremen"
print(retriever.search(query_text=query_text, top_k=5))
