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

INTERVIEW_SYSTEM = """당신은 SIGAK 미감 좌표계의 해석 엔진입니다.
유저의 인터뷰 응답을 분석해서, 미감 좌표계의 4개 축 위에 '추구미 좌표'를 산출합니다.

4개 축:
1. structure (구조): -1 = 날카로운/앵귤러 ↔ +1 = 부드러운/라운드
2. impression (인상): -1 = 따뜻한/친근한 ↔ +1 = 쿨한/도도한
3. maturity (성숙도): -1 = 프레시/어린 ↔ +1 = 성숙한/시크한
4. intensity (강도): -1 = 자연스러운/내추럴 ↔ +1 = 볼드/강렬한

주요 셀럽 좌표 레퍼런스 (근사값):
- 수지: structure=0.4, impression=-0.2, maturity=-0.1, intensity=-0.3 (부드럽고 따뜻, 자연스러운)
- 제니: structure=-0.5, impression=0.6, maturity=0.3, intensity=0.5 (날카롭고 쿨, 볼드)
- 아이유: structure=0.2, impression=0.1, maturity=-0.3, intensity=-0.2 (약간 부드럽, 프레시)
- 한소희: structure=-0.3, impression=0.7, maturity=0.4, intensity=0.3 (쿨하고 성숙)
- 카리나: structure=-0.2, impression=0.4, maturity=-0.1, intensity=0.4 (쿨하고 볼드, 프레시)
- 원빈: structure=-0.6, impression=0.5, maturity=0.5, intensity=0.2 (날카롭고 쿨, 성숙)
- 차은우: structure=0.3, impression=0.3, maturity=-0.2, intensity=-0.1 (부드럽고 쿨, 프레시)
- 뉴진스(그룹): structure=0.1, impression=0.3, maturity=-0.5, intensity=0.2 (프레시하고 약간 쿨)

규칙:
- 레퍼런스 셀럽이 언급되면 해당 셀럽의 좌표를 기준점으로 사용
- 수식어("좀 더 성숙", "근데 좀 자연스럽게")는 해당 축에 오프셋 적용
- 불분명한 경우 0에 가까운 중립값 사용
- 반드시 JSON만 출력, 다른 텍스트 금지

출력 형식:
{
  "coordinates": {"structure": 0.1, "impression": 0.3, "maturity": -0.3, "intensity": 0.2},
  "reference_base": "뉴진스",
  "interpretation": "뉴진스의 프레시한 기반에 성숙도를 높인 방향",
  "confidence": 0.8
}"""


def interpret_interview(interview_data: dict) -> dict:
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

    raw = _call_llm(INTERVIEW_SYSTEM, user_prompt, max_tokens=512)

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
  "similar_celebs": [
    {"name": "셀럽명", "similarity": 0.85, "reason": "유사한 이유"}
  ],
  "trend_context": "현재 트렌드와의 관계 설명"
}"""


def generate_report(
    user_name: str,
    tier: str,
    face_features: dict,
    current_coords: dict,
    aspiration_coords: dict,
    gap: dict,
    interview_data: dict,
    aspiration_interpretation: dict,
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
- 눈 비율: {face_features.get('eye_width_ratio', 'N/A')}
- 눈 간격: {face_features.get('eye_spacing_ratio', 'N/A')}
- 코 길이 비율: {face_features.get('nose_length_ratio', 'N/A')}
- 입술 풍성도: {face_features.get('lip_fullness', 'N/A')}
- 이마 비율: {face_features.get('forehead_ratio', 'N/A')}
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
