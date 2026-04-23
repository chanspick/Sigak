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
