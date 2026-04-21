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

    # ── LLM v2 (Sia 대화 + extraction, Priority 1) ──
    anthropic_model_haiku: str = "claude-haiku-4-5-20251001"   # Sia 대화 (턴당)
    anthropic_model_sonnet: str = "claude-sonnet-4-6"          # Sonnet extraction (대화 종료 후 일괄)

    # ── IG 피드 수집 (Apify, Priority 1 Step 1) ──
    ig_enabled: bool = False                                    # MVP 초기 False. Apify 안정화 후 True
    apify_api_key: str = ""                                     # Apify Instagram Profile Scraper Actor 키
    ig_fetch_timeout: float = 10.0                              # 초. 초과 시 failed 처리
    apify_actor_id: str = "apify~instagram-scraper"             # Actor slug (tilde URL-safe)
    ig_refresh_days: int = 14                                   # 2주 stale 기준 (user_profiles.ig_fetched_at)

    # ── Auth (MVP v1.1 JWT) ──
    jwt_secret: str = ""                         # HS256 signing key. Must be 32+ random bytes in prod.
    jwt_expiry_days: int = 7                     # No refresh token for MVP. Rotating secret invalidates all sessions.

    # ── Payment (MVP v1.1 Toss Payments) ──
    toss_secret_key: str = ""                    # Server-side key. Test keys start with "test_gsk_", live with "live_gsk_".
    toss_base_url: str = "https://api.tosspayments.com"  # Same host for test and live; keys determine environment.

    # ── CV Pipeline ──
    clip_model: str = "ViT-L-14"                 # CLIP model variant
    clip_pretrained: str = "openai"
    use_mock_clip: bool = True                    # WoZ phase: use random embeddings
    face_photo_max_size: int = 2048               # Max dimension in px

    # ── Coordinate System ──
    coordinate_axes: int = 3                      # Number of aesthetic axes
    embedding_dim: int = 768                      # CLIP embedding dimension
    anchors_per_pole: int = 10                    # Reference anchors per axis pole

    # ── Report ──
    report_delivery_hours: int = 24
    base_url: str = "https://www.sigak.asia"

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
