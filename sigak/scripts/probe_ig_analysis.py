"""Live probe — IG Apify + Sonnet Vision 파이프라인 체감 검증 (D6 Phase A, Task 0).

실행 조건 (CRITICAL — 실 API 비용 발생):
  - env RUN_PROBE_LIVE=1
  - env APIFY_API_KEY
  - env ANTHROPIC_API_KEY
  - env IG_ENABLED=true (기본 false)
  - env PROBE_IG_HANDLE=<핸들> (예: doooo.ey)

비용 (2026-04 실측 가까운 추정):
  - Apify 10 results 호출: ~$0.027 (FREE tier)
  - Sonnet 4.6 Vision 1 call: ~$0.035
  - 총 ~$0.062 per probe

사용:
  RUN_PROBE_LIVE=1 APIFY_API_KEY=xxx ANTHROPIC_API_KEY=sk-ant-xxx \\
    IG_ENABLED=true PROBE_IG_HANDLE=xhan0_0 \\
    python scripts/probe_ig_analysis.py

출력:
  - fetch status (success/private/failed/skipped)
  - profile_basics 요약
  - latest_posts 카운트 + display_url 보존 수
  - IgFeedAnalysis JSON (분석 결과)
  - 체감 체크리스트 (tone_category / observed_adjectives 적절성)
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def _require_live() -> str:
    if os.environ.get("RUN_PROBE_LIVE") != "1":
        print("[skipped] RUN_PROBE_LIVE != 1. 실제 API 호출 없음.")
        print("실행: RUN_PROBE_LIVE=1 IG_ENABLED=true PROBE_IG_HANDLE=<handle> python scripts/probe_ig_analysis.py")
        sys.exit(0)

    handle = os.environ.get("PROBE_IG_HANDLE", "").strip()
    if not handle:
        print("[error] PROBE_IG_HANDLE 미설정")
        sys.exit(1)

    for k in ("APIFY_API_KEY", "ANTHROPIC_API_KEY"):
        if not os.environ.get(k):
            print(f"[error] {k} 미설정")
            sys.exit(1)

    return handle


def _print_divider(title: str) -> None:
    print()
    print("=" * 60)
    print(title)
    print("=" * 60)


def main() -> int:
    handle = _require_live()

    # 지연 임포트 — env 확인 후에만 모듈 로드
    from services import ig_scraper
    from schemas.user_profile import IgFeedCache

    _print_divider(f"1. Apify + Vision fetch — @{handle}")
    status, cache = ig_scraper.fetch_ig_profile(handle)
    print(f"status: {status}")

    if not isinstance(cache, IgFeedCache):
        print("[end] cache 없음. 종료.")
        return 0

    _print_divider("2. profile_basics")
    print(json.dumps(
        cache.profile_basics.model_dump(),
        ensure_ascii=False, indent=2,
    ))

    _print_divider("3. latest_posts display_url 보존 현황")
    posts = cache.latest_posts or []
    with_url = sum(1 for p in posts if p.display_url)
    print(f"총 {len(posts)}개 중 display_url 있음: {with_url}개")
    for i, p in enumerate(posts[:3], 1):
        url = (p.display_url or "")[:60] + ("…" if p.display_url and len(p.display_url) > 60 else "")
        print(f"  [{i}] ts={p.timestamp} caption={(p.caption or '')[:40]!r}")
        print(f"      display_url={url}")
        print(f"      comments={len(p.latest_comments or [])}")

    _print_divider("4. IgFeedAnalysis (Sonnet Vision 결과)")
    if cache.analysis is None:
        print("[warn] analysis = None (Vision 실패 or skip)")
        print("  가능 원인: 비공개 계정 / display_url 만료 / Sonnet API 오류")
        return 0

    analysis_dump = cache.analysis.model_dump()
    analysis_dump["analyzed_at"] = analysis_dump["analyzed_at"].isoformat()
    print(json.dumps(analysis_dump, ensure_ascii=False, indent=2))

    _print_divider("5. 체감 체크리스트")
    print("□ tone_category 가 피드 실제 톤과 일치하는가?")
    print("□ tone_percentage 숫자가 그럴듯한가 (극단치 100/0 아닌가)?")
    print("□ observed_adjectives 가 댓글 본문에서 실제 나올 법한 어휘인가?")
    print("□ mood_signal 이 정중체 1 문장인가?")
    print("□ three_month_shift 가 null 이면 일관됐다는 뜻 — 실제 일관된가?")

    _print_divider("6. refresh 정책 상태")
    print(f"last_analyzed_post_count: {cache.last_analyzed_post_count}")
    current = cache.profile_basics.post_count
    stale = ig_scraper.is_analysis_stale(cache, current_post_count=current)
    print(f"is_analysis_stale(current_post_count={current}) = {stale}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
