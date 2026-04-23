"""Sia 응답 샘플 fixture loader — Phase D (Task 8).

디렉터리 레이아웃:
  tests/fixtures/sia_samples/{female,male}/<turn_type>.json

각 fixture 스키마:
  fixture_id : str               — 고유 식별자 ("<gender>_<turn_type>_v1")
  gender     : "female"|"male"
  turn_type  : decide_next_turn 반환값 15 종 중 하나
  context    : {
      user_name_display: str     — expected_response 안에 이미 치환된 이름
      mock_analysis: dict|None   — IgFeedAnalysis 형태 (없어도 됨)
      session_state: dict        — spectrum_log / precision_hits / precision_misses
  }
  expected_response        : str — 실 Haiku 가 생성할 법한 자연 텍스트
  validator_expectations   : {
      assertion_count_max  : int
      abstract_noun_count  : int
      banned_ending_count  : int
      whitelist_alignment  : bool
  }

loader 는 Python only. 실 Haiku / Apify 호출 없음. 비용 0.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Iterator


FIXTURE_ROOT = Path(__file__).parent


def load_fixture(gender: str, turn_type: str) -> dict:
    """단일 fixture 조회. 없으면 FileNotFoundError."""
    path = FIXTURE_ROOT / gender / f"{turn_type}.json"
    if not path.exists():
        raise FileNotFoundError(f"Missing fixture: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def load_all_fixtures() -> list[dict]:
    """모든 gender × turn_type fixture 를 평탄화해서 반환."""
    result: list[dict] = []
    for gender_dir in sorted(FIXTURE_ROOT.iterdir()):
        if not gender_dir.is_dir() or gender_dir.name.startswith("__"):
            continue
        for fx_path in sorted(gender_dir.glob("*.json")):
            result.append(json.loads(fx_path.read_text(encoding="utf-8")))
    return result


def iter_fixture_paths() -> Iterator[Path]:
    for gender_dir in sorted(FIXTURE_ROOT.iterdir()):
        if not gender_dir.is_dir() or gender_dir.name.startswith("__"):
            continue
        yield from sorted(gender_dir.glob("*.json"))
