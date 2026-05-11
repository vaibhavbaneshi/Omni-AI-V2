import chromadb
import numpy as np

from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer

# -----------------------------------
# CONFIG
# -----------------------------------

COLLECTION_NAME = "omniai_docs"

# -----------------------------------
# EMBEDDING MODEL
# -----------------------------------

embedding_model = SentenceTransformer(
    "BAAI/bge-small-en-v1.5"
)

# -----------------------------------
# CHROMADB
# -----------------------------------

client = chromadb.PersistentClient(
    path="./chroma_db"
)

collection = client.get_collection(
    name=COLLECTION_NAME
)

# -----------------------------------
# LOAD DOCUMENTS
# -----------------------------------

data = collection.get()

documents = data["documents"]

# -----------------------------------
# BM25 SETUP
# -----------------------------------

tokenized_docs = [
    doc.split() for doc in documents
]

bm25 = BM25Okapi(tokenized_docs)

# -----------------------------------
# USER QUERY
# -----------------------------------

query = input("\nAsk a question: ")

# -----------------------------------
# VECTOR SEARCH
# -----------------------------------

query_embedding = embedding_model.encode(
    [query]
).tolist()

vector_results = collection.query(
    query_embeddings=query_embedding,
    n_results=3
)

# -----------------------------------
# BM25 SEARCH
# -----------------------------------

tokenized_query = query.split()

bm25_scores = bm25.get_scores(
    tokenized_query
)

top_bm25_indices = np.argsort(
    bm25_scores
)[::-1][:3]

# -----------------------------------
# PRINT VECTOR RESULTS
# -----------------------------------

print("\n==============================")
print("VECTOR SEARCH RESULTS")
print("==============================\n")

for idx, doc in enumerate(
    vector_results["documents"][0]
):
    print(f"--- Result {idx+1} ---\n")
    print(doc)
    print("\n")

# -----------------------------------
# PRINT BM25 RESULTS
# -----------------------------------

print("\n==============================")
print("BM25 RESULTS")
print("==============================\n")

for idx in top_bm25_indices:
    print(documents[idx])
    print("\n")