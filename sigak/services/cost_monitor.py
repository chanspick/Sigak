"""Cost Monitor — Sonnet 일일 비용 리밋 (Phase K5).

CLAUDE.md 본인 확정: "cost_monitor 일일 리밋".

목적:
  - Best Shot 같은 대량 Vision 호출 상품이 비정상적으로 반복되면
    하루 비용이 폭증할 수 있음. 일일 USD cap 으로 안전장치.
  - cap 초과 시 차단 + 로그 + 운영 알림.

설계:
  - Redis INCRBYFLOAT + TTL 기반 일일 counter.
  - Redis 미사용 환경 (dev/테스트) 은 in-memory fallback.
  - 호출부는 `check_and_reserve(estimated_cost)` → 허용 / 거부.
  - 실패 나면 Sonnet 호출 skip + caller 가 refund.
"""
from __future__ import annotations

import logging
import threading
from datetime import datetime, timezone
from typing import Optional

from config import get_settings


logger = logging.getLogger(__name__)


class CostLimitExceeded(Exception):
    """일일 비용 cap 초과 — caller 는 유저 refund + 운영 알림."""


# ─────────────────────────────────────────────
#  In-memory fallback counter (thread-safe)
# ─────────────────────────────────────────────

_LOCAL_LOCK = threading.Lock()
_LOCAL_COUNTER: dict[str, float] = {}   # date_key → accumulated USD


def _today_key(now: Optional[datetime] = None) -> str:
    now = now or datetime.now(timezone.utc)
    return now.strftime("%Y-%m-%d")


def _bucket_key(resource: str, day: str) -> str:
    return f"cost_monitor:{resource}:{day}"


# ─────────────────────────────────────────────
#  Redis helper (lazy import)
# ─────────────────────────────────────────────

def _get_redis():
    """services.sia_session.get_redis 재사용 (singleton).

    Redis 미사용 환경에서는 Exception → caller 가 in-memory fallback.
    """
    from services.sia_session import get_redis
    return get_redis()


# ─────────────────────────────────────────────
#  Public API
# ─────────────────────────────────────────────

def check_and_reserve(
    *,
    resource: str,
    estimated_cost_usd: float,
    daily_cap_usd: Optional[float] = None,
) -> float:
    """비용 예약 — 성공 시 누적 후 신규 총액 반환, 실패 시 CostLimitExceeded.

    Args:
      resource   : "best_shot_sonnet" / "verdict_v2_sonnet" 등 버킷 식별자
      estimated_cost_usd : 이번 호출 예상 비용
      daily_cap_usd      : None 이면 settings.best_shot_cost_daily_usd_cap 사용

    Idempotency 보장 안 함 — caller 가 재시도 시 중복 예약 위험. 구간은
    Sonnet 1회 호출 단위로 짧게 잡기 권장.
    """
    settings = get_settings()
    cap = daily_cap_usd if daily_cap_usd is not None else settings.best_shot_cost_daily_usd_cap
    day = _today_key()
    key = _bucket_key(resource, day)

    # 1차 시도 — Redis
    try:
        r = _get_redis()
        new_total = r.incrbyfloat(key, estimated_cost_usd)
        # TTL 없으면 25h 설정 (롤오버 여유)
        try:
            ttl = r.ttl(key)
            if ttl is None or ttl < 0:
                r.expire(key, 25 * 3600)
        except Exception:
            pass
        new_total_f = float(new_total)
        if new_total_f > cap:
            # 즉시 rollback
            r.incrbyfloat(key, -estimated_cost_usd)
            raise CostLimitExceeded(
                f"{resource}: daily cap {cap:.2f} USD reached ({new_total_f:.2f})"
            )
        logger.info(
            "cost_monitor: resource=%s reserved=%.4f total=%.2f cap=%.2f",
            resource, estimated_cost_usd, new_total_f, cap,
        )
        return new_total_f
    except CostLimitExceeded:
        raise
    except Exception:
        logger.debug("Redis unavailable — using in-memory fallback", exc_info=True)

    # 2차 — in-memory fallback (dev/test)
    with _LOCAL_LOCK:
        current = _LOCAL_COUNTER.get(key, 0.0)
        new_total = current + estimated_cost_usd
        if new_total > cap:
            raise CostLimitExceeded(
                f"{resource}: daily cap {cap:.2f} USD reached (in-memory {new_total:.2f})"
            )
        _LOCAL_COUNTER[key] = new_total
        return new_total


def get_today_total(resource: str) -> float:
    """현재 누적 — 모니터링/디버그 전용."""
    day = _today_key()
    key = _bucket_key(resource, day)
    try:
        r = _get_redis()
        v = r.get(key)
        return float(v) if v is not None else 0.0
    except Exception:
        pass
    with _LOCAL_LOCK:
        return _LOCAL_COUNTER.get(key, 0.0)


def reset_local_counter():
    """테스트 격리 전용 — Redis 에는 영향 없음."""
    with _LOCAL_LOCK:
        _LOCAL_COUNTER.clear()
