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
    import time
    settings = get_settings()
    client = _get_client()
    for attempt in range(2):
        try:
            response = client.messages.create(
                model=settings.llm_model,
                max_tokens=max_tokens,
                system=system,
                messages=[{"role": "user", "content": user}],
            )
            return response.content[0].text
        except Exception as e:
            err_type = type(e).__name__
            print(f"[LLM] attempt {attempt+1} failed: {err_type}: {e}")
            if attempt == 0 and ("rate" in str(e).lower() or "overloaded" in str(e).lower() or "529" in str(e)):
                time.sleep(2)
                continue
            raise


# ─────────────────────────────────────────────
#  1. Interview Interpretation
#     "뉴진스 같은데 좀 더 성숙" → aspiration coordinates
# ─────────────────────────────────────────────

def _build_interview_system(gender: str = "female") -> str:
    """유형 앵커 데이터에서 동적으로 인터뷰 해석 프롬프트를 생성한다."""
    type_ref = get_type_reference_prompt(gender)
    return f"""당신은 SIGAK 미감 좌표계의 해석 엔진입니다.
유저의 인터뷰 응답을 분석해서, 미감 좌표계의 3개 축 위에 '추구미 좌표'를 산출합니다.

3축 좌표계:
- shape [-1, +1]: Soft(둥글고 부드러운 골격) ↔ Sharp(날카롭고 선명한 골격)
- volume [-1, +1]: Subtle(작고 섬세한 이목구비) ↔ Bold(크고 존재감 있는 이목구비)
- age [-1, +1]: Fresh(어리고 생기있는 비율) ↔ Mature(성숙하고 정돈된 비율)

SIGAK 인상 유형 레퍼런스:
{type_ref}

규칙:
- 유저가 특정 유형이나 키워드를 언급하면 해당 유형의 좌표를 기준점으로 사용
- 별명도 인식하세요 (예: "첫사랑" = 따뜻한 첫사랑, "시크" = 날카롭고 시크)
- 유저가 특정 인물을 언급하면, 해당 인물의 구조적 특성을 기반으로 가장 유사한 유형 좌표에 매핑
- 수식어("좀 더 성숙", "근데 좀 자연스럽게")는 해당 축에 오프셋 적용
- 불분명한 경우 0에 가까운 중립값 사용
- 반드시 JSON만 출력, 다른 텍스트 금지

출력 형식:
{{"coordinates": {{"shape": 0.1, "volume": 0.3, "age": -0.3}},
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
    # 이미지 키워드: style_image_keywords(신규) 또는 style_keywords(레거시) 사용
    image_kw = interview_data.get('style_image_keywords') or interview_data.get('style_keywords', '없음')

    user_prompt = f"""다음 인터뷰 응답에서 추구미 좌표를 산출해주세요.

[추구 이미지]
{interview_data.get('desired_image', '없음')}

[레퍼런스]
{interview_data.get('reference_celebs', '없음')}

[이미지 키워드]
{image_kw}

[현재 고민]
{interview_data.get('current_concerns', '없음')}

[자기 인식]
{interview_data.get('self_perception', '없음')}

[얼굴 고민 영역]
{interview_data.get('face_concerns', '없음')}

[메이크업 레벨]
{interview_data.get('makeup_level', '없음')}

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
            "coordinates": {"shape": 0, "volume": 0, "age": 0},
            "reference_base": "unknown",
            "interpretation": "파싱 실패 — 수동 보정 필요",
            "confidence": 0.0,
        }

    return result


# ─────────────────────────────────────────────
#  2. Report Generation (v2 — Action Spec 기반)
#     Action Spec이 의사결정, Claude는 해설만 담당
# ─────────────────────────────────────────────

REPORT_SYSTEM_V2 = """역할: 당신은 스타일링 해설가입니다.
아래 이미 결정된 추천을 유저 친화적으로 설명하세요.

규칙:
- 추천 항목을 임의로 추가하거나 삭제하지 마세요
- action_tips는 recommended_actions의 순서를 그대로 유지하세요
- 축 점수나 delta 수치를 직접 언급하지 마세요
- "~할 수 있습니다", "~할 수 있어요", "~경향이 있다", "~편이에요" 등 유보적 표현 절대 금지
- 단정형으로 말하세요: "~해보세요", "~줍니다", "~어울려요"
- 부드럽게 하고 싶으면 유보 표현 대신 별도 문장으로 분리하세요
- 같은 내용을 다른 표현으로 반복하지 마세요
- 해요체를 사용하세요
- action_tips 각 항목의 zone 필드는 입력값을 그대로 복사하세요 (번역/의역 금지)

## 금지 표현 목록 (절대 사용 금지)
- 유보: "~경향이 있다", "~할 수 있다", "~편이에요", "~보일 수 있어요"
- 허락: "~해도 돼요", "~괜찮아요", "~나쁘지 않아요"
- 게이밍/캐주얼: "치트키", "꿀팁", "핵꿀", "개꿀", "간지"
- "느낌" 남발: "부드러운 느낌" → "부드러운 무드" 또는 "부드러워요"로 교체
- 한영 동어반복: "소프트한 부드러운", "볼드한 강렬한" → 한 쪽만 사용
- 오탈자: "코등" → "콧등", "코볼" → "콧볼"

## 톤 가이드
- 전문가가 1:1 상담하듯 직접적이고 단정적으로
- "~해보세요"는 OK, "~하면 좋을 것 같아요"는 금지
- 남성(male)에게는 "메이크업" 대신 "그루밍", "스킨케어", "헤어스타일링" 중심
- 여성(female)에게는 "메이크업", "헤어", "스타일링" 자유롭게

각 추천에 대해:
1. 왜 이 영역인지 한 줄 이유
2. 초보자용 적용 팁 1개 (구체적, 실행 가능)
3. 주의할 점 (avoid가 있으면)

## summary 규칙 (필수)
- 반드시 현재 인상과 추구 방향의 차이를 1문장 이상 포함하세요
- 핵심 action 방향을 1문장 이상 포함하세요
- 유저의 퍼스널컬러 타입이 주어지면, "이 방향으로 가려면 컬러는 ___계열을 잡으세요" 식의 톤 가이드를 1문장 포함하세요
- 최소 2문장, 최대 4문장
- 금지: "스타일링을 추천해요" 수준의 일반론만으로 끝내기
- 필수 포함: 매칭 유형명, 추구 방향, 구체적 포인트 1개 이상

반드시 아래 JSON 구조로만 응답하세요. 다른 텍스트를 포함하지 마세요.

{
  "summary": "전체 요약 2~4문장 (현재 인상 + 추구 방향 + 핵심 action)",
  "action_tips": [
    {
      "zone": "영역명 (입력 그대로)",
      "title": "추천 제목",
      "description": "설명 2~3문장",
      "beginner_tip": "초보자 팁 1문장"
    }
  ],
  "avoid_tip": "주의할 점 1~2문장 (없으면 null)",
  "closing": "마무리 한 줄"
}"""


def generate_report(action_spec, user_context: dict) -> str:
    """
    Action Spec 기반 리포트 생성 (v2).
    Claude에게 최소 입력만 전달하고, 해설만 받는다.

    Args:
        action_spec: ActionSpec 인스턴스
        user_context: {"name": str, "face_shape": str, "tier": str, "gender": str}

    Returns:
        Claude raw 응답 문자열 (parse_or_fallback으로 후처리)
    """
    prompt_payload = {
        "user_name": user_context.get("name", ""),
        "face_shape": user_context.get("face_shape", ""),
        "tier": user_context.get("tier", "basic"),
        "matched_type": action_spec.matched_type_label,
        "primary_change_direction": action_spec.primary_gap_axis,
        "recommended_actions": [
            {"순서": a.priority, "영역": a.zone, "방법": a.method, "효과": a.goal}
            for a in action_spec.recommended_actions
        ],
        "avoid_actions": [
            {"영역": a.zone, "이유": a.reason}
            for a in action_spec.avoid_actions
        ],
        "expected_effects": action_spec.expected_effects,
    }

    # summary_context 구성
    aspiration_summary = user_context.get("aspiration_summary", "")
    gap_direction_kr = user_context.get("primary_gap_direction_kr", "")
    top_goals = [a.goal for a in action_spec.recommended_actions[:2]]

    personal_color = user_context.get("personal_color", "")

    user_prompt = f"""{user_context.get('name', '')}님의 스타일링 추천을 설명해주세요.

[매칭 유형] {prompt_payload['matched_type']}
[주요 변화 방향] {prompt_payload['primary_change_direction']}
[추구미 해석] {aspiration_summary}
[변화 방향 한글] {gap_direction_kr}
[핵심 액션 목표] {', '.join(top_goals)}
[얼굴형] {prompt_payload['face_shape']}
[성별] {user_context.get('gender', 'female')}
[퍼스널컬러] {personal_color or '미판정'}

[추천 액션]
{json.dumps(prompt_payload['recommended_actions'], ensure_ascii=False, indent=2)}

[주의 사항]
{json.dumps(prompt_payload['avoid_actions'], ensure_ascii=False, indent=2) if prompt_payload['avoid_actions'] else '없음'}

[기대 효과]
{chr(10).join('- ' + e for e in prompt_payload['expected_effects'])}

JSON으로만 응답해주세요."""

    return _call_llm(REPORT_SYSTEM_V2, user_prompt, max_tokens=1500)


# ─────────────────────────────────────────────
#  2.5. JSON parse fallback
# ─────────────────────────────────────────────

import re


def parse_or_fallback(raw_text: str, action_spec) -> dict:
    """Claude JSON 파싱. 실패 시 deterministic fallback."""
    # 1차: 직접 파싱
    try:
        return json.loads(raw_text)
    except (json.JSONDecodeError, TypeError):
        pass

    # 2차: fenced code block 제거 후 재시도
    try:
        cleaned = re.sub(r'^```(?:json)?\s*', '', raw_text.strip())
        cleaned = re.sub(r'\s*```$', '', cleaned)
        return json.loads(cleaned)
    except (json.JSONDecodeError, TypeError):
        pass

    # 3차: deterministic fallback
    return _build_fallback_report(action_spec)


def _build_fallback_report(action_spec) -> dict:
    """Claude 파싱 실패 시 Action Spec으로 직접 리포트 생성"""
    return {
        "summary": " ".join(action_spec.expected_effects[:2]),
        "action_tips": [
            {
                "zone": a.zone,
                "title": a.goal,
                "description": f"{a.zone} 영역에 {a.method}을 적용해보세요.",
                "beginner_tip": "거울을 보면서 소량부터 시작해보세요.",
            }
            for a in action_spec.recommended_actions
        ],
        "avoid_tip": (
            action_spec.avoid_actions[0].reason if action_spec.avoid_actions else None
        ),
        "closing": "한 가지씩 천천히 시도해보세요.",
    }


# ─────────────────────────────────────────────
#  2.9. Legacy generate_report (하위 호환)
# ─────────────────────────────────────────────

def generate_report_legacy(
    user_name: str,
    tier: str,
    face_features: dict,
    current_coords: dict,
    aspiration_coords: dict,
    gap: dict,
    interview_data: dict,
    aspiration_interpretation: dict,
    similar_types: Optional[list[dict]] = None,
    type_comparisons: Optional[list[dict]] = None,
    cluster_result: Optional[dict] = None,
) -> dict:
    """Legacy report generation — Phase 4에서 제거 예정."""
    return {
        "executive_summary": "리포트 생성 방식이 변경되었습니다.",
        "sections": [],
        "action_items": [],
        "similar_types": [],
        "trend_context": "",
    }


# ─────────────────────────────────────────────
#  3. Face Structure Interpretation
#     raw 수치 → 자연어 해석
# ─────────────────────────────────────────────

FACE_INTERPRET_SYSTEM = """당신은 SIGAK의 얼굴 구조 분석 전문가입니다.
InsightFace 랜드마크에서 추출한 수치 데이터를 기반으로,
유저의 얼굴 구조 특징을 자연어로 해석합니다.

톤:
- 판단이 아닌 관찰. "예쁘다/못생겼다"가 아니라 "이러한 특징을 가지고 있다"
- 따뜻하고 전문적인 어조, 해요체
- 전체적인 조화와 특징적인 포인트를 함께 언급
- "~경향이 있다", "~할 수 있다", "~편이에요" 등 유보적 hedging 표현 절대 금지
- 단정적으로 서술하세요: "둥근 인상을 줘요", "입체적인 구조예요"
- 부드럽게 하고 싶으면 유보 표현 대신 별도 부연 문장을 추가하세요

## 해석문 작성 규칙 (필수)
- 해석 문장에 숫자, 소수점, 도(°), 퍼센트(%)를 절대 포함하지 마세요.
- 숫자는 구조화 JSON 필드(value, percentile)에만 남기세요.
- "각도로", "비율로", "돌출도로", "근접도로" 같은 측정 단위+조사 시작 패턴도 금지합니다.
- 해석문은 반드시 의미 중심으로 시작하세요.
- 서술문은 의미와 인상만 설명하세요.

절대 금지 사항:
- 소수점 숫자 (0.613, 0.192 등) 절대 포함하지 마세요
- 퍼센타일 (P45, 상위 30% 등) 절대 포함하지 마세요
- 좌표값 (-0.70, 0.10 등) 절대 포함하지 마세요
- 각도는 자연어로만 표현하세요 ("날카로운 턱선", "부드러운 곡선")
- 영문 zone 이름 (under_eye, brow_arch 등) 대신 한글 (눈 밑, 눈썹 등) 사용하세요
- "느낌" 남발 금지. "부드러운 느낌" → "부드러운 인상" 또는 "부드러워요"
- 한영 동어반복 금지: "소프트한 부드러운" → "부드러운" 하나만
- 오탈자 주의: "코등"(X) → "콧등"(O), "코볼"(X) → "콧볼"(O)
- "치트키", "꿀팁" 등 캐주얼 표현 금지

- 금지 예: "93.7°의 턱선 각도는 날카로운 편으로"
- 허용 예: "턱선이 날카롭고 또렷한 인상을 만들어요"
- 금지 예: "0.719의 광대 돌출도는 상당히 뚜렷한 편으로"
- 허용 예: "광대가 뚜렷해서 입체적이고 개성 있는 인상을 줘요"

[중요] feature 필드는 반드시 아래 목록에서만 선택하세요. 다른 키를 만들지 마세요:
- jaw_angle (턱선)
- eye_tilt (눈꼬리 기울기)
- eye_width_ratio (눈 크기)
- cheekbone_prominence (광대)
- lip_fullness (입술)
- nose_length_ratio (코 길이)
- nose_bridge_height (코 높이)
- face_length_ratio (얼굴 종횡비)
- forehead_ratio (이마 비율)
- brow_arch (눈썹 아치)
- symmetry_score (대칭도)
- golden_ratio_score (황금비)

5~7개 항목을 선택하여 해석하세요.

반드시 아래 JSON 구조로만 출력하세요. 다른 텍스트 금지.

{
  "overall_impression": "전체적인 인상을 2~3문장으로 요약. 숫자 없이 의미만.",
  "feature_interpretations": [
    {
      "feature": "jaw_angle",
      "label": "턱선",
      "interpretation": "자연어 해석 1~2문장. 숫자 없이 인상과 느낌만."
    }
  ],
  "harmony_note": "얼굴 전체 조화에 대한 1문장 코멘트",
  "distinctive_points": ["특징적인 포인트 1~3개 (숫자 없이)"]
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
