import chromadb

from sentence_transformers import SentenceTransformer

# -----------------------------------
# CONFIG
# -----------------------------------

COLLECTION_NAME = "omniai_docs"

# -----------------------------------
# TEST QUERIES
# -----------------------------------

evaluation_queries = [
    {
        "query": "What are embeddings?",
        "expected_keyword": "embedding"
    },
    {
        "query": "Explain vector databases",
        "expected_keyword": "vector"
    },
    {
        "query": "What is semantic search?",
        "expected_keyword": "semantic"
    }
]

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
# RUN EVALUATION
# -----------------------------------

for test in evaluation_queries:

    query = test["query"]

    expected_keyword = test[
        "expected_keyword"
    ]

    query_embedding = embedding_model.encode(
        [query]
    ).tolist()

    results = collection.query(
        query_embeddings=query_embedding,
        n_results=3
    )

    retrieved_docs = results["documents"][0]

    success = any(
        expected_keyword.lower() in doc.lower()
        for doc in retrieved_docs
    )

    print("\n========================")
    print(f"QUERY: {query}")
    print("========================")

    print(f"\nExpected Keyword:")
    print(expected_keyword)

    print("\nRetrieved Results:\n")

    for doc in retrieved_docs:
        print(doc[:300])
        print("\n---\n")

    print("PASS" if success else "FAIL")    