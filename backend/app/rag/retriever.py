from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

from backend.app.rag.ingest import load_document, DATA_PATH
from backend.app.rag.chunker import chunk_text

model = SentenceTransformer("BAAI/bge-small-en-v1.5")

document = load_document(DATA_PATH)

chunks = chunk_text(document, chunk_size=300, overlap=50)

chunk_embeddings = model.encode(chunks)

query = "what is machine learning?"

query_embedding = model.encode([query])

similarities = cosine_similarity(
    query_embedding,
    chunk_embeddings    
)[0]

best_match_index = similarities.argsort()[-1]

print("\nQUERY: ")
print(query)

print("\nBEST MATCH:  ")
print(chunks[best_match_index])

print("\nSIMILARITY SCORE: ")
print(similarities[best_match_index])