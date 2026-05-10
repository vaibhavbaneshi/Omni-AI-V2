import chromadb
import requests
from sentence_transformers import SentenceTransformer

# -----------------------------
# CONFIG
# -----------------------------

OLLAMA_URL = "http://localhost:11434/api/generate"

MODEL_NAME = "llama3"

COLLECTION_NAME = "omniai_docs"

# -----------------------------
# EMBEDDING MODEL
# -----------------------------

embedding_model = SentenceTransformer(

    "BAAI/bge-small-en-v1.5"

)

# -----------------------------
# CHROMADB
# -----------------------------

client = chromadb.PersistentClient(

    path="./chroma_db"

)

collection = client.get_collection(

    name=COLLECTION_NAME

)

# -----------------------------
# USER QUERY
# -----------------------------
query = input("\nAsk a question: ")

# -----------------------------
# QUERY EMBEDDING
# -----------------------------

query_embedding = embedding_model.encode(
    [query]
).tolist()

# -----------------------------
# RETRIEVE RELEVANT DOCUMENTS
# -----------------------------
results = collection.query(
    query_embeddings=query_embedding,
    n_results=3
)   

retrieved_chunks = results['documents'][0]

context = "\n\n".join(retrieved_chunks)
print("\nRETRIEVED CONTEXT:\n")
print(context)
# -----------------------------
# PROMPT TEMPLATE       
# -----------------------------

prompt = f"""You are an AI assistant. Answer ONLY from the provided context.

If the answer is not in context, say:

"I could not find the answer in the provided documents."

Context:
{context}

User Question: {query}
"""

# -----------------------------
# CALL OLLAMA API
# -----------------------------

payload = {
    "model": MODEL_NAME,
    "prompt": prompt,
    "stream": True
}   

response = requests.post(OLLAMA_URL, json=payload, stream=True)

print("\nAI Response:\n")

for line in response.iter_lines():
    if line:
        import json
        chunk = json.loads(line.decode('utf-8'))
        print(chunk.get("response", ""), end="", flush=True)