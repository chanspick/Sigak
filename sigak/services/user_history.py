"""user_history JSONB append helper (STEP 4).

users.user_history JSONB 구조:
  {
    "conversations":         [ConversationHistoryEntry, ...],
    "best_shot_sessions":    [BestShotHistoryEntry, ...],
    "aspiration_analyses":   [AspirationHistoryEntry, ...],
    "verdict_sessions":      [VerdictHistoryEntry, ...],
    "pi_history":            [PiHistoryEntry, ...],            # Phase I (Backward echo)
    "trajectory_events":     [TrajectoryEvent, ...],
  }

각 리스트: head 가 최신. append_history 는 head 에 prepend + tail pop
(config.user_history_max_per_type 초과 시).

Caller 는 DB 트랜잭션 소유자 — 본 모듈은 UPDATE 만 실행. commit 미실행.
컬럼 없음 / user row 없음 등 예외는 삼킴 (logging 만) — 메인 플로우 영향 금지.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
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
    "pi_history",
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

    # CLAUDE.md trajectory[] populate — 5 카테고리 통합 시계열 자동 누적.
    # 좌표/점수 미산출 카테고리(verdict/best_shot/conversation)도 timestamp+id 기록.
    # aspiration / pi 는 coord_3axis 추출 가능. Tail truncate: max_entries * 5.
    traj_event = _build_trajectory_event(category, entry_dict)
    if traj_event is not None:
        traj_list = history.get("trajectory_events")
        if not isinstance(traj_list, list):
            traj_list = []
        history["trajectory_events"] = [traj_event, *traj_list][: max_entries * 5]

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


def _build_trajectory_event(
    category: str, entry: dict[str, Any]
) -> Optional[dict[str, Any]]:
    """5 카테고리 entry → trajectory_events 항목 dict.

    Args:
      category: append_history 의 category ("conversations" / "best_shot_sessions" /
        "aspiration_analyses" / "verdict_sessions" / "pi_history")
      entry: model_dump 결과 dict

    Returns:
      trajectory event dict — captured_at(iso) / event_type / reference_id +
      coordinate_snapshot (aspiration: aspiration_vector_snapshot.from_coord /
      pi: coord_3axis 직접) + score_at_time (None, vault 조립 시 fallback).
      reference_id 추출 실패 시 None.
    """
    type_map = {
        "conversations": ("conversation", "session_id", "started_at"),
        "verdict_sessions": ("verdict", "session_id", "created_at"),
        "best_shot_sessions": ("best_shot", "session_id", "created_at"),
        "aspiration_analyses": ("aspiration", "analysis_id", "created_at"),
        "pi_history": ("pi", "report_id", "created_at"),
    }
    if category not in type_map:
        return None
    event_type, id_key, ts_key = type_map[category]

    reference_id = entry.get(id_key)
    if not reference_id:
        return None
    reference_id = str(reference_id)

    captured_at_raw = entry.get(ts_key)
    if isinstance(captured_at_raw, datetime):
        captured_at_str = captured_at_raw.isoformat()
    elif isinstance(captured_at_raw, str) and captured_at_raw.strip():
        captured_at_str = captured_at_raw.strip()
    else:
        captured_at_str = datetime.now(timezone.utc).isoformat()

    coordinate_snapshot: Optional[dict[str, float]] = None
    if event_type == "aspiration":
        gap = entry.get("aspiration_vector_snapshot")
        if isinstance(gap, dict):
            from_c = (
                gap.get("from_coord")
                or gap.get("from")
                or gap.get("user_coord")
            )
            if isinstance(from_c, dict):
                try:
                    coordinate_snapshot = {
                        "shape": float(from_c.get("shape", 0.5)),
                        "volume": float(from_c.get("volume", 0.5)),
                        "age": float(from_c.get("age", 0.5)),
                    }
                except (TypeError, ValueError):
                    coordinate_snapshot = None
    elif event_type == "pi":
        # PI 는 coord_3axis 를 직접 entry 에 보유 (PiHistoryEntry.coord_3axis)
        coord_raw = entry.get("coord_3axis")
        if isinstance(coord_raw, dict):
            try:
                coordinate_snapshot = {
                    "shape": float(coord_raw.get("shape", 0.5)),
                    "volume": float(coord_raw.get("volume", 0.5)),
                    "age": float(coord_raw.get("age", 0.5)),
                }
            except (TypeError, ValueError):
                coordinate_snapshot = None

    return {
        "captured_at": captured_at_str,
        "event_type": event_type,
        "reference_id": reference_id,
        "coordinate_snapshot": coordinate_snapshot,
        "score_at_time": None,
    }


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
