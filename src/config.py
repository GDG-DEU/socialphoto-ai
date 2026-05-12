from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    log_level: str = "INFO"

    api_host: str = "0.0.0.0"
    api_port: int = 8000

    api_key: str | None = None
    x_api_key: str | None = Field(default=None, validation_alias="X-API-Key")
    socket_io_secret: str | None = None
    backend_url: str | None = None
    cors_allowed_origins: str = "*"

    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: str | None = None

    pinecone_api_key: str | None = None
    pinecone_index_name: str | None = None
    pinecone_namespace: str | None = None

    cloudinary_cloud_name: str | None = None
    cloudinary_api_key: str | None = None
    cloudinary_api_secret: str | None = None

    gemini_api_key: str | None = None
    gemini_model_name: str | None = None

    openai_api_key: str | None = None
    openai_model_name: str | None = None
    
    analyze_system_instruction: str = (
        "You are an expert photography critic for a social media platform for photographers. "
        "Your role is to comprehensively analyze images, evaluating aesthetic and technical quality, composition, and color profile."
    )
    analyze_prompt_template: str = (
        "Analyze this photo.\n"
        "IMPORTANT: Your `improvement_tips` must focus ONLY on photographic execution (lighting, composition, editing). DO NOT suggest watermarks, text overlays, or business advice.\n"
        "IMPORTANT: Write your responses in the following language: {language}"
    )

    ml_models_dir: str = "models/ml"

    max_image_size: int = 1024
    res_threshold: int = 1024


@lru_cache
def get_settings() -> Settings:
    return Settings()
