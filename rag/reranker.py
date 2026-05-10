import chromadb

from sentence_transformers import (
    SentenceTransformer,
    CrossEncoder
)

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
# RERANKER MODEL
# -----------------------------------

reranker = CrossEncoder(
    "cross-encoder/ms-marco-MiniLM-L-6-v2"
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
# USER QUERY
# -----------------------------------

query = input("\nAsk a question: ")

# -----------------------------------
# VECTOR RETRIEVAL
# -----------------------------------

query_embedding = embedding_model.encode(
    [query]
).tolist()

results = collection.query(
    query_embeddings=query_embedding,
    n_results=5
)

documents = results["documents"][0]

# -----------------------------------
# RERANKING
# -----------------------------------

pairs = [
    [query, doc]
    for doc in documents
]

scores = reranker.predict(pairs)

# -----------------------------------
# SORT BY SCORE
# -----------------------------------

reranked_results = sorted(
    zip(documents, scores),
    key=lambda x: x[1],
    reverse=True
)

# -----------------------------------
# PRINT RESULTS
# -----------------------------------

print("\n==============================")
print("RERANKED RESULTS")
print("==============================\n")

for idx, (doc, score) in enumerate(
    reranked_results
):
    print(f"--- Rank {idx+1} ---")
    print(f"Score: {score:.4f}\n")
    print(doc)
    print("\n")