"""Sia parser unit tests (v2 Priority 1 D5 Task 1).

`services.sia_parser.parse_sia_output` / `is_name_fallback_turn` 전수 검증.

커버 케이스:
  - 정확히 4 라인 하이픈 → mode="choices"
  - 3 또는 5+ 라인 하이픈 → mode="freetext"
  - 4 라인 사이 공백 → mode="freetext"
  - 4 라인 중간에 등장 (뒤에 다른 서술) → mode="freetext"
  - bullet 만 있고 body 없음 → mode="choices", body=""
  - trailing whitespace 허용
  - 빈 문자열 / None 대체 → freetext
  - 하이픈 + 공백 아닌 경우 ("-abc") → bullet 인식 안 함
  - name_fallback 판정: 첫 턴 + 한글 이름 없음 + resolved_name 없음
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.sia_parser import is_name_fallback_turn, parse_sia_output


# ─────────────────────────────────────────────
#  parse_sia_output — choices 모드
# ─────────────────────────────────────────────

def test_parses_four_hyphen_choices():
    """정확히 4 라인 연속 하이픈 → mode=choices, body 는 위 텍스트."""
    text = (
        "정세현님은 쿨뮤트 톤이 일관된 분입니다. 피드 분석 완료했습니다.\n"
        "\n"
        "어떤 인상으로 기억되고 싶으신가요?\n"
        "- 편안하고 기대고 싶은 인상\n"
        "- 세련되고 거리감 있는 인상\n"
        "- 특별한 날처럼 공들인 인상\n"
        "- 무심한데 센스 있는 인상"
    )
    body, choices, mode = parse_sia_output(text)
    assert mode == "choices"
    assert choices == [
        "편안하고 기대고 싶은 인상",
        "세련되고 거리감 있는 인상",
        "특별한 날처럼 공들인 인상",
        "무심한데 센스 있는 인상",
    ]
    assert "어떤 인상으로 기억되고 싶으신가요?" in body
    # body 에는 bullet 포함되면 안 됨
    assert "- 편안하고" not in body


def test_trailing_whitespace_tolerant():
    """각 bullet 라인의 trailing whitespace/탭 허용."""
    text = (
        "질문입니다.\n"
        "- 선택1   \n"
        "- 선택2\t\n"
        "- 선택3 \n"
        "- 선택4"
    )
    body, choices, mode = parse_sia_output(text)
    assert mode == "choices"
    assert choices == ["선택1", "선택2", "선택3", "선택4"]


def test_only_choices_no_body():
    """body 없이 bullet 만 있는 경우도 choices 인정. body 는 빈 문자열."""
    text = "- A\n- B\n- C\n- D"
    body, choices, mode = parse_sia_output(text)
    assert mode == "choices"
    assert choices == ["A", "B", "C", "D"]
    assert body == ""


# ─────────────────────────────────────────────
#  parse_sia_output — freetext 모드
# ─────────────────────────────────────────────

def test_three_hyphens_freetext():
    """3 라인 하이픈 → freetext. body 는 원문 유지."""
    text = "질문?\n- A\n- B\n- C"
    body, choices, mode = parse_sia_output(text)
    assert mode == "freetext"
    assert choices == []
    assert body == text


def test_five_hyphens_freetext():
    """5 라인 하이픈 → freetext. body 는 원문 유지."""
    text = "질문?\n- A\n- B\n- C\n- D\n- E"
    body, choices, mode = parse_sia_output(text)
    assert mode == "freetext"
    assert choices == []
    assert body == text


def test_hyphens_midtext_freetext():
    """4 라인 하이픈이 텍스트 중간, 뒤에 다른 서술 있음 → freetext."""
    text = (
        "서술 앞.\n"
        "- A\n- B\n- C\n- D\n"
        "이어지는 서술입니다."
    )
    body, choices, mode = parse_sia_output(text)
    assert mode == "freetext"
    assert choices == []
    assert body == text


def test_four_hyphens_with_blank_line_inside_freetext():
    """4 라인이지만 사이에 공백 라인 존재 → 연속 아님 → freetext."""
    text = "질문?\n- A\n- B\n\n- C\n- D"
    body, choices, mode = parse_sia_output(text)
    assert mode == "freetext"
    assert choices == []


def test_malformed_hyphen_no_space_freetext():
    """'-abc' 는 bullet 인식 안 함 (rule: '- ' 하이픈+공백 필수)."""
    text = "질문?\n-A\n-B\n-C\n-D"
    body, choices, mode = parse_sia_output(text)
    assert mode == "freetext"
    assert choices == []


def test_empty_output():
    """빈 문자열 → freetext, choices=[]."""
    body, choices, mode = parse_sia_output("")
    assert mode == "freetext"
    assert choices == []


def test_whitespace_only_output():
    """공백/개행만 → freetext."""
    body, choices, mode = parse_sia_output("   \n  \n")
    assert mode == "freetext"
    assert choices == []


def test_asterisk_bullet_not_recognized_as_hyphen():
    """별표 bullet 은 하이픈이 아니므로 choices 로 인식 안 함 (Hard Rule #4 별도)."""
    text = "질문?\n* A\n* B\n* C\n* D"
    body, choices, mode = parse_sia_output(text)
    assert mode == "freetext"


# ─────────────────────────────────────────────
#  is_name_fallback_turn
# ─────────────────────────────────────────────

def test_is_name_fallback_turn_first_turn_empty_name():
    """첫 턴 + 한글 이름 없음 + resolved_name 없음 → True."""
    assert is_name_fallback_turn(
        user_has_korean_name=False,
        resolved_name=None,
        turn_count=0,
    )


def test_is_name_fallback_turn_korean_name_false():
    """한글 이름 있으면 False — 1순위 호칭 직접 사용."""
    assert not is_name_fallback_turn(
        user_has_korean_name=True,
        resolved_name=None,
        turn_count=0,
    )


def test_is_name_fallback_turn_already_resolved():
    """fallback 응답 이미 받은 경우 (resolved_name 설정됨) → False."""
    assert not is_name_fallback_turn(
        user_has_korean_name=False,
        resolved_name="민지",
        turn_count=0,
    )


def test_is_name_fallback_turn_not_first_turn():
    """turn_count > 0 이면 fallback 이미 지나갔음 → False."""
    assert not is_name_fallback_turn(
        user_has_korean_name=False,
        resolved_name=None,
        turn_count=1,
    )


def test_is_name_fallback_turn_empty_string_resolved():
    """resolved_name="" (빈 문자열) 도 falsy → fallback 활성."""
    assert is_name_fallback_turn(
        user_has_korean_name=False,
        resolved_name="",
        turn_count=0,
    )
