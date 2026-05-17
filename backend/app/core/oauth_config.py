import os

from dotenv import load_dotenv

load_dotenv()


def get_oauth_settings() -> dict[str, str]:
    return {
        "frontend_url": os.getenv("FRONTEND_URL", "http://localhost:3000").rstrip("/"),
        "api_public_url": os.getenv("API_PUBLIC_URL", "http://localhost:8000").rstrip("/"),
        "github_client_id": os.getenv("GITHUB_CLIENT_ID", "").strip(),
        "github_client_secret": os.getenv("GITHUB_CLIENT_SECRET", "").strip(),
        "google_client_id": os.getenv("GOOGLE_CLIENT_ID", "").strip(),
        "google_client_secret": os.getenv("GOOGLE_CLIENT_SECRET", "").strip(),
    }


def oauth_providers_status() -> dict[str, bool]:
    settings = get_oauth_settings()
    return {
        "github": bool(settings["github_client_id"] and settings["github_client_secret"]),
        "google": bool(settings["google_client_id"] and settings["google_client_secret"]),
    }
