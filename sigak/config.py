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

    # ── Cache / Session Store (v2 Priority 1 D3) ──
    redis_url: str = "redis://localhost:6379/0"                 # Sia session 저장. Railway 에선 rediss://...
    sia_session_ttl_seconds: int = 300                          # 5분 sliding TTL
    sia_session_max_turns: int = 50                             # soft limit — Sia 가 "정리하겠습니다" 제안

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
    ig_fetch_timeout: float = 60.0                              # 초. 대형 계정 대응 여유. MCP 실측: 30 results ≈ 20s, cristiano급 ≈ 50s
    apify_actor_id: str = "apify~instagram-scraper"             # Actor slug (tilde URL-safe)
    apify_pinterest_actor_id: str = "devcake~pinterest-data-scraper"   # Pinterest 보드 scraper (v1.5 raw 보존 어댑터)
    pinterest_enabled: bool = True                               # v1.5 — 추구미 Pinterest 정식 활성화. devcake actor 어댑터 + raw R2 보존.
    ig_refresh_days: int = 14                                   # 2주 stale 기준 (user_profiles.ig_fetched_at)

    # ── Cloudflare R2 (Phase K) ──
    r2_endpoint_url: str = ""                                    # https://{account_id}.r2.cloudflarestorage.com
    r2_access_key_id: str = ""
    r2_secret_access_key: str = ""
    r2_bucket_user_photos: str = "sigak-user-photos"
    r2_bucket_aspiration: str = "sigak-aspiration-targets"
    r2_public_base_url: str = ""                                 # CDN 퍼블릭 호스트 (optional)
    r2_local_fallback_dir: str = ""                              # 미설정 시 ~/.sigak_r2_local

    # ── Best Shot (Phase K) ──
    best_shot_min_upload: int = 50                               # 50장 미만 → 피드 추천 유도
    best_shot_max_upload: int = 500
    best_shot_quality_cutoff: float = 0.35                       # heuristic 통과 기준 (0-1)
    best_shot_cost_daily_usd_cap: float = 20.0                   # Sonnet 일일 총 비용 cap

    # ── user_history / IG 스냅샷 (Aspiration v1 풀 패치 STEP 1) ──
    user_history_max_per_type: int = 10                          # 각 history 배열 최대 길이 (초과 시 tail pop)
    ig_snapshot_ttl_hours: int = 24                              # Sia 재진입 24h 캐시 기준
    inject_history_token_limit: int = 80_000                     # LLM 주입 시 history 토큰 상한 (초과 시 summarize)

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
