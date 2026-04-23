"""CoordinateSystem — Shape/Volume/Age 3축 미감 좌표계 (Phase G3).

CLAUDE.md §4.4 / §12.1 확정:
  Shape  — 얼굴형/실루엣 (0=소프트/둥근, 1=샤프/각진)
  Volume — 부피감/입체감 (0=평면,      1=입체)
  Age    — 인상 성숙도  (0=베이비/프레시, 1=매추어/성숙)

설계:
- 유저 대면 스케일: 0~1
- 내부 연산 스케일: -1~+1 (delta 누적용)
- 변환: internal = user * 2 - 1  /  user = (internal + 1) / 2
- 환각 방지: 모든 좌표 산출은 실 데이터 기반 (Vision/대화 delta 누적)
  → 매직 넘버 가중치 금지. Haiku/Sonnet 산출 값 직접 반영.

사용처 (Phase I~M 에서 consume):
- UserTasteProfile.current_position      — Sia 대화에서 누적된 유저 좌표
- UserTasteProfile.aspiration_vector     — 추구미 분석 결과 갭
- KnowledgeMatcher.match_trends_for_user — compatible_coordinates 범위 매칭
- PI 리포트 / 추구미 비교 리포트 시각화
"""
from __future__ import annotations

import math
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


AxisName = Literal["shape", "volume", "age"]

AXIS_ORDER: tuple[AxisName, ...] = ("shape", "volume", "age")


class AxisDefinition(BaseModel):
    """축 메타 — UI 라벨링 / 내러티브 문구에 재사용."""
    model_config = ConfigDict(frozen=True)

    name: AxisName
    name_kr: str
    negative_label_kr: str      # 0 쪽 극점
    positive_label_kr: str      # 1 쪽 극점
    negative_short: str         # 내러티브 단축 — "소프트" 등
    positive_short: str


AXES: dict[AxisName, AxisDefinition] = {
    "shape": AxisDefinition(
        name="shape",
        name_kr="형태",
        negative_label_kr="소프트/둥근",
        positive_label_kr="샤프/각진",
        negative_short="소프트",
        positive_short="샤프",
    ),
    "volume": AxisDefinition(
        name="volume",
        name_kr="부피",
        negative_label_kr="평면/플랫",
        positive_label_kr="입체/볼륨",
        negative_short="평면",
        positive_short="입체",
    ),
    "age": AxisDefinition(
        name="age",
        name_kr="인상",
        negative_label_kr="베이비/프레시",
        positive_label_kr="매추어/성숙",
        negative_short="프레시",
        positive_short="성숙",
    ),
}


# ─────────────────────────────────────────────
#  VisualCoordinate
# ─────────────────────────────────────────────

class VisualCoordinate(BaseModel):
    """유저 대면 3축 좌표 (0~1 외부 스케일).

    Haiku/Sonnet 산출 값을 직접 반영. 매직 넘버 가중 금지.
    """
    model_config = ConfigDict(extra="ignore")

    shape: float = Field(ge=0.0, le=1.0)
    volume: float = Field(ge=0.0, le=1.0)
    age: float = Field(ge=0.0, le=1.0)

    def as_tuple(self) -> tuple[float, float, float]:
        return (self.shape, self.volume, self.age)

    def distance_to(self, other: "VisualCoordinate") -> float:
        """Euclidean 거리 (0~√3). 작을수록 유사."""
        a = self.as_tuple()
        b = other.as_tuple()
        return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))

    def gap_vector(self, target: "VisualCoordinate") -> "GapVector":
        """self → target 로의 이동 벡터.

        primary = |delta| 최대인 축, secondary = 그 다음.
        delta 부호는 그대로 (양수=positive 방향 이동, 음수=negative 방향).
        """
        deltas: list[tuple[AxisName, float]] = [
            ("shape",  target.shape  - self.shape),
            ("volume", target.volume - self.volume),
            ("age",    target.age    - self.age),
        ]
        ranked = sorted(deltas, key=lambda t: abs(t[1]), reverse=True)
        (p_axis, p_delta), (s_axis, s_delta), (t_axis, t_delta) = ranked
        return GapVector(
            primary_axis=p_axis,
            primary_delta=p_delta,
            secondary_axis=s_axis,
            secondary_delta=s_delta,
            tertiary_axis=t_axis,
            tertiary_delta=t_delta,
        )

    @classmethod
    def from_internal(cls, shape: float, volume: float, age: float) -> "VisualCoordinate":
        """내부 스케일 (-1~+1) → 유저 스케일 (0~1)."""
        return cls(
            shape=_to_external(shape),
            volume=_to_external(volume),
            age=_to_external(age),
        )

    def to_internal(self) -> tuple[float, float, float]:
        return (
            _to_internal(self.shape),
            _to_internal(self.volume),
            _to_internal(self.age),
        )

    def apply_deltas(self, shape_d: float, volume_d: float, age_d: float) -> "VisualCoordinate":
        """내부 스케일 delta 누적 후 clamp. Sia 대화 중 매 메시지 Haiku 가 산출.

        내부 스케일에서 누적한 뒤 외부로 변환. clamp 로 경계 안전.
        """
        si, vi, ai = self.to_internal()
        si = _clamp(si + shape_d, -1.0, 1.0)
        vi = _clamp(vi + volume_d, -1.0, 1.0)
        ai = _clamp(ai + age_d, -1.0, 1.0)
        return VisualCoordinate.from_internal(si, vi, ai)


def _to_external(internal: float) -> float:
    """-1..+1 → 0..1 (clamp 후 변환)."""
    return (_clamp(internal, -1.0, 1.0) + 1.0) / 2.0


def _to_internal(external: float) -> float:
    """0..1 → -1..+1."""
    return _clamp(external, 0.0, 1.0) * 2.0 - 1.0


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


# ─────────────────────────────────────────────
#  GapVector
# ─────────────────────────────────────────────

class GapVector(BaseModel):
    """현재 → 목표 3축 이동 벡터. 추구미 분석 + PI 리포트 narrative 에 사용."""
    model_config = ConfigDict(extra="ignore")

    primary_axis: AxisName
    primary_delta: float        # -1..+1 (외부 스케일 기준)

    secondary_axis: AxisName
    secondary_delta: float

    tertiary_axis: AxisName
    tertiary_delta: float

    def magnitude(self) -> float:
        """이동 총 거리 (|delta| 합)."""
        return abs(self.primary_delta) + abs(self.secondary_delta) + abs(self.tertiary_delta)

    def narrative(self) -> str:
        """페르소나 B 톤 서술 — Sia 리포트에 그대로 사용 가능.

        예시 출력:
          "형태 쪽으로 +0.30 이동이 크고 (소프트 → 샤프),
           부피는 +0.15 보조 이동 (평면 → 입체),
           인상은 거의 같이 가요."
        """
        parts: list[str] = []
        for axis, delta, label_primary in (
            (self.primary_axis, self.primary_delta, True),
            (self.secondary_axis, self.secondary_delta, False),
        ):
            direction, axis_info = _direction_text(axis, delta)
            if label_primary:
                parts.append(
                    f"{axis_info.name_kr} 쪽으로 {_fmt_signed(delta)} 이동이 크고 ({direction})"
                )
            else:
                parts.append(
                    f"{axis_info.name_kr}은 {_fmt_signed(delta)} 보조 이동 ({direction})"
                )

        # 3번째 축: |delta| 작으면 "거의 같이" 표현
        if abs(self.tertiary_delta) < 0.05:
            t_info = AXES[self.tertiary_axis]
            parts.append(f"{t_info.name_kr}은 거의 같이 가요")
        else:
            t_direction, t_info = _direction_text(self.tertiary_axis, self.tertiary_delta)
            parts.append(
                f"{t_info.name_kr}은 {_fmt_signed(self.tertiary_delta)} ({t_direction})"
            )

        return ", ".join(parts) + "."


def _direction_text(axis: AxisName, delta: float) -> tuple[str, AxisDefinition]:
    """delta 부호에 따른 방향 라벨 — ("소프트 → 샤프", AxisDef)."""
    info = AXES[axis]
    if delta >= 0:
        return f"{info.negative_short} → {info.positive_short}", info
    return f"{info.positive_short} → {info.negative_short}", info


def _fmt_signed(x: float) -> str:
    """0.30 / -0.15 형태. 3축 소수 둘째 자리 표기."""
    return f"{x:+.2f}"


# ─────────────────────────────────────────────
#  Mid / neutral 기본값
# ─────────────────────────────────────────────

def neutral_coordinate() -> VisualCoordinate:
    """(0.5, 0.5, 0.5) — 데이터 부족 시 기본 neutral."""
    return VisualCoordinate(shape=0.5, volume=0.5, age=0.5)
