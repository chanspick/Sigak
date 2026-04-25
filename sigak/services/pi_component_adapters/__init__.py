"""PI 9 컴포넌트 어댑터 패키지 — Phase I PI-C.

각 어댑터는 순수 함수. side effect / LLM 호출 / R2 호출 없음.
PI-A 가 본 패키지의 어댑터들을 호출해 PiContent 를 합성한 뒤 LLM payload 또는
DB 영속화에 사용.

레이아웃:
  raw 3:   coordinate_map / face_structure / celeb_reference
  vault 3: cover / type_reference / gap_analysis
  trend 3: skin_analysis / hair_recommendation / action_plan

preview_dispatcher.to_preview 는 PiContent → PiPreview 혼합 iii 분배.
"""
from services.pi_component_adapters.action_plan_adapter import build_action_plan
from services.pi_component_adapters.celeb_reference_adapter import build_celeb_reference
from services.pi_component_adapters.coordinate_map_adapter import build_coordinate_map
from services.pi_component_adapters.cover_adapter import build_cover
from services.pi_component_adapters.face_structure_adapter import build_face_structure
from services.pi_component_adapters.gap_analysis_adapter import build_gap_analysis
from services.pi_component_adapters.hair_recommendation_adapter import (
    build_hair_recommendation,
)
from services.pi_component_adapters.preview_dispatcher import to_preview
from services.pi_component_adapters.skin_analysis_adapter import build_skin_analysis
from services.pi_component_adapters.type_reference_adapter import build_type_reference

__all__ = [
    "build_action_plan",
    "build_celeb_reference",
    "build_coordinate_map",
    "build_cover",
    "build_face_structure",
    "build_gap_analysis",
    "build_hair_recommendation",
    "build_skin_analysis",
    "build_type_reference",
    "to_preview",
]
