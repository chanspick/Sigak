"""user_history JSONB append helper (STEP 4).

users.user_history JSONB 구조:
  {
    "conversations":         [ConversationHistoryEntry, ...],
    "best_shot_sessions":    [BestShotHistoryEntry, ...],
    "aspiration_analyses":   [AspirationHistoryEntry, ...],
    "verdict_sessions":      [VerdictHistoryEntry, ...],
  }

각 리스트: head 가 최신. append_history 는 head 에 prepend + tail pop
(config.user_history_max_per_type 초과 시).

Caller 는 DB 트랜잭션 소유자 — 본 모듈은 UPDATE 만 실행. commit 미실행.
컬럼 없음 / user row 없음 등 예외는 삼킴 (logging 만) — 메인 플로우 영향 금지.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Literal, Optional, Union

from pydantic import BaseModel
from sqlalchemy import text

from config import get_settings


logger = logging.getLogger(__name__)


HistoryCategory = Literal[
    "conversations",
    "best_shot_sessions",
    "aspiration_analyses",
    "verdict_sessions",
]


def append_history(
    db,
    *,
    user_id: str,
    category: HistoryCategory,
    entry: Union[BaseModel, dict[str, Any]],
) -> bool:
    """prepend entry to users.user_history[category] + tail pop.

    Args:
      db: SQLAlchemy session (caller 가 commit 담당)
      user_id: users.id
      category: 4 카테고리 중 하나
      entry: Pydantic 모델 (권장) 또는 dict — JSON 직렬화 가능해야 함

    Returns:
      True 저장 성공, False 스킵/실패 (logging 남김).
    """
    settings = get_settings()
    max_entries = max(1, int(settings.user_history_max_per_type))

    entry_dict = _to_dict(entry)
    if entry_dict is None:
        logger.warning(
            "append_history: entry serialization failed user=%s category=%s",
            user_id, category,
        )
        return False

    try:
        row = db.execute(
            text(
                "SELECT user_history FROM users WHERE id = :uid FOR UPDATE"
            ),
            {"uid": user_id},
        ).first()
    except Exception:
        # users.user_history 컬럼 없음 (migration 미적용) — 조용히 스킵
        logger.warning(
            "append_history: column missing user=%s (migration needed)",
            user_id,
        )
        return False

    if row is None:
        logger.warning("append_history: user not found: %s", user_id)
        return False

    raw = row.user_history
    history = dict(raw) if isinstance(raw, dict) else {}

    current_list = history.get(category)
    if not isinstance(current_list, list):
        current_list = []

    # Prepend + trim
    new_list = [entry_dict, *current_list][:max_entries]
    history[category] = new_list

    try:
        db.execute(
            text(
                "UPDATE users SET user_history = CAST(:h AS jsonb) "
                "WHERE id = :uid"
            ),
            {
                "uid": user_id,
                "h": json.dumps(history, ensure_ascii=False, default=str),
            },
        )
    except Exception:
        logger.exception(
            "append_history UPDATE failed user=%s category=%s", user_id, category,
        )
        return False

    logger.info(
        "user_history append: user=%s category=%s new_len=%d (max=%d)",
        user_id, category, len(new_list), max_entries,
    )
    return True


def _to_dict(entry: Union[BaseModel, dict[str, Any]]) -> Optional[dict[str, Any]]:
    """entry → JSON serializable dict. 실패 시 None."""
    if isinstance(entry, BaseModel):
        try:
            return entry.model_dump(mode="json")
        except Exception:
            logger.exception("_to_dict: pydantic model_dump failed")
            return None
    if isinstance(entry, dict):
        # JSON 직렬화 가능 확인 (datetime 등은 default=str 로 처리되지만,
        # 최소 dict 구조 확인만)
        try:
            json.dumps(entry, ensure_ascii=False, default=str)
            return entry
        except Exception:
            logger.exception("_to_dict: dict not JSON serializable")
            return None
    logger.warning("_to_dict: unsupported entry type: %s", type(entry).__name__)
    return None
