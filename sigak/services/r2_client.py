"""Cloudflare R2 wrapper (Phase K2).

CLAUDE.md §9.2 R2 레이아웃:
  /users/{user_id}/
    feed_snapshots/{snapshot_id}/ (영구)
    aspiration_targets/...        (영구)
    pi_reports/{report_id}/       (영구)
    best_shot/uploads/{session_id}/  (24h TTL)
    best_shot/selected/{session_id}/ (30일)

MVP:
  - boto3 S3-compatible 기반 R2 호출 (put/get/delete/exists)
  - credentials 미설정 시 local fallback — dev 환경용. 프로덕션 배포 시 env 필수.
  - TTL 는 R2 측 Lifecycle 규칙으로 관리 (이 wrapper 는 trigger 만 기록).

설계:
  - 클라이언트 싱글톤
  - 키 prefix helper (user_photo_key / best_shot_upload_key / ...)
  - put_bytes / get_bytes / delete_prefix / exists
  - local fallback : Path 기반 저장, 동일 인터페이스
"""
from __future__ import annotations

import logging
import shutil
import time
from pathlib import Path
from typing import Optional

from config import get_settings


logger = logging.getLogger(__name__)


class R2Error(Exception):
    """R2 I/O 오류. caller 는 필요 시 fallback 처리."""


# ─────────────────────────────────────────────
#  Client singleton
# ─────────────────────────────────────────────

_client = None
_client_mode: Optional[str] = None   # "r2" | "local" | None


def _init_client():
    """R2 boto3 클라이언트 or local fallback 결정. lazy init."""
    global _client, _client_mode
    if _client is not None and _client_mode is not None:
        return

    settings = get_settings()
    have_creds = bool(
        settings.r2_endpoint_url
        and settings.r2_access_key_id
        and settings.r2_secret_access_key
    )

    if have_creds:
        try:
            import boto3
            from botocore.config import Config

            _client = boto3.client(
                "s3",
                endpoint_url=settings.r2_endpoint_url,
                aws_access_key_id=settings.r2_access_key_id,
                aws_secret_access_key=settings.r2_secret_access_key,
                region_name="auto",
                config=Config(signature_version="s3v4"),
            )
            _client_mode = "r2"
            logger.info("R2 client initialized (endpoint=%s)", settings.r2_endpoint_url)
            return
        except Exception:
            logger.exception("R2 client init failed — falling back to local")

    # Local fallback
    fallback_dir = settings.r2_local_fallback_dir or str(
        Path.home() / ".sigak_r2_local"
    )
    _client = {"base_dir": Path(fallback_dir)}
    _client_mode = "local"
    Path(fallback_dir).mkdir(parents=True, exist_ok=True)
    logger.warning(
        "R2 credentials absent — using local fallback at %s (DEV ONLY)",
        fallback_dir,
    )


def reset_client():
    """테스트 격리."""
    global _client, _client_mode
    _client = None
    _client_mode = None


# ─────────────────────────────────────────────
#  Key helpers
# ─────────────────────────────────────────────

def user_photo_key(user_id: str, sub_path: str) -> str:
    """유저 스페이스 내부 키. leading slash 없음."""
    sub = sub_path.lstrip("/")
    return f"users/{user_id}/{sub}"


def best_shot_upload_key(user_id: str, session_id: str, photo_id: str) -> str:
    return user_photo_key(user_id, f"best_shot/uploads/{session_id}/{photo_id}")


def best_shot_selected_key(user_id: str, session_id: str, photo_id: str) -> str:
    return user_photo_key(user_id, f"best_shot/selected/{session_id}/{photo_id}")


# ─────────────────────────────────────────────
#  user_media prefix — STEP 1 전수 R2 저장 (v1 연료)
#  user_media/{user_id}/
#    ├── ig_snapshots/{timestamp}/photo_NN.jpg
#    └── aspiration_targets/{analysis_id}/photo_NN.jpg
#  본인 IG 사진 (페어링) 은 aspiration_users/ 별도 복사 대신 기존
#  ig_snapshots R2 URL 참조 (비용 절감).
# ─────────────────────────────────────────────

def user_media_key(user_id: str, sub_path: str) -> str:
    """user_media 네임스페이스. 신규 전수 저장 대상."""
    sub = sub_path.lstrip("/")
    return f"user_media/{user_id}/{sub}"


def ig_snapshot_dir(user_id: str, snapshot_ts: str) -> str:
    """Sia 진입 시점 IG 피드 스냅샷 디렉토리 prefix. 10장 단위."""
    return user_media_key(user_id, f"ig_snapshots/{snapshot_ts}/")


def ig_snapshot_photo_key(user_id: str, snapshot_ts: str, index: int) -> str:
    return user_media_key(
        user_id, f"ig_snapshots/{snapshot_ts}/photo_{index:02d}.jpg"
    )


def aspiration_target_dir(user_id: str, analysis_id: str) -> str:
    """추구미 타겟 IG/Pinterest 사진 디렉토리 prefix."""
    return user_media_key(user_id, f"aspiration_targets/{analysis_id}/")


def aspiration_target_photo_key(user_id: str, analysis_id: str, index: int) -> str:
    return user_media_key(
        user_id, f"aspiration_targets/{analysis_id}/photo_{index:02d}.jpg"
    )


# ─────────────────────────────────────────────
#  v1.5 raw 영구 보존 (Apify raw + Vision Sonnet raw)
#  PII 격리 위해 R2 분리 저장. DB / LLM 주입 금지.
# ─────────────────────────────────────────────

def aspiration_apify_raw_key(user_id: str, analysis_id: str) -> str:
    """추구미 분석 시 Apify scraper 응답 raw JSON 저장 키."""
    return user_media_key(
        user_id, f"aspiration_targets/{analysis_id}/apify_raw.json"
    )


def aspiration_vision_raw_key(user_id: str, analysis_id: str) -> str:
    """추구미 분석 시 Sonnet Vision response raw text 저장 키."""
    return user_media_key(
        user_id, f"aspiration_targets/{analysis_id}/vision_raw.json"
    )


def ig_snapshot_vision_raw_key(user_id: str, snapshot_ts: str) -> str:
    """본인 IG essentials 의 Sonnet Vision response raw text 저장 키."""
    return user_media_key(
        user_id, f"ig_snapshots/{snapshot_ts}/vision_raw.json"
    )


def verdict_sonnet_raw_key(user_id: str, verdict_id: str) -> str:
    """Verdict v2 Sonnet cross-analysis response raw text 저장 키.

    데이터 기업 원칙 — LLM 출력 영구 보존. 응답 본문이 수 KB 라 BYTEA
    DB 누적 부담 → R2 영구 저장. 실패 시 r2_persistence dead-letter.
    """
    return user_media_key(
        user_id, f"verdicts/{verdict_id}/sonnet_raw.txt"
    )


def pi_llm_raw_key(user_id: str, report_id: str, step: str) -> str:
    """옛 SIGAK_V3 PI 의 LLM 호출별 raw response 저장 키.

    step 예시: face_structure / interview / type_match / gap_narration / finale.
    각 호출의 원시 응답 (재현 불가능한 LLM 텍스트) 영구 보존.
    """
    safe_step = "".join(c for c in step if c.isalnum() or c in "_-")
    return user_media_key(
        user_id, f"reports/{report_id}/llm_raw/{safe_step}.txt"
    )


# ─────────────────────────────────────────────
#  Public API
# ─────────────────────────────────────────────

def put_bytes(
    key: str,
    data: bytes,
    *,
    bucket: Optional[str] = None,
    content_type: str = "application/octet-stream",
) -> str:
    """bytes → R2. 저장된 key 반환.

    bucket 생략 시 r2_bucket_user_photos 기본 사용.
    """
    _init_client()
    settings = get_settings()
    effective_bucket = bucket or settings.r2_bucket_user_photos

    if _client_mode == "r2":
        try:
            _client.put_object(
                Bucket=effective_bucket,
                Key=key,
                Body=data,
                ContentType=content_type,
            )
        except Exception as e:
            raise R2Error(f"put failed: {key}: {e}") from e
        return key

    # Local fallback
    base: Path = _client["base_dir"]
    full = base / effective_bucket / key
    full.parent.mkdir(parents=True, exist_ok=True)
    full.write_bytes(data)
    return key


def put_bytes_with_retry(
    key: str,
    data: bytes,
    *,
    bucket: Optional[str] = None,
    content_type: str = "application/octet-stream",
    retries: int = 3,
    backoff_seconds: float = 1.0,
) -> str:
    """put_bytes 를 retry 와 함께. 모두 실패 시 R2Error raise.

    데이터 기업 원칙: 일시 장애 (network blip / 5xx) 회복 + 그래도 실패 시
    호출처가 dead-letter (services.r2_persistence) 로 보존하도록 raise.

    Args:
      retries: 시도 횟수 (기본 3회). 1회 = retry 없음.
      backoff_seconds: 첫 backoff. 매 실패마다 2배 (exponential).

    Returns: 성공 시 저장된 key.
    Raises: R2Error — retries 회 모두 실패.
    """
    last_exc: Optional[Exception] = None
    delay = backoff_seconds
    for attempt in range(1, max(retries, 1) + 1):
        try:
            return put_bytes(
                key, data, bucket=bucket, content_type=content_type,
            )
        except Exception as e:  # R2Error 포함 모든 예외
            last_exc = e
            logger.warning(
                "[r2_client] put attempt %d/%d failed key=%s err=%s",
                attempt, retries, key, e,
            )
            if attempt < retries:
                time.sleep(delay)
                delay *= 2
    raise R2Error(
        f"put_bytes_with_retry failed after {retries} attempts: {key}: {last_exc}"
    ) from last_exc


def get_bytes(key: str, *, bucket: Optional[str] = None) -> bytes:
    """key → bytes. 없으면 R2Error."""
    _init_client()
    settings = get_settings()
    effective_bucket = bucket or settings.r2_bucket_user_photos

    if _client_mode == "r2":
        try:
            resp = _client.get_object(Bucket=effective_bucket, Key=key)
            return resp["Body"].read()
        except Exception as e:
            raise R2Error(f"get failed: {key}: {e}") from e

    base: Path = _client["base_dir"]
    full = base / effective_bucket / key
    if not full.exists():
        raise R2Error(f"not found (local): {key}")
    return full.read_bytes()


def exists(key: str, *, bucket: Optional[str] = None) -> bool:
    _init_client()
    settings = get_settings()
    effective_bucket = bucket or settings.r2_bucket_user_photos

    if _client_mode == "r2":
        try:
            _client.head_object(Bucket=effective_bucket, Key=key)
            return True
        except Exception:
            return False

    base: Path = _client["base_dir"]
    return (base / effective_bucket / key).exists()


def delete_prefix(prefix: str, *, bucket: Optional[str] = None) -> int:
    """prefix 아래 전수 삭제. 삭제된 개수 반환. 운영: best_shot abort/expire."""
    _init_client()
    settings = get_settings()
    effective_bucket = bucket or settings.r2_bucket_user_photos

    deleted = 0
    if _client_mode == "r2":
        try:
            paginator = _client.get_paginator("list_objects_v2")
            for page in paginator.paginate(Bucket=effective_bucket, Prefix=prefix):
                keys = [{"Key": obj["Key"]} for obj in page.get("Contents", [])]
                if not keys:
                    continue
                _client.delete_objects(
                    Bucket=effective_bucket, Delete={"Objects": keys},
                )
                deleted += len(keys)
        except Exception as e:
            raise R2Error(f"delete_prefix failed: {prefix}: {e}") from e
        return deleted

    base: Path = _client["base_dir"]
    target = base / effective_bucket / prefix
    if target.exists():
        if target.is_dir():
            for fp in target.rglob("*"):
                if fp.is_file():
                    deleted += 1
            shutil.rmtree(target)
        elif target.is_file():
            target.unlink()
            deleted += 1
    return deleted


def public_url(key: str) -> Optional[str]:
    """CDN public base URL 이 설정돼 있으면 유저 노출용 URL 반환. 없으면 None."""
    settings = get_settings()
    if not settings.r2_public_base_url:
        return None
    base = settings.r2_public_base_url.rstrip("/")
    return f"{base}/{key}"


def get_client_mode() -> Optional[str]:
    """현재 client 모드 반환 ('r2' / 'local' / None). 테스트 / 디버그 용."""
    _init_client()
    return _client_mode
