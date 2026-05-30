import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from app.core.chroma_client import get_collection
from sentence_transformers import SentenceTransformer

model = SentenceTransformer("BAAI/bge-small-en-v1.5")

collection = get_collection("omniai_docs")

query = "what is embeddings in AI?"

query_embedding = model.encode([query]).tolist()

results = collection.query(
    query_embeddings=query_embedding,
    n_results=3,
)

print("\nQuery:", query)
print("\nTop Results:\n")

for doc in results["documents"][0]:
    print("-", doc)
