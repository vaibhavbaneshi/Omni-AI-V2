from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

model = SentenceTransformer("BAAI/bge-small-en-v1.5")

sentences = [
    "Dogs are loyal animals",
    "Puppies are friendly pets",
    "Databases store information"
]

embeddings = model.encode(sentences)

similarity_1 = cosine_similarity(
    [embeddings[0]],
    [embeddings[1]]
)

similarity_2 = cosine_similarity(
    [embeddings[0]],
    [embeddings[2]]
)

print("\nDog vs Puppy:")
print(similarity_1)

print("\nDog vs Database:")
print(similarity_2)