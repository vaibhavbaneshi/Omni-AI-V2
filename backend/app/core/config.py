from dotenv import load_dotenv
import os

load_dotenv()

class Settings:

    APP_NAME = os.getenv("APP_NAME")

    MODEL_NAME = os.getenv("MODEL_NAME")

    OLLAMA_URL = os.getenv("OLLAMA_URL")
    CHROMA_DB_PATH = os.getenv("CHROMA_DB_PATH", "../chroma_db")

    COLLECTION_NAME = os.getenv("COLLECTION_NAME", "omni_ai")

    POSTGRES_HOST = os.getenv(
        "POSTGRES_HOST",
        "localhost"
    )

    POSTGRES_PORT = os.getenv(
        "POSTGRES_PORT",
        "5432"
    )

    POSTGRES_DB = os.getenv(
        "POSTGRES_DB",
        "omni_ai"
    )

    POSTGRES_USER = os.getenv(
        "POSTGRES_USER",
        "postgres"
    )

    POSTGRES_PASSWORD = os.getenv(
        "POSTGRES_PASSWORD",
        "postgres"
    )

settings = Settings()