"""Knowledge Base 로더 (Phase G6).

CLAUDE.md §4.5 — 사람 큐레이션 기반 외부 지식 레이어.

MVP 범위:
- YAML 파일 로드 + Pydantic 검증
- 성별/시즌 필터
- KnowledgeMatcher (Phase G7) 에서 소비

Notion 전환은 v1.1+ (환경변수 기반 backend 스위치 예정).
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import yaml

from schemas.knowledge import (
    Gender,
    MethodologyItem,
    ReferenceItem,
    TrendItem,
)


logger = logging.getLogger(__name__)

_KB_ROOT = Path(__file__).parent
_TRENDS_DIR = _KB_ROOT / "trends"
_METHODS_DIR = _KB_ROOT / "methodology"
_REFS_DIR = _KB_ROOT / "references"


# ─────────────────────────────────────────────
#  Loader
# ─────────────────────────────────────────────

def load_trends(
    gender: Optional[Gender] = None,
    season: Optional[str] = None,
) -> list[TrendItem]:
    """트렌드 YAML 로드 + 필터. 부분 검증 실패 항목은 스킵 + 경고 로그."""
    items: list[TrendItem] = []
    for path in _iter_yaml(_TRENDS_DIR, gender):
        raw = _load_yaml_list(path)
        for entry in raw:
            try:
                item = TrendItem.model_validate(entry)
            except Exception:
                logger.warning("invalid trend entry in %s: %s", path.name, entry.get("trend_id"))
                continue
            if gender is not None and item.gender != gender:
                continue
            if season is not None and item.season != season:
                continue
            items.append(item)
    return items


def load_methodologies(gender: Optional[Gender] = None) -> list[MethodologyItem]:
    items: list[MethodologyItem] = []
    for path in _iter_yaml(_METHODS_DIR, gender):
        raw = _load_yaml_list(path)
        for entry in raw:
            try:
                item = MethodologyItem.model_validate(entry)
            except Exception:
                logger.warning("invalid methodology in %s", path.name)
                continue
            if gender is not None and item.gender != gender:
                continue
            items.append(item)
    return items


def load_references(gender: Optional[Gender] = None) -> list[ReferenceItem]:
    items: list[ReferenceItem] = []
    for path in _iter_yaml(_REFS_DIR, gender):
        raw = _load_yaml_list(path)
        for entry in raw:
            try:
                item = ReferenceItem.model_validate(entry)
            except Exception:
                logger.warning("invalid reference in %s", path.name)
                continue
            if gender is not None and item.gender != gender:
                continue
            items.append(item)
    return items


# ─────────────────────────────────────────────
#  Helpers
# ─────────────────────────────────────────────

def _iter_yaml(root: Path, gender: Optional[Gender]):
    """root 하위 YAML 파일 iter. gender 지정 시 해당 하위 폴더만."""
    if not root.exists():
        return
    if gender:
        sub = root / gender
        if sub.exists():
            yield from sorted(sub.glob("*.yaml"))
        return
    yield from sorted(root.glob("**/*.yaml"))


def _load_yaml_list(path: Path) -> list[dict]:
    """단일 YAML 파일 → list[dict]. 최상위는 list 또는 {items: [...]} 허용."""
    try:
        with path.open("r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
    except yaml.YAMLError:
        logger.exception("YAML parse failed: %s", path)
        return []
    if data is None:
        return []
    if isinstance(data, list):
        return data
    if isinstance(data, dict) and isinstance(data.get("items"), list):
        return data["items"]
    logger.warning("YAML shape unexpected in %s", path)
    return []
