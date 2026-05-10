import chromadb
from sentence_transformers import SentenceTransformer

model = SentenceTransformer("BAAI/bge-small-en-v1.5")

# client = chromadb.Client(
#     settings=chromadb.Settings(anonymized_telemetry=False)
# )

client = chromadb.Client()

client = chromadb.PersistentClient(
    path="./chroma_db"
)

collection = client.get_collection(name="omniai_docs")

query = "what is embeddings in AI?"

query_embedding = model.encode([query]).tolist()

results = collection.query(
    query_embeddings=query_embedding,
    n_results=3
)
print("\nMETADATAS: ")
print(results["metadatas"])

print("\nQUERY: ")
print(query)

print("\nTOP 3 MATCHES:\n ")

for idx, doc in enumerate(results['documents'][0]):
    print(f"Match {idx + 1}:")
    print(doc)
    print("\n")