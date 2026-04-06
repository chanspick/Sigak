"""
SIGAK LLM Pipeline — Interview Interpretation + Report Generation

Uses Claude API to:
1. Parse natural language aspirations → aspiration coordinates
2. Generate personalized PI report narrative
"""
import json
from typing import Optional
import anthropic

from config import get_settings
from pipeline.similarity import get_type_reference_prompt, load_anchors
from pipeline.face_comparison import format_comparison_for_report
from pipeline.cluster import format_cluster_for_report


# ─────────────────────────────────────────────
#  Client
# ─────────────────────────────────────────────

def _get_client():
    settings = get_settings()
    return anthropic.Anthropic(api_key=settings.anthropic_api_key)


def _call_llm(system: str, user: str, max_tokens: int = 2048) -> str:
    settings = get_settings()
    client = _get_client()
    response = client.messages.create(
        model=settings.llm_model,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    return response.content[0].text


# ─────────────────────────────────────────────
#  1. Interview Interpretation
#     "뉴진스 같은데 좀 더 성숙" → aspiration coordinates
# ─────────────────────────────────────────────

def _build_interview_system(gender: str = "female") -> str:
    """유형 앵커 데이터에서 동적으로 인터뷰 해석 프롬프트를 생성한다."""
    type_ref = get_type_reference_prompt(gender)
    return f"""당신은 SIGAK 미감 좌표계의 해석 엔진입니다.
유저의 인터뷰 응답을 분석해서, 미감 좌표계의 4개 축 위에 '추구미 좌표'를 산출합니다.

4개 축:
1. structure (구조): -1 = 날카로운/앵귤러 ↔ +1 = 부드러운/라운드
2. impression (인상): -1 = 따뜻한/친근한 ↔ +1 = 쿨한/도도한
3. maturity (성숙도): -1 = 프레시/어린 ↔ +1 = 성숙한/시크한
4. intensity (강도): -1 = 자연스러운/내추럴 ↔ +1 = 볼드/강렬한

SIGAK 인상 유형 레퍼런스:
{type_ref}

규칙:
- 유저가 특정 유형이나 키워드를 언급하면 해당 유형의 좌표를 기준점으로 사용
- 별명도 인식하세요 (예: "첫사랑" = 따뜻한 첫사랑, "시크" = 날카롭고 시크)
- 유저가 셀럽 이름을 언급하면, 해당 셀럽의 구조적 특성을 기반으로 가장 유사한 유형 좌표에 매핑
- 수식어("좀 더 성숙", "근데 좀 자연스럽게")는 해당 축에 오프셋 적용
- 불분명한 경우 0에 가까운 중립값 사용
- 반드시 JSON만 출력, 다른 텍스트 금지

출력 형식:
{{"coordinates": {{"structure": 0.1, "impression": 0.3, "maturity": -0.3, "intensity": 0.2}},
  "reference_base": "따뜻한 첫사랑",
  "interpretation": "따뜻한 첫사랑 기반에 성숙도를 높인 방향",
  "confidence": 0.8
}}"""


def interpret_interview(interview_data: dict, gender: str = "female") -> dict:
    """
    Parse interview responses into aspiration coordinates.

    interview_data: {
        "desired_image": "뉴진스 같은데 좀 더 성숙한 느낌",
        "reference_celebs": "카리나, 한소희",
        "style_keywords": "시크, 모던, 깔끔",
        "current_concerns": "너무 동안이라 진지해 보이고 싶다",
        ...
    }
    """
    user_prompt = f"""다음 인터뷰 응답에서 추구미 좌표를 산출해주세요.

[추구 이미지]
{interview_data.get('desired_image', '없음')}

[레퍼런스 셀럽]
{interview_data.get('reference_celebs', '없음')}

[스타일 키워드]
{interview_data.get('style_keywords', '없음')}

[현재 고민]
{interview_data.get('current_concerns', '없음')}

[자기 인식]
{interview_data.get('self_perception', '없음')}

JSON으로만 응답해주세요."""

    system_prompt = _build_interview_system(gender)
    raw = _call_llm(system_prompt, user_prompt, max_tokens=512)

    # Parse JSON response
    try:
        # Strip markdown code fence if present
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1].rsplit("```", 1)[0]
        result = json.loads(cleaned)
    except json.JSONDecodeError:
        # Fallback: return neutral coordinates
        result = {
            "coordinates": {"structure": 0, "impression": 0, "maturity": 0, "intensity": 0},
            "reference_base": "unknown",
            "interpretation": "파싱 실패 — 수동 보정 필요",
            "confidence": 0.0,
        }

    return result


# ─────────────────────────────────────────────
#  2. Report Generation
#     coordinates + gap + user context → full narrative report
# ─────────────────────────────────────────────

REPORT_SYSTEM = """당신은 SIGAK의 미감 리포트 라이터입니다.
유저의 얼굴 분석 데이터와 미감 좌표를 기반으로, 전문적이면서도 따뜻한 톤의 PI 리포트를 작성합니다.

리포트 톤:
- 판단이 아닌 분석. "못생겼다/예쁘다"가 아니라 "당신의 구조는 이러하고, 이 방향이 자연스럽다"
- 브랜드 톤: 미니멀, 에디토리얼, 따뜻한 전문성
- 비유보다 구체적 실행 방안 우선
- 존댓말(~합니다/~입니다)

반드시 아래 JSON 구조로만 출력하세요. 다른 텍스트 금지.

{
  "executive_summary": "2~3문장 핵심 요약",
  "sections": [
    {
      "id": "face_structure",
      "title": "얼굴 구조 분석",
      "content": "얼굴형, 비율, 대칭도 분석 서술",
      "key_findings": ["발견1", "발견2"]
    },
    {
      "id": "skin_analysis",
      "title": "피부톤 분석",
      "content": "피부톤 분류 + 컬러 매칭 방향",
      "key_findings": []
    },
    {
      "id": "current_position",
      "title": "미감 좌표 — 현재 위치",
      "content": "4축 좌표 해석. 각 축에서의 위치가 의미하는 바",
      "key_findings": []
    },
    {
      "id": "aspiration",
      "title": "미감 좌표 — 추구미",
      "content": "추구미 좌표 해석. 유저가 원하는 방향",
      "key_findings": []
    },
    {
      "id": "gap_analysis",
      "title": "갭 분석 — 실행 방향",
      "content": "현재→추구미 사이 갭의 의미와 전략적 방향",
      "key_findings": []
    },
    {
      "id": "action_plan",
      "title": "실행 가이드",
      "content": "구체적 실행 방안 종합",
      "key_findings": []
    }
  ],
  "action_items": [
    {"category": "메이크업", "recommendation": "구체적 조언", "priority": "high"},
    {"category": "헤어", "recommendation": "구체적 조언", "priority": "high"},
    {"category": "스타일링", "recommendation": "구체적 조언", "priority": "medium"},
    {"category": "컬러", "recommendation": "구체적 조언", "priority": "medium"}
  ],
  "similar_types": [
    {
      "name": "유형 라벨 (예: 따뜻한 첫사랑)",
      "type_id": 1,
      "similarity_pct": 82,
      "reason": "유사한 이유",
      "key_differences": ["턱선이 더 날카로움 → structure sharp", "눈매 올라감 → impression cool"],
      "styling_insight": "이 유형을 참고한 구체적 스타일링 한 줄"
    }
  ],
  "type_comparisons": [
    {
      "type_name": "유형 라벨",
      "similarities": ["유사한 특징 1~2개"],
      "differences": ["차이점 1~3개 (축 영향 포함)"],
      "direction_summary": "부드러운 인상을 베이스로, 날카로운 턱선을 살리는 방향"
    }
  ],
  "cluster_label": "쿨 갓데스",
  "cluster_description": "클러스터 특성 설명 + 대표 셀럽 + 유저 위치 해석",
  "trend_context": "현재 트렌드와의 관계 설명"
}

중요: similar_types, type_comparisons, cluster_label, cluster_description 필드는 반드시 포함하세요.
프롬프트에 CLIP/구조적 비교 데이터가 주어지면 그 수치를 기반으로, 없으면 좌표 분석을 기반으로 작성하세요.
셀럽 이름 대신 유형 라벨(예: "따뜻한 첫사랑", "날카롭고 시크")을 사용하세요."""


def _format_similar_types(similar_types: Optional[list[dict]]) -> str:
    """유형 유사도 결과를 LLM 프롬프트 삽입용 문자열로 포매팅."""
    if not similar_types:
        return "[유사 유형] 데이터 없음 — 분석 결과를 바탕으로 가장 유사한 유형을 추론해주세요."

    lines = ["[유사 유형 분석 (CLIP 임베딩 기반)]"]
    for i, c in enumerate(similar_types, 1):
        type_id = c.get("type_id", "?")
        mode = "CLIP 코사인" if c["mode"] == "clip" else "좌표 거리"
        lines.append(f"  {i}위: {c['name_kr']} (Type {type_id}) — 유사도 {c['similarity_pct']}% ({mode})")
        desc = c.get("description_kr", "")
        if desc:
            lines.append(f"     설명: {desc}")
        delta = c.get("axis_delta", {})
        diffs = []
        for ax, val in delta.items():
            if abs(val) >= 0.2:
                direction = "더 높음" if val > 0 else "더 낮음"
                diffs.append(f"{ax} {abs(val):.1f} {direction}")
        if diffs:
            lines.append(f"     축별 차이: {', '.join(diffs)}")
    lines.append("  → similar_types 필드에 위 결과를 반영해주세요.")
    return "\n".join(lines)


def generate_report(
    user_name: str,
    tier: str,
    face_features: dict,
    current_coords: dict,
    aspiration_coords: dict,
    gap: dict,
    interview_data: dict,
    aspiration_interpretation: dict,
    similar_celebs: Optional[list[dict]] = None,
    celeb_comparisons: Optional[list[dict]] = None,
    cluster_result: Optional[dict] = None,
) -> dict:
    """
    Generate the full PI report using Claude.

    Returns structured report JSON ready for template rendering.
    """
    user_prompt = f"""다음 데이터를 기반으로 {user_name}님의 PI 리포트를 작성해주세요.

[진단 티어] {tier}

[얼굴 구조 분석]
- 얼굴형: {face_features.get('face_shape', 'N/A')}
- 턱선 각도: {face_features.get('jaw_angle', 'N/A')}°
- 광대 돌출도: {face_features.get('cheekbone_prominence', 'N/A')}
- 눈 크기 비율: {face_features.get('eye_width_ratio', 'N/A')}
- 눈 가로세로비: {face_features.get('eye_ratio', 'N/A')}
- 눈꼬리 기울기: {face_features.get('eye_tilt', 'N/A')}° (+ 올라감 / - 처짐)
- 눈 간격: {face_features.get('eye_spacing_ratio', 'N/A')}
- 눈썹 아치: {face_features.get('brow_arch', 'N/A')}
- 코 길이 비율: {face_features.get('nose_length_ratio', 'N/A')}
- 코 높이: {face_features.get('nose_bridge_height', 'N/A')}
- 입술 풍성도: {face_features.get('lip_fullness', 'N/A')}
- 얼굴 종횡비: {face_features.get('face_length_ratio', 'N/A')}
- 이마 비율: {face_features.get('forehead_ratio', 'N/A')}
- 인중 비율: {face_features.get('philtrum_ratio', 'N/A')}
- 대칭도: {face_features.get('symmetry_score', 'N/A')}
- 황금비 근접도: {face_features.get('golden_ratio_score', 'N/A')}
- 피부톤: {face_features.get('skin_tone', 'N/A')}
- 피부 밝기: {face_features.get('skin_brightness', 'N/A')}

[미감 좌표 — 현재]
- 구조(날카로운↔부드러운): {current_coords.get('structure', 0):.2f}
- 인상(따뜻한↔쿨한): {current_coords.get('impression', 0):.2f}
- 성숙도(프레시↔성숙): {current_coords.get('maturity', 0):.2f}
- 강도(자연스러운↔볼드): {current_coords.get('intensity', 0):.2f}

[미감 좌표 — 추구미]
- 구조: {aspiration_coords.get('structure', 0):.2f}
- 인상: {aspiration_coords.get('impression', 0):.2f}
- 성숙도: {aspiration_coords.get('maturity', 0):.2f}
- 강도: {aspiration_coords.get('intensity', 0):.2f}
- 해석: {aspiration_interpretation.get('interpretation', '')}
- 레퍼런스 베이스: {aspiration_interpretation.get('reference_base', '')}

[갭 분석]
- 주요 이동 방향: {gap.get('primary_direction', '')} → {gap.get('primary_shift_kr', '')}
- 보조 이동 방향: {gap.get('secondary_direction', '')} → {gap.get('secondary_shift_kr', '')}
- 갭 크기: {gap.get('magnitude', 0):.2f}

[인터뷰 응답]
- 자기 인식: {interview_data.get('self_perception', 'N/A')}
- 추구미: {interview_data.get('desired_image', 'N/A')}
- 레퍼런스: {interview_data.get('reference_celebs', 'N/A')}
- 스타일 키워드: {interview_data.get('style_keywords', 'N/A')}
- 현재 고민: {interview_data.get('current_concerns', 'N/A')}
- 일상 루틴: {interview_data.get('daily_routine', 'N/A')}

{"[웨딩 정보] 컨셉: " + interview_data.get('wedding_concept', '') + ", 드레스: " + interview_data.get('dress_preference', '') if tier == 'wedding' else ''}
{"[크리에이터 정보] 콘텐츠: " + interview_data.get('content_style', '') + ", 타겟: " + interview_data.get('target_audience', '') if tier == 'creator' else ''}

{_format_similar_types(similar_celebs)}

{format_comparison_for_report(celeb_comparisons, tier=tier) if celeb_comparisons else ""}

{format_cluster_for_report(cluster_result, tier=tier) if cluster_result else ""}

JSON으로만 응답해주세요."""

    raw = _call_llm(REPORT_SYSTEM, user_prompt, max_tokens=4096)

    try:
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1].rsplit("```", 1)[0]
        report = json.loads(cleaned)
    except json.JSONDecodeError:
        report = {
            "executive_summary": "리포트 생성 중 오류가 발생했습니다. 수동 보정이 필요합니다.",
            "sections": [],
            "action_items": [],
            "similar_celebs": [],
            "trend_context": "",
        }

    return report


# ─────────────────────────────────────────────
#  3. Face Structure Interpretation
#     raw 수치 → 자연어 해석
# ─────────────────────────────────────────────

FACE_INTERPRET_SYSTEM = """당신은 SIGAK의 얼굴 구조 분석 전문가입니다.
MediaPipe 랜드마크에서 추출한 수치 데이터를 기반으로,
유저의 얼굴 구조 특징을 자연어로 해석합니다.

톤:
- 판단이 아닌 관찰. "예쁘다/못생겼다"가 아니라 "이러한 특징을 가지고 있다"
- 각 특징이 주는 인상을 설명 (예: "부드러운 턱라인은 친근하고 편안한 인상을 준다")
- 따뜻하고 전문적인 어조, 존댓말
- 전체적인 조화와 특징적인 포인트를 함께 언급

반드시 아래 JSON 구조로만 출력하세요. 다른 텍스트 금지.

{
  "overall_impression": "전체적인 인상을 2~3문장으로 요약",
  "feature_interpretations": [
    {
      "feature": "jaw_angle",
      "label": "턱선",
      "interpretation": "자연어 해석 1~2문장"
    }
  ],
  "harmony_note": "얼굴 전체 조화에 대한 1문장 코멘트",
  "distinctive_points": ["가장 특징적인 포인트 1~3개"]
}"""


def interpret_face_structure(face_features: dict) -> dict:
    """
    raw 얼굴 수치를 LLM으로 자연어 해석한다.

    Args:
        face_features: face.py에서 추출한 특징 dict
            jaw_angle, eye_tilt, cheekbone_prominence, lip_fullness,
            face_shape, symmetry_score, golden_ratio_score 등

    Returns:
        {
            "overall_impression": "...",
            "feature_interpretations": [...],
            "harmony_note": "...",
            "distinctive_points": [...]
        }
    """
    user_prompt = f"""다음 얼굴 구조 수치를 자연어로 해석해주세요.

[얼굴 구조 데이터]
- 얼굴형: {face_features.get('face_shape', 'N/A')}
- 턱선 각도: {face_features.get('jaw_angle', 'N/A')}° (낮을수록 날카로움, 높을수록 부드러움)
- 광대 돌출도: {face_features.get('cheekbone_prominence', 'N/A')} (0~1, 높을수록 돌출)
- 눈 크기 비율: {face_features.get('eye_width_ratio', 'N/A')} (눈 너비 / 얼굴 너비)
- 눈 가로세로비: {face_features.get('eye_ratio', 'N/A')} (높을수록 길쭉한 눈)
- 눈꼬리 기울기: {face_features.get('eye_tilt', 'N/A')}° (+ 올라감 / - 처짐)
- 눈 간격: {face_features.get('eye_spacing_ratio', 'N/A')}
- 눈썹 아치: {face_features.get('brow_arch', 'N/A')}
- 코 길이 비율: {face_features.get('nose_length_ratio', 'N/A')}
- 코 높이: {face_features.get('nose_bridge_height', 'N/A')}
- 입술 풍성도: {face_features.get('lip_fullness', 'N/A')} (0~1)
- 얼굴 종횡비: {face_features.get('face_length_ratio', 'N/A')}
- 이마 비율: {face_features.get('forehead_ratio', 'N/A')}
- 인중 비율: {face_features.get('philtrum_ratio', 'N/A')}
- 대칭도: {face_features.get('symmetry_score', 'N/A')} (0~1, 1=완벽)
- 황금비 근접도: {face_features.get('golden_ratio_score', 'N/A')} (0~1, 1=황금비)
- 피부톤: {face_features.get('skin_tone', 'N/A')}
- 피부 밝기: {face_features.get('skin_brightness', 'N/A')} (0~1)

JSON으로만 응답해주세요."""

    raw = _call_llm(FACE_INTERPRET_SYSTEM, user_prompt, max_tokens=1024)

    try:
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1].rsplit("```", 1)[0]
        result = json.loads(cleaned)
    except json.JSONDecodeError:
        result = {
            "overall_impression": "얼굴 구조 해석 중 오류가 발생했습니다.",
            "feature_interpretations": [],
            "harmony_note": "",
            "distinctive_points": [],
        }

    return result
