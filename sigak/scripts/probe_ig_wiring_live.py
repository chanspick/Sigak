"""IG wiring 실 경로 probe — fetch_ig_raw + attach_vision_analysis + chat/start.

Step 4 + Step 5 시뮬레이션:
  (4) 분리 저장 경로 실 Apify + Sonnet 로 각 단계 소요 시간 + 데이터 정합 검증
  (5) chat/start 호출 → Haiku 호출 → vision_summary prompt 주입 + opening_message

env 요구사항 probe_ig_analysis.py 와 동일.

사용:
  RUN_PROBE_LIVE=1 IG_ENABLED=true \\
    APIFY_API_KEY=... ANTHROPIC_API_KEY=... \\
    PROBE_IG_HANDLE=xhan0_0 \\
    .venv/Scripts/python.exe sigak/scripts/probe_ig_wiring_live.py
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def _require() -> str:
    if os.environ.get("RUN_PROBE_LIVE") != "1":
        print("[skipped] RUN_PROBE_LIVE != 1")
        sys.exit(0)
    h = os.environ.get("PROBE_IG_HANDLE", "").strip()
    if not h:
        print("[error] PROBE_IG_HANDLE 미설정"); sys.exit(1)
    for k in ("APIFY_API_KEY", "ANTHROPIC_API_KEY"):
        if not os.environ.get(k):
            print(f"[error] {k} 미설정"); sys.exit(1)
    return h


def _divider(title: str) -> None:
    print()
    print("=" * 60)
    print(title)
    print("=" * 60)


class _FakeDB:
    def __init__(self):
        self.upserts: list[tuple] = []
        self.commits = 0

    def commit(self):
        self.commits += 1

    def rollback(self): pass

    def close(self): pass


def main() -> int:
    handle = _require()

    from services import ig_scraper
    from services.sia_hardcoded import render_hardcoded
    from services.sia_prompts_v4 import load_haiku_prompt
    from services.sia_llm import call_sia_turn_with_retry, _render_ig_summary
    from services.sia_decision import decide
    from schemas.sia_state import ConversationState, MsgType

    # ── Step 4a: fetch_ig_raw 실 Apify
    _divider(f"Step 4a — fetch_ig_raw(@{handle}) — Apify only")
    t0 = time.time()
    status, preview = ig_scraper.fetch_ig_raw(handle)
    t_apify = time.time() - t0
    print(f"status: {status} | elapsed: {t_apify:.2f}s")
    if preview is None:
        print("[end] preview 없음"); return 0
    print(f"scope: {preview.scope} | analysis: {preview.analysis}")
    posts = preview.latest_posts or []
    preview_urls = [p.display_url for p in posts if p.display_url][:6]
    print(f"preview_urls count: {len(preview_urls)}")

    # ── Step 4b: attach_vision_analysis 실 Sonnet
    _divider("Step 4b — attach_vision_analysis — Sonnet Vision")
    t1 = time.time()
    analyzed, _vision_raw = ig_scraper.attach_vision_analysis(preview)
    t_vision = time.time() - t1
    print(f"elapsed: {t_vision:.2f}s")
    print(f"analysis populated: {analyzed.analysis is not None}")
    print(f"last_analyzed_post_count: {analyzed.last_analyzed_post_count}")

    _divider("Step 4 합산 시간")
    print(f"Apify:  {t_apify:.2f}s")
    print(f"Vision: {t_vision:.2f}s")
    print(f"Total:  {t_apify + t_vision:.2f}s")

    # ── Step 5: chat/start 시뮬레이션 — Haiku 호출 + vision_summary 주입
    _divider("Step 5 — chat/start 시뮬: load_haiku_prompt + call_sia_turn_with_retry")

    state = ConversationState(
        session_id="probe-smoke",
        user_id="u-probe",
        user_name="한",
    )
    state.gender = "female"
    # ig_feed_cache 는 dict 형태 (state 저장 포맷). model_dump(mode="json") 후 주입.
    state.ig_feed_cache = analyzed.model_dump(mode="json")

    # decide 1회 — 첫 턴이면 M1 결합
    composition = decide(state)
    print(f"decide() primary: {composition.primary_type.value}")
    print(f"         secondary: {composition.secondary_type.value if composition.secondary_type else None}")
    print(f"         is_combined: {composition.is_combined}")

    # M1 결합 — OPENING 하드코딩
    opening = render_hardcoded(MsgType.OPENING_DECLARATION, state)
    print(f"\nOPENING_DECLARATION hardcoded:")
    print(f"  {opening}")

    # OBSERVATION Haiku 호출
    vision_summary = _render_ig_summary(state.ig_feed_cache)
    print(f"\nvision_summary length: {len(vision_summary)} chars")
    print(f"vision_summary first 200: {vision_summary[:200]}...")

    prompt = load_haiku_prompt(
        MsgType.OBSERVATION,
        state,
        user_flags=None,
        vision_summary=vision_summary,
        is_first_turn=True,
        is_combined=True,
        secondary_type=MsgType.OBSERVATION,
    )
    print(f"\nsystem prompt length: {len(prompt)} chars")

    t2 = time.time()
    obs_text_raw = call_sia_turn_with_retry(
        system_prompt=prompt,
        messages_history=[{"role": "user", "content": "(대화 시작)"}],
    )
    t_haiku = time.time() - t2
    print(f"\nHaiku elapsed: {t_haiku:.2f}s")
    print(f"\nOBSERVATION Haiku 응답 (raw):")
    print(f"  {obs_text_raw}")

    # M1 meta preamble 후처리 (routes/sia.py 와 동일 경로)
    from routes.sia import _strip_m1_meta_preamble
    obs_text = _strip_m1_meta_preamble(obs_text_raw, state.user_name)
    if obs_text != obs_text_raw:
        print(f"\nOBSERVATION 후처리 후:")
        print(f"  {obs_text}")

    combined = f"{opening} {obs_text}".strip()
    _divider("최종 opening_message (Sia 첫 메시지)")
    print(combined)

    # ── 체감 체크리스트
    _divider("체감 체크리스트")
    print("□ opening 이 한님 호명 포함?")
    print("□ obs_text 가 Vision 관찰 (벽돌/자연광/웜뮤트 등) 반영?")
    print("□ 친구 톤 (~더라구요 / ~가봐요?) 유지?")
    print("□ 마지막 문장 `?` 로 끝남 (M1 secondary=OBSERVATION QUESTION_REQUIRED)?")
    print("□ 분석 jargon (모드/포지셔닝 등) 없음?")
    print("□ 평가 표현 (예뻐요/멋집니다 등) 없음?")

    return 0


if __name__ == "__main__":
    sys.exit(main())
