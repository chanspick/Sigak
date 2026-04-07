"""SIGAK Configuration"""
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # ── App ──
    app_name: str = "SIGAK PI Diagnostic"
    debug: bool = True
    api_prefix: str = "/api/v1"

    # ── Database ──
    database_url: str = "postgresql+asyncpg://sigak:sigak@localhost:5432/sigak"

    # ── Storage (S3-compatible) ──
    s3_bucket: str = "sigak-uploads"
    s3_endpoint: str = ""  # Leave empty for AWS, set for MinIO
    s3_access_key: str = ""
    s3_secret_key: str = ""

    # ── LLM ──
    anthropic_api_key: str = ""
    llm_model: str = "claude-sonnet-4-20250514"
    llm_max_tokens: int = 4096

    # ── CV Pipeline ──
    clip_model: str = "ViT-L-14"                 # CLIP model variant
    clip_pretrained: str = "openai"
    use_mock_clip: bool = True                    # WoZ phase: use random embeddings
    face_photo_max_size: int = 2048               # Max dimension in px

    # ── Coordinate System ──
    coordinate_axes: int = 3                      # Number of aesthetic axes
    embedding_dim: int = 768                      # CLIP embedding dimension
    anchors_per_pole: int = 10                    # Reference celebs per axis pole

    # ── Report ──
    report_delivery_hours: int = 24
    base_url: str = "https://sigak.kr"

    class Config:
        env_file = (".env", "../.env")
        env_file_encoding = "utf-8"
        extra = "ignore"


_settings = None

def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
