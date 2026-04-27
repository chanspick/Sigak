"""R2 영구 보존 layer — dead-letter aware put.

데이터 기업 원칙: raw bytes 손실 절대 금지. R2 일시 장애 / 영구 장애 모두
대응 가능하도록 retry → dead-letter (DB BYTEA) 2단계 보존.

Flow:
  1. r2_client.put_bytes_with_retry (3회 exponential backoff, 1s/2s/4s)
  2. 그래도 실패 → r2_upload_failures 테이블에 raw bytes 그대로 INSERT
  3. 운영자/cron 이 retry_dead_letter() 발동 → 다시 R2 put 시도

호출처가 db session 명시적 주입. r2_client 자체는 DB 무관 유지.

사용처:
  - services.ig_scraper._upload_snapshot_photo_to_r2  (IG 피드 사진)
  - services.aspiration_common.materialize_ig_vision_raw_to_r2  (Vision raw txt)
  - services.aspiration_common.materialize_apify_raw_to_r2  (Apify raw JSON)
  - 향후 추가: best_shot upload / verdict / pi 사진 호출처 등
"""
from __future__ import annotations

import logging
import uuid
from typing import Optional

from sqlalchemy import text

from services import r2_client
from services.r2_client import R2Error


logger = logging.getLogger(__name__)


class DeadLetterPersistError(RuntimeError):
    """R2 put 도 실패하고 dead-letter INSERT 도 실패한 정말 위급한 상황.

    호출처는 이 예외를 logger.critical 로 잡아야 함 — 운영자 호출 필요.
    데이터 기업 원칙 위배 발생 (raw 손실 가능).
    """


def put_bytes_durable(
    db,
    *,
    user_id: str,
    purpose: str,
    r2_key: str,
    data: bytes,
    content_type: str = "application/octet-stream",
    src_url: Optional[str] = None,
    bucket: Optional[str] = None,
    retries: int = 3,
) -> tuple[str, bool]:
    """raw 손실 0 보장 put. R2 retry → 실패 시 dead-letter row INSERT.

    Args:
      db: SQLAlchemy session. 호출처 트랜잭션. caller 가 commit 책임.
      user_id: 소유자 (FK CASCADE).
      purpose: 'ig_snapshot' | 'ig_vision_raw' | 'aspiration_photo' | ...
        (운영 모니터링 / retry_dead_letter 분기에 사용)
      r2_key: 업로드할 R2 키. dead-letter 시에도 동일 키 보존 (재시도 시 사용).
      data: raw bytes 그 자체.
      content_type: image/jpeg 등.
      src_url: 원본 fetch URL (IG CDN 등). 재수집 fallback 메타.
      bucket: 명시 안 하면 r2_bucket_user_photos.
      retries: r2_client.put_bytes_with_retry 의 시도 횟수.

    Returns:
      (r2_key, durable_in_r2)
        durable_in_r2=True  → R2 에 저장됨, 정상 사용 가능.
        durable_in_r2=False → R2 실패, dead-letter 에 보존됨. r2_key 는
                              아직 R2 에 없으니 caller 가 응답 URL 로 사용 X.

    Raises:
      DeadLetterPersistError: R2 put 도, dead-letter INSERT 도 모두 실패.
        진짜 raw 손실 위험 — 운영자 호출 필요.
    """
    # 1) R2 put with retry
    try:
        r2_client.put_bytes_with_retry(
            r2_key, data, bucket=bucket,
            content_type=content_type, retries=retries,
        )
        return r2_key, True
    except R2Error as e:
        logger.error(
            "[r2_persistence] R2 put failed after retry → dead-letter "
            "user=%s purpose=%s key=%s err=%s",
            user_id, purpose, r2_key, e,
        )
        try:
            db.execute(
                text(
                    "INSERT INTO r2_upload_failures "
                    "  (id, user_id, purpose, r2_key, payload, content_type, "
                    "   src_url, error_kind, attempts, status, "
                    "   created_at, last_attempted_at) "
                    "VALUES (:id, :uid, :purpose, :key, :payload, :ct, "
                    "        :src, :err, :att, 'pending', NOW(), NOW())"
                ),
                {
                    "id": uuid.uuid4().hex,
                    "uid": user_id,
                    "purpose": purpose,
                    "key": r2_key,
                    "payload": data,
                    "ct": content_type,
                    "src": src_url,
                    "err": type(e).__name__,
                    "att": retries,
                },
            )
            return r2_key, False
        except Exception as ie:
            # R2 도 실패하고 dead-letter 도 실패. 진짜 위급.
            logger.critical(
                "[r2_persistence] DEAD-LETTER INSERT FAILED — DATA LOSS RISK "
                "user=%s purpose=%s key=%s r2_err=%s dl_err=%s",
                user_id, purpose, r2_key, e, ie,
            )
            raise DeadLetterPersistError(
                f"R2 put + dead-letter both failed: {r2_key}"
            ) from ie


def retry_dead_letter(
    db,
    *,
    limit: int = 50,
    purposes: Optional[list[str]] = None,
) -> dict:
    """pending dead-letter row 들을 R2 에 재시도. 운영자/cron 발동.

    각 row 에 대해:
      - r2_client.put_bytes_with_retry (또 retry — 정말 일시 장애였다면 회복)
      - 성공 → status='completed', completed_at=NOW()
      - 실패 → attempts+1, last_attempted_at=NOW() (status 유지)

    Args:
      limit: 한 번에 처리할 최대 row 수 (DoS 방지).
      purposes: 특정 purpose 만 재시도 (None = 전체).

    Returns:
      {scanned, recovered, still_pending, errors}
    """
    if db is None:
        return {"scanned": 0, "recovered": 0, "still_pending": 0, "errors": 0}

    where = "status = 'pending'"
    params: dict = {"lim": int(limit)}
    if purposes:
        where += " AND purpose = ANY(:purposes)"
        params["purposes"] = list(purposes)

    rows = db.execute(
        text(
            "SELECT id, user_id, purpose, r2_key, payload, content_type "
            f"FROM r2_upload_failures WHERE {where} "
            "ORDER BY created_at ASC LIMIT :lim"
        ),
        params,
    ).fetchall()

    recovered = 0
    errors = 0
    for row in rows:
        try:
            r2_client.put_bytes_with_retry(
                row.r2_key,
                bytes(row.payload),
                content_type=row.content_type or "application/octet-stream",
                retries=2,  # 가벼운 재시도 (dead-letter 자체가 retry 후의 잔여)
            )
            db.execute(
                text(
                    "UPDATE r2_upload_failures SET "
                    "  status='completed', completed_at=NOW(), "
                    "  last_attempted_at=NOW() "
                    "WHERE id=:id"
                ),
                {"id": row.id},
            )
            recovered += 1
        except Exception:
            db.execute(
                text(
                    "UPDATE r2_upload_failures SET "
                    "  attempts = attempts + 1, last_attempted_at=NOW() "
                    "WHERE id=:id"
                ),
                {"id": row.id},
            )
            errors += 1

    db.commit()
    return {
        "scanned": len(rows),
        "recovered": recovered,
        "still_pending": len(rows) - recovered,
        "errors": errors,
    }
