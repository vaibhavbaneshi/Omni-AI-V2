from dotenv import load_dotenv
import os

load_dotenv()

class Settings:

    APP_NAME = os.getenv("APP_NAME")

    MODEL_NAME = os.getenv("MODEL_NAME")

    OLLAMA_URL = os.getenv("OLLAMA_URL")

    CHROMA_DB_PATH = os.getenv(
        "CHROMA_DB_PATH"
    )

    COLLECTION_NAME = os.getenv(
        "COLLECTION_NAME"
    )

    POSTGRES_HOST = os.getenv(
        "POSTGRES_HOST"
    )

    POSTGRES_PORT = os.getenv(
        "POSTGRES_PORT"
    )

    POSTGRES_DB = os.getenv(
        "POSTGRES_DB"
    )

    POSTGRES_USER = os.getenv(
        "POSTGRES_USER"
    )

    POSTGRES_PASSWORD = os.getenv(
        "POSTGRES_PASSWORD"
    )

settings = Settings()