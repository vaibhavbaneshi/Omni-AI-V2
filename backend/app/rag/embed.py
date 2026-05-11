from sentence_transformers import SentenceTransformer

model = SentenceTransformer('BAAI/bge-small-en-v1.5')

sentences = [
    "Dogs are loyal animals.",
    "Puppies are very friendly.",
    "Database systems are crucial for data management."
]

embeddings = model.encode(sentences)

print(f"Total embeddings: {len(embeddings)}")

print("\nEmbedding shape:")
print(embeddings[0].shape)

print("\nFirst 10 values:")
print(embeddings[0][:10])