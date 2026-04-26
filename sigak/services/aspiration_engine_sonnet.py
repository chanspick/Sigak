"""Aspiration v2 engine — Sonnet 4.6 cross-analysis (본인 사진 + 추구미 사진).

Verdict v2 (services/verdict_v2.py) 패턴 그대로 차용. 단일 Sonnet 호출에
풀 컨텍스트 (taste_profile + matched_trends + history_context + latest_pi +
user_analysis + target_analysis) 주입하고 JSON 출력으로 다음을 한 번에:

  hook_line / gap_narrative / photo_pair_comments[] / best_fit_pair_index /
  recommendation / sia_overall_message / numbers

기존 aspiration_engine_ig / aspiration_engine_pinterest 의 narrative 생성
부분 (compose_overall_message + select_photo_pairs 의 _empty_profile stub)
을 본 모듈로 교체. Apify 수집 / Vision / R2 저장 / vault append / 토큰
정책은 라우트 + engine_ig/pinterest 에 그대로 유지.

페르소나 B (친밀체 — Verdict 정중체와 분리). vault echo 강제 — Sia
대화 발화 / 본인 IG 분석 / 이전 추구미 / latest_pi 가 narrative 안에
직접 녹음. 트렌드 카드 출력 X — recommendation 안에 spirit 흡수
("숫자/출처 노출 없이 자연스러운 내러티브로 녹임").

CLAUDE.md §3.5 / §3.6 / §6.1 / §0 차별화 #2 ("쓸수록 정교") 정의 준수.
"""
from __future__ import annotations

import base64
import io
import json
import logging
from typing import Any, Optional, TypedDict

import anthropic
import httpx
from PIL import Image, ImageOps
from pydantic import ValidationError

from config import get_settings


logger = logging.getLogger(__name__)


class AspirationV2Error(Exception):
    """Aspiration v2 생성 재시도 후에도 실패."""


# ─────────────────────────────────────────────
#  Image downscale — 413 방어 (verdict_v2 동일)
# ─────────────────────────────────────────────

MAX_LONGEST_SIDE_PX = 1568
JPEG_QUALITY = 85


def downscale_image(data: bytes) -> tuple[bytes, str]:
    """원본 → (downscaled JPEG, "image/jpeg"). EXIF 정방향 + RGB + LANCZOS."""
    try:
        img = Image.open(io.BytesIO(data))
        img = ImageOps.exif_transpose(img)
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")
        w, h = img.size
        longest = max(w, h)
        if longest > MAX_LONGEST_SIDE_PX:
            ratio = MAX_LONGEST_SIDE_PX / longest
            img = img.resize(
                (max(1, int(w * ratio)), max(1, int(h * ratio))),
                Image.Resampling.LANCZOS,
            )
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=JPEG_QUALITY, optimize=True)
        return buf.getvalue(), "image/jpeg"
    except Exception:
        logger.exception(
            "downscale_image failed (bytes=%d) — returning original", len(data),
        )
        return data, "image/jpeg"


# ─────────────────────────────────────────────
#  Photo input
# ─────────────────────────────────────────────

class PhotoInput(TypedDict, total=False):
    """업로드 사진 입력 형식 (verdict_v2.PhotoInput 동일).

    url 우선, 없으면 base64 + media_type. role = "user" | "target".
    index = 0-based 순번 (페어 매칭).
    """
    url: str
    base64: str
    media_type: str
    index: int
    role: str


# ─────────────────────────────────────────────
#  System Prompt (페르소나 B, Aspiration 전용)
# ─────────────────────────────────────────────

ASPIRATION_V2_SYSTEM_PROMPT = """당신은 SIGAK 의 추구미 분석 엔진입니다.
유저 본인의 IG 피드 사진과 유저가 추구하는 대상 (제3자 IG 핸들 또는 Pinterest 보드)
의 사진을 같이 보고, **본인 vs 추구미** 결의 차이와 이동 방향을 짚어줍니다.

[역할]
- 분석가이자 친근 비서. 유저가 "어떻게 알았지" 라고 느낄 만큼 vault 데이터
  (Sia 대화 / 본인 IG 분석 / 이전 추구미 분석 / latest_pi) 를 narrative
  안에 직접 녹입니다.
- 사진만 보고 단편적으로 묘사하지 않습니다. 두 set (본인 / 추구미) 을
  cross-analysis 해서 결의 거리와 이동 방향을 한 번에 짚어야 합니다.

[페르소나 B — 친밀체 (Verdict 정중체와 분리)]
- 허용 어미: ~더라구요 / ~이시잖아요 / ~이신 것 같은데 / ~인가봐요? / ~으시죠? / ~이세요
- 금지 어미: ~네요 / ~군요 / ~같아요 / ~같습니다 / ~것 같 / ~합니다 (Verdict 정중체) / ~수 있습니다
- 호명: user_name 1-2회. 이름 다음 ',' 뒤 문장 시작 X.

[Hard Rules — 위반 시 응답 무효, 재시도 트리거]
HR1. "Verdict" / "verdict" / "판정" 단어 X
HR2. 마크다운 X (`**bold**`, `##`, `>`, ``` 전부)
HR3. 리스트 불릿 X (UI 자체 처리)
HR4. 이모지 X
HR5. 평가어 X ("좋아 보입니다", "잘 어울립니다", "멋집니다")
HR6. 추상 칭찬 X ("매력적", "독특한", "특별한", "흥미로운", "인상적", "센스 있", "안목", "감각이 있")
HR7. 영업 어휘 X ("리포트로", "구독", "추천해드릴", "정리해드릴", 가격 수치 전부)
HR8. 확인 요청 X ("본인도 그렇게 생각하세요?", "맞으신가요?")
HR9. 시적 비유 X ("봄바람 같은", "햇살처럼")
HR10. 내부 좌표 영문 / 정성 라벨 X (shape / volume / age / 소프트 / 샤프 / 프레시 / 성숙)
      → "윤곽" / "분위기" / "어른스러운" / "산뜻한" 같은 일상 형용사로 풀어쓰기
HR11. 트렌드 메타 X (`[score: ...]`, 미디어 인용 라벨, trend_id, 화살표 ↘ ▲)

[vault echo 강제 — narrative 차별화 핵심]
다음을 가능한 한 모두 narrative 안에 자연스럽게 녹이세요. 일반적인 사진 묘사
("이분 블루 자켓 잘 떨어지네요", "골목 분위기가 살아있네요") 가 아니라,
**유저 본인의 누적 데이터를 짚어주는** narrative 가 되어야 합니다.

  1. taste_profile.user_original_phrases — 첫 1개를 gap_narrative 첫 문장에
     reframe 해서 인용 ("샤프함과 빈티지 자유로움 사이라고 하셨잖아요" 류).
  2. user_analysis_snapshot (본인 IG 분석) 의 tone_category / mood / pose_frequency
     를 추구미 쪽 동일 필드와 같은 문장에서 비교 ("본인 피드는 정돈된 도시 톤,
     추구미 쪽은 빈티지 골목 톤").
  3. taste_profile.aspiration_history_recent 가 있으면 carry ("지난번엔 X 결을
     추구하셨는데 이번엔 Y 쪽으로 한 칸 더").
  4. taste_profile.latest_pi.top_action_text 가 있으면 우회 표현으로 echo
     ("전에 짚어드린 이동과 결을 같이 가는 방향이세요").
  5. taste_profile.strength_score 가 0.6 미만이면 sia_overall_message 끝에
     "조금 더 쓰시면 더 정확해져요" 자연 hint.

[matched_trends — 카테고리 다양성 흡수 강제]
matched_trends 는 KB 매칭 결과 list. **반드시 다양한 카테고리 (mood /
silhouette / color_palette / styling_method) 의 spirit 을 recommendation 안에
흡수**. 같은 카테고리 (예: 헤어) 만 반복해서 언급하면 응답 무효.
trend_id / score / 카테고리 라벨 출력 X — narrative 안에 자연스럽게 녹임.

[입력 구조]
- user_photos: 본인 IG 사진 N장 (1~5)
- target_photos: 추구미 사진 N장 (1~5). 순서가 user_photos 와 1:1 페어 매칭.
- target_display_name: "@yuni" / Pinterest 보드 이름 등
- target_type: "ig" | "pinterest"
- user_analysis_snapshot: 본인 IgFeedAnalysis dump (tone/mood/pose/consistency)
- target_analysis_snapshot: 추구미 IgFeedAnalysis dump (동일 키)
- gap_vector: primary_axis / primary_delta / secondary_axis / tertiary_axis
- taste_profile: 5필드 + latest_pi (current_position / aspiration_vector /
  conversation_signals / user_original_phrases / strength_score)
- matched_trends: KB 매칭 list (다양한 카테고리)
- history_context: Sia 대화 / Best Shot / Aspiration / PI 이전 세션 markdown

[출력 구조 — 엄격 JSON]
{
  "hook_line": "30자 이내 한 줄 통찰. 본인 vs 추구미 결의 거리감 한 줄 요약.",
  "gap_narrative": "4-5 문장. user_original_phrases reframe 첫 문장 + 본인 피드 분석 신호 vs 추구미 분석 신호 비교 + 갭 축에서 어느 방향으로 한 칸인지 + (있으면) aspiration_history carry.",
  "photo_pair_comments": [
    "쌍 0 — 본인 사진 ↔ 추구미 사진 비교 한 줄 (60-100자). 단일 사진 묘사 X. 두 사진 같이 본 결의 차이.",
    "쌍 1 — ...",
    // user_photos 와 target_photos 의 min(N) 만큼
  ],
  "best_fit_pair_index": 0,  // 가장 의미있는 1쌍의 인덱스 (taste_profile 기준 strength 가장 큰 페어). 페어 0건이면 null.
  "recommendation": {
    "style_direction": "1-2 문장. 추구미 쪽으로 어떤 결의 이동인지. matched_trends 다양한 카테고리 spirit 흡수 (트렌드 라벨 직접 X).",
    "next_action": "1-2 문장. 한 걸음 행동 ('다음 피드에 X 한 컷 시도해보세요' 류).",
    "why": "1-2 문장. 왜 이 방향. 본인 결 + 갭 + 트렌드 spirit 통합 근거."
  },
  "sia_overall_message": "마무리 종합. 3-4 문장. 페르소나 B 친밀체. (strength_score < 0.6 이면) 끝에 '조금 더 쓰시면 더 정확해져요' 자연 hint.",
  "numbers": {
    "primary_axis": "shape | volume | age",  // 가장 큰 갭 축 (gap_vector.primary_axis)
    "primary_delta": -1.0~1.0,                 // gap_vector.primary_delta 그대로
    "alignment": "근접 | 보통 | 상충"          // 본인 vs 추구미 정합 정도
  }
}

[best_fit_pair_index 선정 규칙]
- photo_pair_comments 중 taste_profile.aspiration_vector 와 가장 부합하는
  쌍의 인덱스를 best_fit_pair_index 로 명시.
- 페어가 1쌍이면 0. 0쌍이면 null.
- UI 가 이 인덱스를 첫 노출 또는 강조에 활용.

[hook_line 작성 규칙]
✅ 허용: "본인 도시 톤 ↔ 추구미 빈티지 한 칸 차이"
✅ 허용: "분위기 축에서 한 칸, 다른 결은 거의 같습니다"
❌ 금지: "이쪽이 부족합니다" (평가어), "추구미가 더 좋네요" (비교 평가)

[gap_narrative 작성 규칙]
✅ 허용 첫 문장: "샤프함과 빈티지 자유로움 사이라고 하셨잖아요. 추구미 쪽 골목
   톤이 그 빈티지 결과 정확히 닿아있더라구요."
❌ 금지 첫 문장: "이분 피드는 깔끔한 톤입니다" (vault echo 0)

[photo_pair_comments 작성 규칙]
✅ 허용: "본인 쪽 정돈된 실내 컷, 추구미 쪽은 자연광 골목 — 분위기 결에서
   한 칸 차이가 또렷하게 보여요."
❌ 금지: "이분 블루 톤 재킷이 정말 깔끔하게 떨어지네요" (단일 사진 묘사)
❌ 금지: "이분 골목 가게의 차분한 분위기가 정말 살아있네요" (단일 사진 묘사)

[recommendation 작성 규칙]
- style_direction: "본인 결을 유지하면서 분위기 톤만 한 칸 빈티지 쪽으로
  당기시면 추구미와 자연스럽게 닿아요" 류
- next_action: "다음 피드에 자연광 골목 컷 한 장, 톤은 본인 쿨뮤트 그대로"
  류 — 구체 한 걸음
- why: "본인 결의 정돈됨 + 추구미 골목 분위기 + 2026 봄 이지 시크 무드가
  같은 결로 묶여요" 류 — matched_trends spirit 자연 흡수, 라벨 직접 X

[출력 형식]
- 반드시 유효한 JSON 1개만. 마크다운 wrapper / 주석 / 설명 텍스트 X.
- photo_pair_comments 길이는 입력 페어 수와 정확히 일치.
"""


# ─────────────────────────────────────────────
#  Anthropic Client (Sonnet 4.6, separate singleton)
# ─────────────────────────────────────────────

_client: Optional[anthropic.Anthropic] = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        settings = get_settings()
        if not settings.anthropic_api_key:
            raise RuntimeError("ANTHROPIC_API_KEY not configured")
        _client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    return _client


def reset_client() -> None:
    global _client
    _client = None


# ─────────────────────────────────────────────
#  Photo content block
# ─────────────────────────────────────────────

def _fetch_url_to_base64(
    url: str,
    *,
    timeout: float = 10.0,
) -> Optional[tuple[str, str]]:
    """URL → (base64_str, "image/jpeg"). 실패 시 None.

    IG / Pinterest CDN URL 을 Anthropic API "url" source 로 직접 넘기면
    robots.txt disallowed 로 400 거부. 백엔드에서 fetch + downscale +
    base64 변환 후 "base64" source 로 보내야 함 (verdict_v2 패턴 동일).

    downscale_image 재사용 — EXIF 정방향 + 1568px + JPEG q=85 + 413 방어.
    """
    try:
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            resp = client.get(url)
            resp.raise_for_status()
            ct = (
                resp.headers.get("content-type", "image/jpeg")
                .split(";")[0].strip().lower()
            )
            if not ct.startswith("image/"):
                ct = "image/jpeg"
            downscaled, ct_out = downscale_image(resp.content)
            data = base64.standard_b64encode(downscaled).decode("ascii")
            return data, ct_out
    except Exception:
        logger.warning(
            "aspiration v2 image fetch failed: %s", url[:80], exc_info=True,
        )
        return None


def _photo_to_content_block(photo: PhotoInput) -> Optional[dict]:
    """PhotoInput → Claude API image content block.

    base64 직접 주어지면 그대로. url 만 들어오면 fetch + base64 변환
    (IG / Pinterest CDN robots.txt 차단 회피).

    fetch 실패 시 None 반환 — caller 가 해당 사진 skip.
    """
    b64 = photo.get("base64")
    if b64:
        mt = photo.get("media_type", "image/jpeg")
        return {
            "type": "image",
            "source": {"type": "base64", "media_type": mt, "data": b64},
        }
    url = photo.get("url")
    if not url:
        raise ValueError("PhotoInput requires 'url' or 'base64'")

    fetched = _fetch_url_to_base64(url)
    if fetched is None:
        return None
    data, mt = fetched
    return {
        "type": "image",
        "source": {"type": "base64", "media_type": mt, "data": data},
    }


# ─────────────────────────────────────────────
#  Context renderers
# ─────────────────────────────────────────────

def _render_taste_profile(taste_profile: Optional[Any]) -> str:
    """UserTasteProfile snapshot → prompt JSON (Verdict 패턴 차용)."""
    if taste_profile is None:
        return "(taste_profile 없음 — gap_vector 만으로 narrative)"
    dump = (
        taste_profile.model_dump(mode="json")
        if hasattr(taste_profile, "model_dump")
        else taste_profile
    )
    slim = {
        "current_position": dump.get("current_position"),
        "aspiration_vector": dump.get("aspiration_vector"),
        "conversation_signals": dump.get("conversation_signals"),
        "user_original_phrases": dump.get("user_original_phrases"),
        "strength_score": dump.get("strength_score"),
    }
    return json.dumps(slim, ensure_ascii=False, indent=2)


def _render_latest_pi(taste_profile: Optional[Any]) -> str:
    """taste_profile.latest_pi → 본질 좌표 + 닮은꼴 셀럽 우회 inject.

    Verdict v2 _render_latest_pi_for_verdict() 동일 패턴. 상품명 직접 호명
    금지 — "지난번 정밀 분석" 우회.
    """
    if taste_profile is None:
        return ""
    latest_pi = getattr(taste_profile, "latest_pi", None)
    if latest_pi is None:
        return ""

    lines: list[str] = []
    coord = getattr(latest_pi, "coord_3axis", None)
    if isinstance(coord, dict):
        try:
            lines.append(
                f"  본질 좌표: shape {float(coord.get('shape', 0.5)):.2f} / "
                f"volume {float(coord.get('volume', 0.5)):.2f} / "
                f"age {float(coord.get('age', 0.5)):.2f}"
            )
        except (TypeError, ValueError):
            pass
    top_celeb = getattr(latest_pi, "top_celeb_name", None)
    if top_celeb:
        sim = getattr(latest_pi, "top_celeb_similarity", None)
        if isinstance(sim, (int, float)):
            lines.append(
                f"  닮은꼴 셀럽: {top_celeb} (유사도 {float(sim):.2f})"
            )
        else:
            lines.append(f"  닮은꼴 셀럽: {top_celeb}")
    top_action = getattr(latest_pi, "top_action_text", None)
    if top_action:
        lines.append(f"  지난 액션 hint: {top_action}")

    if not lines:
        return ""

    return (
        "[본질 분석 — 지난번 정밀 분석 결과 (상품명 직접 호명 금지)]\n"
        + "\n".join(lines)
        + "\n\n"
    )


def _render_matched_trends(matched_trends: Optional[list]) -> str:
    """KB 매칭 list → prompt 텍스트. 카테고리 명시로 다양성 흡수 강제."""
    if not matched_trends:
        return "(KB 매칭 없음)"
    lines: list[str] = []
    for m in matched_trends[:5]:
        trend = m.trend if hasattr(m, "trend") else (
            m.get("trend") if isinstance(m, dict) else m
        )
        if trend is None:
            continue
        if hasattr(trend, "model_dump"):
            t_dump = trend.model_dump(mode="json")
        elif isinstance(trend, dict):
            t_dump = trend
        else:
            t_dump = {}
        title = t_dump.get("title") or "?"
        category = t_dump.get("category") or "?"
        action_hints = t_dump.get("action_hints") or []
        hints_str = " / ".join(str(h) for h in action_hints[:3]) or "-"
        score = (
            getattr(m, "score", None)
            if not isinstance(m, dict) else m.get("score", 0.0)
        )
        score_str = f"{float(score):.2f}" if score is not None else "0.00"
        lines.append(
            f"- [카테고리: {category}] {title} (score={score_str}) · "
            f"hints: {hints_str}"
        )
    return "\n".join(lines)


def _render_target_snapshot(snap: Optional[dict]) -> str:
    """IgFeedAnalysis dump → 핵심 필드만 prompt 요약."""
    if not snap:
        return "(분석 신호 없음)"
    parts: list[str] = []
    for key in (
        "tone_category", "mood", "color_palette",
        "style_consistency", "pose_frequency", "saturation_trend",
    ):
        v = snap.get(key)
        if v is None:
            continue
        if isinstance(v, float):
            parts.append(f"  {key}: {v:.2f}")
        else:
            parts.append(f"  {key}: {str(v)[:120]}")
    return "\n".join(parts) if parts else "(요약 가능 필드 없음)"


# ─────────────────────────────────────────────
#  Build user message
# ─────────────────────────────────────────────

def _build_user_message(
    *,
    user_photos: list[PhotoInput],
    target_photos: list[PhotoInput],
    user_name: Optional[str],
    target_display_name: str,
    target_type: str,
    user_analysis_snapshot: Optional[dict],
    target_analysis_snapshot: Optional[dict],
    gap_vector_dump: dict,
    taste_profile: Optional[Any],
    matched_trends: Optional[list],
    history_context: str,
) -> list[dict]:
    """Sonnet messages[0]["content"] 용 블록 리스트.

    구조:
      1. 본인 사진 N개 (label "본인 사진 i")
      2. 추구미 사진 N개 (label "추구미 사진 i")
      3. text block — 모든 컨텍스트 + 분석 instruction
    """
    blocks: list[dict] = []

    user_n_in = min(len(user_photos), 5)
    target_n_in = min(len(target_photos), 5)

    # 사진 블록 — fetch 실패 (CDN 만료 / robots.txt / 네트워크) 시 skip.
    # 라벨 텍스트로 cross 구분 명확화. 실제 첨부된 수만 라벨에 반영.
    user_blocks: list[dict] = []
    for i in range(user_n_in):
        pcopy: PhotoInput = dict(user_photos[i])  # type: ignore
        pcopy.setdefault("index", i)
        pcopy["role"] = "user"
        b = _photo_to_content_block(pcopy)
        if b is not None:
            user_blocks.append(b)

    target_blocks: list[dict] = []
    for i in range(target_n_in):
        pcopy = dict(target_photos[i])  # type: ignore
        pcopy.setdefault("index", i)
        pcopy["role"] = "target"
        b = _photo_to_content_block(pcopy)
        if b is not None:
            target_blocks.append(b)

    user_n = len(user_blocks)
    target_n = len(target_blocks)

    if user_n > 0:
        blocks.append({"type": "text", "text": f"[본인 사진 {user_n}장]"})
        blocks.extend(user_blocks)

    if target_n > 0:
        blocks.append({"type": "text", "text": f"[추구미 사진 {target_n}장]"})
        blocks.extend(target_blocks)

    if user_n == 0 and target_n == 0:
        # 모든 fetch 실패 — Sonnet 에 사진 0장 보내면 의미 X. caller 가
        # fallback 으로 가도록 명시 raise.
        raise AspirationV2Error(
            "all photo fetches failed (CDN expired / robots.txt / network)"
        )

    # 텍스트 컨텍스트
    pi_block = _render_latest_pi(taste_profile)
    user_summary = _render_target_snapshot(user_analysis_snapshot)
    target_summary = _render_target_snapshot(target_analysis_snapshot)

    pair_n = min(user_n, target_n)
    honor = (user_name or "이분").strip()
    if not honor.endswith("님") and honor != "이분":
        honor = f"{honor}님"

    text_body = (
        f"[유저 호명] {honor}\n"
        f"[추구미 대상] {target_display_name} ({target_type})\n"
        f"[페어 수] {pair_n}장 (사진 1:1 인덱스 매칭)\n\n"
        + pi_block
        + f"[taste_profile — 누적 취향 5필드]\n"
        f"{_render_taste_profile(taste_profile)}\n\n"
        f"[gap_vector]\n"
        f"  primary_axis: {gap_vector_dump.get('primary_axis')}\n"
        f"  primary_delta: {gap_vector_dump.get('primary_delta')}\n"
        f"  secondary_axis: {gap_vector_dump.get('secondary_axis')}\n"
        f"  secondary_delta: {gap_vector_dump.get('secondary_delta')}\n"
        f"  tertiary_axis: {gap_vector_dump.get('tertiary_axis')}\n"
        f"  tertiary_delta: {gap_vector_dump.get('tertiary_delta')}\n\n"
        f"[본인 IG 분석 신호 — narrative 도출 근거]\n"
        f"{user_summary}\n\n"
        f"[추구미 분석 신호 — narrative 도출 근거]\n"
        f"{target_summary}\n\n"
        f"[matched_trends — KB 매칭 (다양한 카테고리)]\n"
        f"{_render_matched_trends(matched_trends)}\n\n"
        f"위 정보로 본인 vs 추구미 cross-analysis 결과를 system prompt 의 "
        f"JSON 스키마로 출력. photo_pair_comments 는 페어 {pair_n}개 정확히. "
        f"vault echo 강제 5규칙 + 카테고리 다양성 흡수 + Hard Rules 11종 "
        f"엄수. 마크다운 wrapper / 주석 절대 X."
    )

    if history_context:
        text_body = history_context + "---\n\n" + text_body

    blocks.append({"type": "text", "text": text_body})
    return blocks


# ─────────────────────────────────────────────
#  Sonnet call
# ─────────────────────────────────────────────

def _call_sonnet(
    *,
    user_photos: list[PhotoInput],
    target_photos: list[PhotoInput],
    user_name: Optional[str],
    target_display_name: str,
    target_type: str,
    user_analysis_snapshot: Optional[dict],
    target_analysis_snapshot: Optional[dict],
    gap_vector_dump: dict,
    taste_profile: Optional[Any],
    matched_trends: Optional[list],
    history_context: str,
    max_tokens: int = 3500,
) -> str:
    settings = get_settings()
    client = _get_client()

    content_blocks = _build_user_message(
        user_photos=user_photos,
        target_photos=target_photos,
        user_name=user_name,
        target_display_name=target_display_name,
        target_type=target_type,
        user_analysis_snapshot=user_analysis_snapshot,
        target_analysis_snapshot=target_analysis_snapshot,
        gap_vector_dump=gap_vector_dump,
        taste_profile=taste_profile,
        matched_trends=matched_trends,
        history_context=history_context,
    )

    response = client.messages.create(
        model=settings.anthropic_model_sonnet,
        max_tokens=max_tokens,
        system=ASPIRATION_V2_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": content_blocks}],
    )
    if not response.content:
        raise AspirationV2Error("empty Sonnet response")
    text_blocks = [b.text for b in response.content if b.type == "text"]
    if not text_blocks:
        raise AspirationV2Error("no text block in Sonnet response")
    return "\n".join(text_blocks).strip()


# ─────────────────────────────────────────────
#  Post-processing
# ─────────────────────────────────────────────

def _strip_json_fence(text: str) -> str:
    t = text.strip()
    if t.startswith("```"):
        lines = t.split("\n")
        if len(lines) > 1:
            lines = lines[1:]
        while lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        t = "\n".join(lines).strip()
    return t


# Hard Rules 검증 — false positive 최소화 (한국어 일상 단어 제외).
# Verdict v2 의 sia_validators 패턴 차용하되, 페르소나 B narrative 안에
# 자연스럽게 들어가는 한국어 형용사 (샤프 / 프레시 / 성숙 / 소프트 등) 는
# 검증 대상에서 제외. 좌표 영문 raw + 명백한 메타 / 영업 / 마크다운만 차단.

_BANNED_VERDICT_WORDS = ("verdict", "Verdict", "VERDICT", "판정")
_BANNED_PRAISE = (
    "매력적", "센스 있", "안목 있", "감각이 있",
    # "독특한" / "특별한" / "흥미로운" / "인상적" 은 narrative 자연 등장 — 제외
)
_BANNED_COMMERCE = (
    "리포트로", "구독해", "추천해드릴", "정리해드릴",
    # "프리미엄" / "티어" 는 추구미 narrative 자연 등장 가능성 0 이지만
    # false positive 위험 낮아 유지 X (제외)
)
_BANNED_AXIS_RAW = (
    "shape ", "shape축", "volume ", "volume축", "age ", "age축",
    # 영문 좌표 raw 만. "shape" 자체는 일반 단어 가능성 있어 공백/한글 suffix 동반만.
    # 한국어 정성 라벨 (샤프/프레시/성숙/소프트/베이비/매추어) 은 narrative
    # 자연 등장 — 검증 X.
)
_BANNED_TREND_META = ("[score:", "[mood / trend_score", "trend_id=", "🔥")
_BANNED_MARKDOWN = ("**", "## ", "```", "* * *")


def _collect_user_facing_text(parsed: dict) -> str:
    """JSON 안 user-facing 텍스트 전량 합체."""
    parts: list[str] = []
    parts.append(str(parsed.get("hook_line") or ""))
    parts.append(str(parsed.get("gap_narrative") or ""))
    parts.append(str(parsed.get("sia_overall_message") or ""))
    pair_comments = parsed.get("photo_pair_comments") or []
    if isinstance(pair_comments, list):
        parts.extend(str(c) for c in pair_comments if c)
    rec = parsed.get("recommendation") or {}
    if isinstance(rec, dict):
        parts.append(str(rec.get("style_direction") or ""))
        parts.append(str(rec.get("next_action") or ""))
        parts.append(str(rec.get("why") or ""))
    return "\n".join(p for p in parts if p)


def _validate_hard_rules(parsed: dict) -> None:
    """Hard Rules 검증. 위반 시 AspirationV2Error.

    완화 정책 (false positive 최소화):
      - 한국어 일상 단어 (샤프 / 프레시 / 성숙 / 소프트) 는 검증 X
      - 영문 좌표 raw 는 공백/축 suffix 동반만 차단
      - 명백한 메타 / 영업 / 마크다운만 hard reject
    """
    text = _collect_user_facing_text(parsed)
    if not text:
        raise AspirationV2Error("empty user-facing output")

    bad: list[str] = []

    for w in _BANNED_VERDICT_WORDS:
        if w in text:
            bad.append(f"verdict word: {w!r}")
            break

    for w in _BANNED_PRAISE:
        if w in text:
            bad.append(f"praise: {w!r}")
            break

    for w in _BANNED_COMMERCE:
        if w in text:
            bad.append(f"commerce: {w!r}")
            break

    for w in _BANNED_AXIS_RAW:
        if w in text:
            bad.append(f"axis raw: {w!r}")
            break

    for w in _BANNED_TREND_META:
        if w in text:
            bad.append(f"trend meta: {w!r}")
            break

    for w in _BANNED_MARKDOWN:
        if w in text:
            bad.append(f"markdown: {w!r}")
            break

    if bad:
        raise AspirationV2Error(f"Hard Rules 위반: {'; '.join(bad)}")


# ─────────────────────────────────────────────
#  Public API
# ─────────────────────────────────────────────

def compose_aspiration_v2(
    *,
    user_id: str,
    user_name: Optional[str],
    user_photos: list[PhotoInput],
    target_photos: list[PhotoInput],
    target_display_name: str,
    target_type: str,
    gap_vector_dump: dict,
    user_analysis_snapshot: Optional[dict] = None,
    target_analysis_snapshot: Optional[dict] = None,
    taste_profile: Optional[Any] = None,
    matched_trends: Optional[list] = None,
    history_context: str = "",
    max_retries: int = 2,
) -> dict:
    """단일 Sonnet 4.6 cross-analysis. JSON dict 반환.

    Args:
      user_id: 본인 user id (로그용)
      user_name: 호명용 (None 이면 "이분")
      user_photos: 본인 사진 PhotoInput list (1~5)
      target_photos: 추구미 사진 PhotoInput list (1~5). user_photos 와 1:1
        인덱스 페어 매칭.
      target_display_name: "@yuni" 또는 Pinterest 보드 이름
      target_type: "ig" | "pinterest"
      gap_vector_dump: GapVector.model_dump() 결과
      user_analysis_snapshot: 본인 IgFeedAnalysis dump
      target_analysis_snapshot: 추구미 IgFeedAnalysis dump
      taste_profile: UserTasteProfile snapshot (5필드 + latest_pi)
      matched_trends: KB 매칭 list (다양한 카테고리)
      history_context: history_injector.build_history_context() 결과
      max_retries: API/parse/HardRules 실패 시 재시도 (default 1)

    Returns:
      dict — system prompt JSON 스키마 그대로 + raw_sonnet_response 추가:
        {
          "hook_line": str,
          "gap_narrative": str,
          "photo_pair_comments": list[str],
          "best_fit_pair_index": Optional[int],
          "recommendation": {"style_direction": str, "next_action": str, "why": str},
          "sia_overall_message": str,
          "numbers": {"primary_axis": str, "primary_delta": float, "alignment": str},
          "raw_sonnet_response": str,   # 휘발 방지
        }

    Raises:
      AspirationV2Error: API 실패 / parse 실패 / Hard Rules 위반 (재시도 후).
    """
    if not user_photos and not target_photos:
        raise ValueError("at least one of user_photos / target_photos required")

    last_error: Optional[Exception] = None
    last_raw = ""

    for attempt in range(max_retries + 1):
        try:
            raw = _call_sonnet(
                user_photos=user_photos,
                target_photos=target_photos,
                user_name=user_name,
                target_display_name=target_display_name,
                target_type=target_type,
                user_analysis_snapshot=user_analysis_snapshot,
                target_analysis_snapshot=target_analysis_snapshot,
                gap_vector_dump=gap_vector_dump,
                taste_profile=taste_profile,
                matched_trends=matched_trends,
                history_context=history_context,
            )
            last_raw = raw
            clean = _strip_json_fence(raw)
            parsed = json.loads(clean)
            if not isinstance(parsed, dict):
                raise AspirationV2Error("response not dict")

            _validate_hard_rules(parsed)

            # photo_pair_comments 길이 페어 수와 일치 보장
            pair_n = min(len(user_photos), len(target_photos))
            comments = parsed.get("photo_pair_comments") or []
            if not isinstance(comments, list):
                comments = []
            # 부족하면 빈 string 채움, 초과는 잘라냄 (UI 안정성)
            if len(comments) < pair_n:
                comments = list(comments) + [""] * (pair_n - len(comments))
            elif len(comments) > pair_n:
                comments = comments[:pair_n]
            parsed["photo_pair_comments"] = [str(c) for c in comments]

            # best_fit_pair_index 범위 검증
            bfi = parsed.get("best_fit_pair_index")
            if not (isinstance(bfi, int) and 0 <= bfi < pair_n):
                parsed["best_fit_pair_index"] = None

            parsed["raw_sonnet_response"] = raw

            logger.info(
                "aspiration v2 success: user=%s attempt=%d pairs=%d best_fit=%s",
                user_id, attempt + 1, pair_n, parsed.get("best_fit_pair_index"),
            )
            return parsed

        except (json.JSONDecodeError, ValidationError) as e:
            last_error = e
            logger.warning(
                "aspiration v2 parse failed (attempt %d): %s", attempt + 1, e,
            )
            continue
        except AspirationV2Error as e:
            last_error = e
            logger.warning(
                "aspiration v2 hard rules failed (attempt %d): %s",
                attempt + 1, e,
            )
            continue
        except anthropic.APIError as e:
            last_error = e
            logger.warning(
                "aspiration v2 API error (attempt %d): %s", attempt + 1, e,
            )
            continue

    # 재시도 다 실패 — fallback dict (engine 이 호출자에게 결과 보장).
    # raw 응답 일부 + last_error 같이 로깅 — Railway logs 에서 디버그 가능.
    logger.error(
        "aspiration v2 ALL retries failed user=%s err=%r last_raw_head=%r",
        user_id,
        last_error,
        last_raw[:600] if last_raw else "(empty)",
    )
    raise AspirationV2Error(
        f"aspiration v2 failed after {max_retries + 1} attempts: {last_error}"
    )


def build_aspiration_v2_fallback(
    *,
    user_name: Optional[str],
    target_display_name: str,
    gap_vector_dump: dict,
    pair_n: int,
) -> dict:
    """Sonnet 다 실패 시 deterministic fallback. Hard Rules 통과 형태."""
    honor = (user_name or "이분").strip()
    if honor != "이분" and not honor.endswith("님"):
        honor = f"{honor}님"
    primary = gap_vector_dump.get("primary_axis", "")
    return {
        "hook_line": "본인 결과 추구미 결의 거리를 같이 봤어요",
        "gap_narrative": (
            f"{honor} 본인 피드와 {target_display_name} 쪽 결을 같이 봤어요. "
            "지금 데이터로는 여기까지 또렷해요. "
            "조금씩 더 쓰시면 결이 더 잡히실 거예요."
        ),
        "photo_pair_comments": [
            "본인 쪽과 추구미 쪽 결을 같이 본 한 쌍이에요"
            for _ in range(pair_n)
        ],
        "best_fit_pair_index": 0 if pair_n > 0 else None,
        "recommendation": {
            "style_direction": "본인 결을 유지하면서 한 칸씩 추구미 쪽으로 닿는 방향이세요",
            "next_action": "다음 피드에 추구미 톤 한 컷 시도해보시는 거잖아요",
            "why": "본인 결과 추구미 결이 같은 결로 묶일 수 있어서요",
        },
        "sia_overall_message": (
            "지금 데이터로 짚어드린 거예요. 조금 더 쓰시면 더 정확해져요."
        ),
        "numbers": {
            "primary_axis": primary if primary in ("shape", "volume", "age") else "shape",
            "primary_delta": float(gap_vector_dump.get("primary_delta") or 0.0),
            "alignment": "보통",
        },
        "raw_sonnet_response": "",
    }
