"""Best Shot 엔진 — 300장 → A컷 30장 (Phase K4).

본인 확정 스펙:
  target_count = uploaded // 15
  max_count    = uploaded // 10
  1차 heuristic → max*3 까지 축소
  2차 Sonnet Vision 정밀 선별 (target 최소, max 최대)
  Sonnet 프롬프트: "억지로 상한 채우지 말 것"
  strength_score 에 따라 가중치 변화

Pipeline:
  1. R2 에서 uploaded bytes list 로드
  2. heuristic filter (best_shot_quality.filter_top_n)
  3. cost_monitor.check_and_reserve (Sonnet 1회 호출 예상 비용)
  4. Sonnet Vision 호출 — 이미지 list + profile + matched_trends 주입
  5. 선별된 사진을 best_shot/selected/ 로 이동 저장
  6. Sia 해석 (SiaWriter stub; Phase H 이후 Haiku)
  7. BestShotResult 반환
"""
from __future__ import annotations

import io
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

import anthropic

from config import get_settings
from schemas.best_shot import (
    BestShotResult,
    SelectedPhoto,
)
from schemas.knowledge import MatchedTrend
from schemas.user_taste import UserTasteProfile
from services import cost_monitor
from services import r2_client
from services.best_shot_quality import QualityResult, filter_top_n
from services.knowledge_matcher import match_trends_for_user
from services.sia_writer import get_sia_writer


logger = logging.getLogger(__name__)


# Sonnet 비용 추정 — 사진 30장 @ 이미지당 ~1k tokens + 출력 2k = ~32k input / 2k output
# Sonnet 4.6 pricing: input $3/1M, output $15/1M → 약 $0.13 per call (30장 기준).
# 비용 모니터링에는 약간 보수적으로 상향.
_ESTIMATED_USD_PER_CALL = 0.20


class BestShotEngineError(Exception):
    """엔진 복구 불가 오류. caller 는 session.status='failed' 처리 + refund."""


# ─────────────────────────────────────────────
#  Main entry
# ─────────────────────────────────────────────

def run_best_shot(
    *,
    user_id: str,
    session_id: str,
    uploaded_photo_keys: list[str],
    profile: UserTasteProfile,
    gender: Optional[str],
    user_name: Optional[str] = None,
    history_context: str = "",
) -> BestShotResult:
    """Best Shot 선별 파이프라인 (heuristic → Sonnet).

    uploaded_photo_keys: R2 key list (best_shot/uploads/{session}/{photo_id})
    profile:             UserTasteProfile (strength_score 등 가중치 기준)
    gender:              KB 매칭 용

    Raises:
      BestShotEngineError — 복구 불가 (refund 대상)
      cost_monitor.CostLimitExceeded — 일일 cap 초과 (caller 가 refund + 재시도 방지)
    """
    uploaded_count = len(uploaded_photo_keys)
    if uploaded_count < 50:
        raise BestShotEngineError(f"too few uploaded ({uploaded_count} < 50)")

    target_count = uploaded_count // 15
    max_count = uploaded_count // 10
    if target_count < 1 or max_count < 1:
        raise BestShotEngineError("target/max count zero — abort")

    # 1. bytes 로드
    photos: list[tuple[str, bytes]] = []
    for key in uploaded_photo_keys:
        try:
            photo_id = key.rsplit("/", 1)[-1]
            photos.append((photo_id, r2_client.get_bytes(key)))
        except Exception as e:
            logger.warning("skip photo on load: key=%s err=%s", key, e)
            continue
    if len(photos) < 50:
        raise BestShotEngineError(
            f"load failures left only {len(photos)} photos (min 50)",
        )

    # 2. heuristic 1차 축소 (max_count * 3)
    settings = get_settings()
    heuristic_cutoff = settings.best_shot_quality_cutoff
    heuristic_limit = max(max_count * 3, target_count)
    heuristic_survived = filter_top_n(
        photos, max_count=heuristic_limit, cutoff=heuristic_cutoff,
    )
    if not heuristic_survived:
        raise BestShotEngineError(
            "heuristic filter removed all photos (quality cutoff too high?)",
        )

    # 3. cost_monitor 예약
    cost_monitor.check_and_reserve(
        resource="best_shot_sonnet",
        estimated_cost_usd=_ESTIMATED_USD_PER_CALL,
    )

    # 4. KB 매칭 — gender 제공 시만
    matched_trends: list[MatchedTrend] = []
    if gender in ("female", "male"):
        matched_trends = match_trends_for_user(
            profile, gender=gender, season=None, limit=5,  # type: ignore[arg-type]
        )

    # 5. Sonnet Vision 호출 + 파싱
    strength = float(profile.strength_score or 0.0)
    selection_plan = _call_sonnet_select(
        candidates=heuristic_survived,
        target_count=target_count,
        max_count=max_count,
        profile=profile,
        matched_trends=matched_trends,
        strength_score=strength,
        history_context=history_context,
    )

    # 6. 선별 사진 R2 selected/ 로 복사 이동 + 결과 조립
    selected_photos: list[SelectedPhoto] = _materialize_selection(
        user_id=user_id,
        session_id=session_id,
        selection_plan=selection_plan,
        heuristic_survived=heuristic_survived,
        matched_trends=matched_trends,
        profile=profile,
        user_name=user_name,
    )

    writer = get_sia_writer()
    overall = writer.generate_overall_message(
        profile=profile,
        context={
            "product": "best_shot",
            "selected_count": len(selected_photos),
            "uploaded_count": uploaded_count,
        },
        user_name=user_name,
    )

    return BestShotResult(
        selected_photos=selected_photos,
        sia_overall_message=overall,
        matched_trend_ids=[m.trend.trend_id for m in matched_trends],
        heuristic_survived_count=len(heuristic_survived),
        heuristic_cutoff=heuristic_cutoff,
        sonnet_selected_count=len(selected_photos),
        target_count=target_count,
        max_count=max_count,
    )


# ─────────────────────────────────────────────
#  Sonnet call
# ─────────────────────────────────────────────

_SELECTION_SYSTEM_PROMPT = """당신은 SIGAK 의 Best Shot 선별 엔진입니다.

역할:
  유저가 올린 여러 장의 사진 중 "정세현님답다" 혹은 "정세현님의 추구미에 가까운"
  사진을 target~max 장 범위에서 선별합니다. 상한을 억지로 채우지 마십시오.
  품질 기준이 애매하면 적게 뽑고 넘깁니다.

판단 기준:
  - 유저 profile (current_position / aspiration_vector / user_original_phrases)
  - matched_trends (시즌 KB 호환 가능 방향)
  - strength_score 낮으면 (< 0.3) 가중치: 품질 > 매칭. 데이터 적을 때 과잉 해석 금지.
  - strength_score 높으면: 취향 적합도 가중치 상승.

출력 형식 (엄격 JSON):
{
  "selections": [
    {
      "rank": 1,
      "photo_index": 3,
      "profile_match_score": 0.85,
      "trend_match_score": 0.70,
      "associated_trend_id": "female_2026_spring_002" or null,
      "rationale": "1-2 문장 페르소나 B 톤"
    }
    // target ~ max 개
  ]
}

Hard Rules:
  - selections 개수는 {target} ~ {max} 범위. 넘어가지 말 것.
  - rationale 은 확정/단정 X, 서술형. "결", "무드" 같은 추상명사 금지.
  - JSON 외 텍스트 금지.
"""


def _call_sonnet_select(
    *,
    candidates: list[tuple[str, bytes, QualityResult]],
    target_count: int,
    max_count: int,
    profile: UserTasteProfile,
    matched_trends: list[MatchedTrend],
    strength_score: float,
    history_context: str = "",
) -> list[dict]:
    """Sonnet Vision 호출 → selections dict list.

    candidates 에서 image block 생성해 전달. candidate index 는 0-based.
    """
    settings = get_settings()
    if not settings.anthropic_api_key:
        raise BestShotEngineError("ANTHROPIC_API_KEY not configured")

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    image_blocks: list[dict] = []
    for idx, (_, data, qr) in enumerate(candidates):
        import base64
        b64 = base64.b64encode(data).decode("ascii")
        image_blocks.append({
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": "image/jpeg",
                "data": b64,
            },
        })

    profile_dump = {
        "current_position": (
            profile.current_position.model_dump(mode="json")
            if profile.current_position else None
        ),
        "aspiration_vector": (
            profile.aspiration_vector.model_dump(mode="json")
            if profile.aspiration_vector else None
        ),
        "user_original_phrases": profile.user_original_phrases,
        "strength_score": strength_score,
    }
    trends_dump = [
        {
            "trend_id": m.trend.trend_id,
            "title": m.trend.title,
            "score": m.score,
        }
        for m in matched_trends
    ]

    # Phase I — Backward echo: latest_pi.top_hair_name 우회 inject
    # 상품명 직접 호명 금지 — "지난번 정밀 분석" 표현. None / 빈 latest_pi → "" (회귀 0).
    pi_hair_block = ""
    latest_pi = getattr(profile, "latest_pi", None)
    if latest_pi is not None:
        top_hair = getattr(latest_pi, "top_hair_name", None)
        if top_hair:
            pi_hair_block = (
                "[본질 분석 — 선호 헤어 힌트]\n"
                f"  지난번 정밀 분석 추천 헤어: {top_hair}\n"
                "  → 정합 사진 우선 (강제 X, 자연스러운 가이드).\n\n"
            )

    text_prompt = (
        f"사진 {len(candidates)} 장 중 {target_count}~{max_count} 장 선별.\n\n"
        f"[profile]\n{json.dumps(profile_dump, ensure_ascii=False, indent=2)}\n\n"
        + pi_hair_block
        + f"[matched_trends]\n{json.dumps(trends_dump, ensure_ascii=False, indent=2)}\n\n"
        "photo_index 는 위 이미지 순서 0-based. target~max 범위 엄수.\n"
        "정말 좋은 사진만. 억지로 상한 채우지 말 것."
    )
    # STEP 5i — 이전 Sia/추구미 맥락 주입 (cross-session 연결성)
    if history_context:
        text_prompt = history_context + "---\n\n" + text_prompt

    user_content = image_blocks + [{"type": "text", "text": text_prompt}]

    response = client.messages.create(
        model=settings.anthropic_model_sonnet,
        max_tokens=2000,
        system=_SELECTION_SYSTEM_PROMPT.format(target=target_count, max=max_count),
        messages=[{"role": "user", "content": user_content}],
    )
    if not response.content:
        raise BestShotEngineError("empty Sonnet response")
    text_blocks = [b.text for b in response.content if b.type == "text"]
    raw = "\n".join(text_blocks).strip()

    # fence 제거
    raw = _strip_fence(raw)
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as e:
        raise BestShotEngineError(f"Sonnet response not valid JSON: {e}")

    selections = parsed.get("selections") if isinstance(parsed, dict) else None
    if not isinstance(selections, list) or not selections:
        raise BestShotEngineError("selections empty or malformed")

    # 범위 검증 + clamp (Sonnet 가 넘겼으면 앞 max_count 만)
    if len(selections) > max_count:
        selections = selections[:max_count]
    return selections


def _strip_fence(text: str) -> str:
    t = text.strip()
    if t.startswith("```"):
        lines = t.split("\n")
        if len(lines) > 1:
            lines = lines[1:]
        while lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        t = "\n".join(lines).strip()
    return t


# ─────────────────────────────────────────────
#  Materialize — R2 복사 + SelectedPhoto 조립
# ─────────────────────────────────────────────

def _materialize_selection(
    *,
    user_id: str,
    session_id: str,
    selection_plan: list[dict],
    heuristic_survived: list[tuple[str, bytes, QualityResult]],
    matched_trends: list[MatchedTrend],
    profile: UserTasteProfile,
    user_name: Optional[str] = None,
) -> list[SelectedPhoto]:
    """Sonnet 선별 결과 → SelectedPhoto list + R2 이동.

    각 선별 사진:
      - best_shot/uploads/{session_id}/{photo_id} → best_shot/selected/{session_id}/{photo_id}
      - SiaWriter 으로 개별 comment 생성 (user_name 주입 + 다양성 전달)
    """
    writer = get_sia_writer()
    out: list[SelectedPhoto] = []
    sibling_comments: list[str] = []

    for entry in selection_plan:
        try:
            rank = int(entry.get("rank") or (len(out) + 1))
            idx = int(entry.get("photo_index"))
        except (TypeError, ValueError):
            continue
        if idx < 0 or idx >= len(heuristic_survived):
            continue
        photo_id, data, qr = heuristic_survived[idx]

        # R2 selected/ 로 복사
        from services.r2_client import best_shot_selected_key, put_bytes
        selected_key = best_shot_selected_key(user_id, session_id, photo_id)
        try:
            put_bytes(selected_key, data, content_type="image/jpeg")
        except Exception:
            logger.exception("put to selected failed: %s", selected_key)
            continue

        stored_url = (
            r2_client.public_url(selected_key)
            or f"r2://{selected_key}"   # 비공개 — 라우트가 presigned URL 으로 재발급
        )

        sia_comment = writer.generate_comment_for_photo(
            photo_url=stored_url,
            photo_context={
                "category": "best_shot_selected",
                "rank": rank,
                "rationale": entry.get("rationale"),
            },
            profile=profile,
            user_name=user_name,
            sibling_comments=list(sibling_comments),
        )
        sibling_comments.append(sia_comment)

        out.append(SelectedPhoto(
            photo_id=photo_id,
            stored_url=stored_url,
            rank=rank,
            quality_score=qr.quality_score,
            profile_match_score=float(entry.get("profile_match_score") or 0.5),
            trend_match_score=float(entry.get("trend_match_score") or 0.5),
            sia_comment=sia_comment,
            associated_trend_id=entry.get("associated_trend_id"),
        ))

    out.sort(key=lambda p: p.rank)
    return out


def generate_session_id() -> str:
    return f"bs_{uuid.uuid4().hex[:24]}"
