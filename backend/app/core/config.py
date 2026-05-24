from dotenv import load_dotenv
import os

load_dotenv()

class Settings:

    APP_NAME = os.getenv("APP_NAME", "OmniAI")

    MODEL_NAME = os.getenv("MODEL_NAME")

    OLLAMA_URL = os.getenv("OLLAMA_URL")
    CHROMA_DB_PATH = os.getenv("CHROMA_DB_PATH", "../chroma_db")

    COLLECTION_NAME = os.getenv("COLLECTION_NAME", "omni_ai")

    TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")
    SERPER_API_KEY = os.getenv("SERPER_API_KEY", "")
    WEB_SEARCH_PROVIDER = os.getenv("WEB_SEARCH_PROVIDER", "tavily")

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
