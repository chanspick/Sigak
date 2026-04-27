// 섹션 렌더러 — 섹션 ID에 따라 적절한 섹션 컴포넌트 렌더링.
//
// PI v3 폐기 (PI-REVIVE Phase 5, 2026-04-26). 옛 SIGAK_V3 system 사용.
// 풀 리포트 = /report/{id}/full + components/report/sections/* (B안 재활용 5개).

import type { AccessLevel, ReportSection } from "@/lib/types/report";
import { isSectionLocked } from "@/lib/utils/report";
import { Cover } from "./sections/cover";
import { FaceStructure } from "./sections/face-structure";
import { SkinAnalysis } from "./sections/skin-analysis";
import { CoordinateMap } from "./sections/coordinate-map";

import { GapAnalysis } from "./sections/gap-analysis";
// 2026-04-27 마케터 결정 — hair_recommendation 섹션 미렌더. 부활 시 import 복원 + case 의 return null 제거.
// import { HairRecommendation } from "./sections/hair-recommendation";
import { ActionPlan } from "./sections/action-plan";
import { TypeReference } from "./sections/type-reference";

// Phase B-2.5 (PI-REVIVE 2026-04-26): OverlayData / HairSimulationData props 제거.
// MAKEUP OVERLAY + HAIR COLOR SIMULATION 슬라이더 미사용. v1.5 부활 시 복원.

interface SectionRendererProps {
  section: ReportSection;
  accessLevel: AccessLevel;
}

// 섹션 타입별 분기 렌더링 - 각 section의 locked 상태 계산 후 해당 컴포넌트로 전달
export function SectionRenderer({ section, accessLevel }: SectionRendererProps) {
  // 현재 access_level 기준으로 잠금 상태 계산
  const locked = isSectionLocked(section, accessLevel);
  // 섹션 콘텐츠 (unknown으로 중간 캐스팅하여 타입 안전하게 전달)
  const content = section.content as unknown;

  if (!content) return null;

  switch (section.id) {
    case "cover":
      return (
        <Cover
          content={content as Parameters<typeof Cover>[0]["content"]}
          locked={locked}
        />
      );
    // PI v3 폐기 — executive_summary 는 cover 가 흡수 (user_summary + needs_statement)
    case "face_structure":
      return (
        <FaceStructure
          content={content as Parameters<typeof FaceStructure>[0]["content"]}
          locked={locked}
        />
      );
    case "skin_analysis":
      return (
        <SkinAnalysis
          content={content as Parameters<typeof SkinAnalysis>[0]["content"]}
          locked={locked}
        />
      );
    case "gap_analysis":
      return (
        <GapAnalysis
          content={content as Parameters<typeof GapAnalysis>[0]["content"]}
          locked={locked}
        />
      );
    case "coordinate_map":
      return (
        <CoordinateMap
          content={content as Parameters<typeof CoordinateMap>[0]["content"]}
          locked={locked}
        />
      );
    case "hair_recommendation":
      // 2026-04-27 마케터 결정: PI 레포트에서 hair_recommendation 섹션 숨김
      // ("단 너무 무의미"). 컴포넌트 + 데이터는 보존 — UI 만 미렌더.
      // 부활하려면 본 case 의 return null 만 제거.
      return null;
    case "action_plan":
      return (
        <ActionPlan
          content={content as Parameters<typeof ActionPlan>[0]["content"]}
          locked={locked}
        />
      );
    case "type_reference":
      return (
        <TypeReference
          content={content as Parameters<typeof TypeReference>[0]["content"]}
          locked={locked}
        />
      );
    // PI v3 폐기 — celeb_reference (본인 결정 2026-04-26 / CLAUDE.md feedback_no_celeb_names)
    // PI v3 폐기 — trend_context 는 hair_recommendation / action_plan 의 matched_trend_ids 로 흡수
    default:
      return null;
  }
}
