from dotenv import load_dotenv

import os

load_dotenv()

class Settings:

    APP_NAME = os.getenv("APP_NAME")

    OLLAMA_URL = os.getenv(
        "OLLAMA_URL"
    )

    MODEL_NAME = os.getenv(
        "MODEL_NAME"
    )

    CHROMA_DB_PATH = os.getenv(
        "CHROMA_DB_PATH"
    )

    COLLECTION_NAME = os.getenv(
        "COLLECTION_NAME"
    )

settings = Settings()