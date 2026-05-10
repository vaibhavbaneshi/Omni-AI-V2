from ingest import load_document, DATA_PATH

def chunk_text(text, chunk_size=300, overlap=50):
    chunks=[]

    start = 0

    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append(chunk)

        start += chunk_size - overlap

    return chunks  


if __name__ == "__main__":
    document = load_document(DATA_PATH)

    chunks = chunk_text(document)

    print(f"Total Chunks: {len(chunks)}")

    print("\nFirst Chunk:\n")
    print(chunks[0])