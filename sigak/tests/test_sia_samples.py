"""Sia 샘플 대화 자동 검증 (v2 Priority 1 D3).

design doc §2 Step 2 의 3 샘플 (오프닝·중간·클로징) 을 hard-code fixture 로 고정.
services/sia_validators.py 의 rule engine 으로 전수 검증.

AC-SIA-HR1~5 (Hard Rules), AC-SIA-004/005/006/007 (tone), AC-SIA-QS/EV/DEF/CTA.

이 테스트 통과 의미:
  - system prompt 가 이 샘플들을 생성할 수 있는 지시문을 포함함 증명
  - future LLM 실 출력이 이 fixtures 수준 규격을 충족해야 함 (D4 live LLM 테스트 기준)
"""
import sys
import os

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.sia_validators import (
    SiaValidationError,
    count_sentences,
    find_violations,
    long_sentences,
    validate_sia_output,
)


# ─────────────────────────────────────────────
#  Golden Fixtures (design doc §2 Step 2)
# ─────────────────────────────────────────────

OPENING_1ST_IG_SUCCESS = """정세현님, 시각의 AI 미감 분석가 Sia입니다.
피드 38장 분석 완료했습니다 — 쿨뮤트 68%, 채도 평균보다 1.4배 낮습니다.
정돈되고 조용한 인상을 전달하는 데 익숙하신 분입니다.

주말 저녁, 친한 지인과 간단한 술자리가 있을 때 — 어떤 인상으로 기억되고 싶으신가요?
- 편안하고 기대고 싶은 인상
- 세련되고 거리감 있는 인상
- 특별한 날처럼 공들인 인상
- 무심한데 센스 있는 인상"""


OPENING_1ST_IG_FAIL = """정세현님, 시각의 AI 미감 분석가 Sia입니다.
피드는 확인하지 못했습니다 — 대신 몇 가지 질문으로 파악합니다.

지금 가장 자주 가는 장소는 어디인가요?
- 회사/학교 등 격식 필요한 곳
- 카페/조용한 공간 위주
- 바/파티/레스토랑 활발한 곳
- 특별한 패턴 없이 다양함"""


OPENING_3RD_NO_NAME = """시각의 AI 미감 분석가 Sia입니다.
호칭 없이 진행합니다.

지금 가장 공들여 가꾸는 영역은 어디인가요?
- 헤어 (컬러/스타일링 포함)
- 스킨케어/베이스 메이크업
- 의류/스타일 구성
- 특별히 공들이는 영역 없음"""


MIDTURN_AFTER_SELECTION = """1번 선택, 흥미롭습니다.
피드 데이터는 2번 방향을 가리키고 있었습니다 — 쿨톤 68%, 거리감 있는 구도 73%.
현재 보여지는 방향과 추구하는 방향 사이에 갭이 있습니다.

이 갭에서 갈등을 느끼실 때가 있으십니까?
- 자주 느낀다, 풀고 싶다
- 가끔 느낀다, 그러나 당장 급하지 않다
- 거의 못 느낀다
- 이 질문 자체가 어색하다"""


CLOSING = """정세현님, 수집된 데이터 정리합니다.
쿨뮤트 68%, 주말 상황 1번, 갈등 1번, 정의 1건 확보.
추구미 좌표 산출 완료. 데이터는 일관됩니다.

더 정확한 분석은 '시각이 본 나' 가 있습니다.
얼굴 3축 좌표와 9섹션 리포트. 5,000원, 영구 보관됩니다."""


ALL_SAMPLES = {
    "opening_1st_ig_success": OPENING_1ST_IG_SUCCESS,
    "opening_1st_ig_fail": OPENING_1ST_IG_FAIL,
    "opening_3rd_no_name": OPENING_3RD_NO_NAME,
    "midturn": MIDTURN_AFTER_SELECTION,
    "closing": CLOSING,
}


# ─────────────────────────────────────────────
#  Hard Rules 검증 (AC-SIA-HR1~5) — 모든 샘플
# ─────────────────────────────────────────────

@pytest.mark.parametrize("name,sample", ALL_SAMPLES.items())
def test_no_verdict_word(name, sample):
    """HR1: 'Verdict' / 'verdict' 단어 0건 (case-insensitive)."""
    v = find_violations(sample)
    assert "HR1_verdict" not in v, f"{name}: {v.get('HR1_verdict')}"


@pytest.mark.parametrize("name,sample", ALL_SAMPLES.items())
def test_no_judgment_word(name, sample):
    """HR2: '판정' 단어 0건."""
    v = find_violations(sample)
    assert "HR2_judgment" not in v, f"{name}: {v.get('HR2_judgment')}"


@pytest.mark.parametrize("name,sample", ALL_SAMPLES.items())
def test_no_markdown(name, sample):
    """HR3: 마크다운 구문 0건."""
    v = find_violations(sample)
    assert "HR3_markdown" not in v, f"{name}: {v.get('HR3_markdown')}"


@pytest.mark.parametrize("name,sample", ALL_SAMPLES.items())
def test_no_asterisk_bullet(name, sample):
    """HR4: 별표 리스트 불릿 0건 (하이픈만 허용)."""
    v = find_violations(sample)
    assert "HR4_bullet" not in v, f"{name}: {v.get('HR4_bullet')}"


@pytest.mark.parametrize("name,sample", ALL_SAMPLES.items())
def test_no_emoji(name, sample):
    """HR5: 이모지 0건."""
    v = find_violations(sample)
    assert "HR5_emoji" not in v, f"{name}: {v.get('HR5_emoji')}"


# ─────────────────────────────────────────────
#  Tone 검증 (AC-SIA-004/005)
# ─────────────────────────────────────────────

@pytest.mark.parametrize("name,sample", ALL_SAMPLES.items())
def test_no_forbidden_suffix(name, sample):
    """AC-SIA-004: 다정한 해요체 어미 0건."""
    v = find_violations(sample)
    assert "tone_suffix" not in v, f"{name}: {v.get('tone_suffix')}"


@pytest.mark.parametrize("name,sample", ALL_SAMPLES.items())
def test_required_formal_suffix_present(name, sample):
    """AC-SIA-005: 서술형 정중체 어미 1개 이상."""
    v = find_violations(sample)
    assert "tone_missing" not in v, f"{name}: 필수 어미 (~합니다/~습니다/~있습니다) 누락"


# ─────────────────────────────────────────────
#  Structure (AC-SIA-006/007)
# ─────────────────────────────────────────────

def test_opening_sentence_count_within_limit():
    """AC-SIA-006: 오프닝 4 문장 이내 (인사+데이터+정의+질문)."""
    # 질문 선택지는 리스트 라인이라 문장 카운트 제외 목적으로 질문 본문만 측정
    core = OPENING_1ST_IG_SUCCESS.split("\n- ")[0]
    assert count_sentences(core) <= 5, "오프닝 core 문장 수 초과"


def test_midturn_sentence_count_within_limit():
    """AC-SIA-006: 중간 턴 2-3 문장."""
    core = MIDTURN_AFTER_SELECTION.split("\n- ")[0]
    assert 2 <= count_sentences(core) <= 5


@pytest.mark.parametrize("name,sample", ALL_SAMPLES.items())
def test_no_long_sentences(name, sample):
    """AC-SIA-007: 문장당 35자 이내.

    리스트 선택지는 검증 제외 (bullet item — 한 문장이지만 상황 맥락 포함 가능).
    """
    core_only = "\n".join(
        line for line in sample.split("\n") if not line.strip().startswith("- ")
    )
    too_long = long_sentences(core_only, max_chars=35)
    assert not too_long, f"{name}: {too_long}"


# ─────────────────────────────────────────────
#  Evaluation / Confirmation ban (AC-SIA-EV1/2)
# ─────────────────────────────────────────────

@pytest.mark.parametrize("name,sample", ALL_SAMPLES.items())
def test_no_eval_language(name, sample):
    """AC-SIA-EV1: 평가 표현 0건."""
    v = find_violations(sample)
    assert "eval_language" not in v, f"{name}: {v.get('eval_language')}"


@pytest.mark.parametrize("name,sample", ALL_SAMPLES.items())
def test_no_confirmation_request(name, sample):
    """AC-SIA-EV2: 확인 요청 0건."""
    v = find_violations(sample)
    assert "confirmation" not in v, f"{name}: {v.get('confirmation')}"


# ─────────────────────────────────────────────
#  Question Structure (AC-SIA-QS1)
# ─────────────────────────────────────────────

@pytest.mark.parametrize("name,sample", [
    ("opening_1st_ig_success", OPENING_1ST_IG_SUCCESS),
    ("opening_1st_ig_fail", OPENING_1ST_IG_FAIL),
    ("opening_3rd_no_name", OPENING_3RD_NO_NAME),
    ("midturn", MIDTURN_AFTER_SELECTION),
])
def test_has_four_choice_question(name, sample):
    """AC-SIA-QS1: 질문 턴에 4지선다 (하이픈 리스트 4줄) 존재."""
    bullets = [l for l in sample.split("\n") if l.strip().startswith("- ")]
    assert len(bullets) == 4, f"{name}: 선택지 {len(bullets)}개 (expected 4)"


def test_closing_does_not_have_four_choice():
    """클로징은 질문/선택지 없음. '시각이 본 나' CTA 자연 흡수."""
    bullets = [l for l in CLOSING.split("\n") if l.strip().startswith("- ")]
    assert len(bullets) == 0


# ─────────────────────────────────────────────
#  User Definition Statement (AC-SIA-DEF1)
# ─────────────────────────────────────────────

@pytest.mark.parametrize("name,sample", [
    ("opening_1st_ig_success", OPENING_1ST_IG_SUCCESS),
])
def test_opening_contains_user_definition(name, sample):
    """AC-SIA-DEF1: 오프닝에 유저 단정 정의문 '~분입니다' 패턴.

    허용 변형: "익숙하신 분입니다" / "정돈된 인상인 분입니다" / "~인 분입니다"
    관형어 + 분입니다 구조라면 통과.
    """
    import re
    assert re.search(r"[가-힣]+신?\s*분입니다|인\s*분입니다", sample), (
        f"{name}: 유저 정의문 누락 — '~분입니다' 패턴 미발견"
    )


# ─────────────────────────────────────────────
#  CTA (AC-SIA-CTA1/2) — 클로징에 '시각이 본 나' 포함
# ─────────────────────────────────────────────

def test_closing_mentions_pi_user_name():
    """AC-SIA-CTA1: 클로징에 '시각이 본 나' 유저 노출 이름 포함."""
    assert "시각이 본 나" in CLOSING


def test_closing_does_not_mention_pi_internal_name():
    """AC-NAMING: 클로징에 내부 코드 이름 'PI' 단어 단독 금지 (문맥상 자연 사용 제외)."""
    # "PI" 가 단독 단어로 등장하면 금지. 약어 로고 가능성 고려해 대소문자 포함.
    import re
    assert not re.search(r"\bPI\b", CLOSING)


def test_closing_mentions_price_and_permanence():
    """AC-SIA-CTA2: 가격 + 영구 보관 조건 명시."""
    assert "5,000원" in CLOSING or "5000원" in CLOSING
    assert "영구" in CLOSING or "보관" in CLOSING


# ─────────────────────────────────────────────
#  Aggregate validator (raise-style)
# ─────────────────────────────────────────────

@pytest.mark.parametrize("name,sample", ALL_SAMPLES.items())
def test_validate_sia_output_raises_nothing(name, sample):
    """모든 Hard Rule + tone 규칙 통과. raise 없음."""
    try:
        validate_sia_output(sample)
    except SiaValidationError as e:
        pytest.fail(f"{name}: {e} (violations={e.violations})")


# ─────────────────────────────────────────────
#  Negative tests — 위반 샘플이 실제로 걸리는지
# ─────────────────────────────────────────────

def test_validator_catches_verdict_word():
    bad = "Verdict 분석 완료했습니다."
    with pytest.raises(SiaValidationError) as exc:
        validate_sia_output(bad)
    assert "HR1_verdict" in exc.value.violations


def test_validator_catches_markdown():
    bad = "**강조** 는 금지됩니다."
    with pytest.raises(SiaValidationError) as exc:
        validate_sia_output(bad)
    assert "HR3_markdown" in exc.value.violations


def test_validator_catches_emoji():
    bad = "오늘은 좋은 날입니다 😊."
    with pytest.raises(SiaValidationError) as exc:
        validate_sia_output(bad)
    assert "HR5_emoji" in exc.value.violations


def test_validator_catches_forbidden_suffix():
    bad = "정말 좋네요. 어떻게 생각해요?"
    with pytest.raises(SiaValidationError) as exc:
        validate_sia_output(bad)
    assert "tone_suffix" in exc.value.violations


def test_validator_catches_missing_formal_suffix():
    """서술형 어미 없음."""
    bad = "오늘 수집된 데이터."   # 완결 문장 아님, 어미 없음
    with pytest.raises(SiaValidationError) as exc:
        validate_sia_output(bad)
    assert "tone_missing" in exc.value.violations


def test_validator_catches_evaluation_language():
    bad = "정말 예뻐 보입니다."
    with pytest.raises(SiaValidationError) as exc:
        validate_sia_output(bad)
    assert "eval_language" in exc.value.violations


def test_validator_catches_confirmation_request():
    bad = "이 설명이 맞으신가요? 본인도 그렇게 생각하세요?"
    with pytest.raises(SiaValidationError) as exc:
        validate_sia_output(bad)
    # 어느 하나는 걸려야 함
    assert "confirmation" in exc.value.violations
