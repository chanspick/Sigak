"""Cover 어댑터 — Phase I PI-C.

vault user_phrases echo + IG taste 종합 → narrative 3-4 문장 (LLM 없이 템플릿).
Day 1 fallback: matched_type_name 만으로 generic narrative.
순수 함수 — LLM 호출 X, side effect X.
"""
from __future__ import annotations

from schemas.pi_report import CoverContent


def build_cover(
    vault_phrases: list[str],
    matched_type_name: str,
    ig_taste_summary: str,
) -> CoverContent:
    """vault echo + type + IG 종합 → CoverContent.

    Args:
        vault_phrases: 유저 발화 원어 모음. 비어있어도 OK.
        matched_type_name: PI-B 가 산출한 vault 매칭 type 한국어 이름.
        ig_taste_summary: IG 피드 분석 한 줄 요약. 비어있어도 OK.
    """
    safe_phrases = [p for p in (vault_phrases or []) if isinstance(p, str) and p.strip()]
    safe_type = (matched_type_name or "").strip()
    safe_ig = (ig_taste_summary or "").strip()

    key_phrases = safe_phrases[:3]

    if safe_type and safe_ig:
        headline = f"{safe_type}의 첫인상"
        narrative = (
            f"피드를 펼쳐보니 {safe_ig}. "
            f"전체 결은 {safe_type} 쪽으로 모이네요."
        )
        if key_phrases:
            phrase_str = " · ".join(f"\"{p}\"" for p in key_phrases)
            narrative += f" 본인 말로는 {phrase_str} 라는 결이 반복돼요."
        narrative += " 시각이 본 당신의 출발점입니다."
    elif safe_type:
        headline = f"{safe_type}의 첫인상"
        narrative = (
            f"분석 결과 {safe_type} 결이 도드라져요. "
            "더 많은 데이터가 쌓이면 결이 또렷해집니다."
        )
        if key_phrases:
            phrase_str = " · ".join(f"\"{p}\"" for p in key_phrases)
            narrative += f" 본인 말로는 {phrase_str} 라는 결이 잡혀요."
    else:
        # Day 1 fallback — 어떤 데이터도 없을 때
        headline = "시각이 본 당신"
        narrative = (
            "지금은 데이터가 갖춰지는 단계예요. "
            "Sia 와의 대화·피드 분석·추구미 분석을 한 단계씩 거치면 "
            "당신의 결이 점점 또렷해집니다."
        )
        if key_phrases:
            phrase_str = " · ".join(f"\"{p}\"" for p in key_phrases)
            narrative += f" 시작점은 {phrase_str}."

    return CoverContent(
        narrative=narrative,
        key_phrases=key_phrases,
        headline=headline,
    )
