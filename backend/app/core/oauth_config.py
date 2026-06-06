from app.core.app_settings import get_settings


def get_oauth_settings() -> dict[str, str]:
    settings = get_settings()
    return {
        "frontend_url": settings.FRONTEND_URL.rstrip("/"),
        "api_public_url": settings.API_PUBLIC_URL.rstrip("/"),
        "github_client_id": settings.GITHUB_CLIENT_ID.strip(),
        "github_client_secret": settings.GITHUB_CLIENT_SECRET.strip(),
        "google_client_id": settings.GOOGLE_CLIENT_ID.strip(),
        "google_client_secret": settings.GOOGLE_CLIENT_SECRET.strip(),
    }


def oauth_providers_status() -> dict[str, bool]:
    settings = get_oauth_settings()
    return {
        "github": bool(settings["github_client_id"] and settings["github_client_secret"]),
        "google": bool(settings["google_client_id"] and settings["google_client_secret"]),
    }
