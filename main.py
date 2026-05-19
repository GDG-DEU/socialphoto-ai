import uvicorn

from src.config import get_settings


if __name__ == "__main__":
    settings = get_settings()
    env = settings.app_env.lower()
    reload_enabled = env not in {"production", "prod"}
    uvicorn.run(
        "app:combined_app",
        host=settings.api_host,
        port=settings.api_port,
        reload=reload_enabled,
    )