// 섹션 렌더러 — 섹션 ID에 따라 적절한 섹션 컴포넌트 렌더링.
//
// PI v3 9 컴포넌트 (본인 결정 2026-04-25):
//   raw 3   : cover / celeb_reference / face_structure
//   vault 3 : type_reference / gap_analysis / skin_analysis
//   trend 3 : coordinate_map / hair_recommendation / action_plan
//
// PI v3 풀 화면은 components/pi-v3/PIv3Screen 이 inline 렌더.
// 이 파일은 v1/v2 legacy 리포트 흐름 유지 + executive_summary / trend_context 폐기.

import type { AccessLevel, ReportSection } from "@/lib/types/report";
import { isSectionLocked } from "@/lib/utils/report";
import { Cover } from "./sections/cover";
import { FaceStructure } from "./sections/face-structure";
import { SkinAnalysis } from "./sections/skin-analysis";
import { CoordinateMap } from "./sections/coordinate-map";

import { GapAnalysis } from "./sections/gap-analysis";
import { HairRecommendation } from "./sections/hair-recommendation";
import { ActionPlan } from "./sections/action-plan";
import { TypeReference } from "./sections/type-reference";

interface OverlayData {
  before_url: string;
  after_url: string;
}

interface HairSimulationData {
  before_url: string;
  after_url: string;
  color_name: string;
  color_hex: string;
}

interface SectionRendererProps {
  section: ReportSection;
  accessLevel: AccessLevel;
  overlay?: OverlayData | null;
  hairSimulation?: HairSimulationData | null;
}

// 섹션 타입별 분기 렌더링 - 각 section의 locked 상태 계산 후 해당 컴포넌트로 전달
export function SectionRenderer({ section, accessLevel, overlay, hairSimulation }: SectionRendererProps) {
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
      return (
        <HairRecommendation
          content={content as Parameters<typeof HairRecommendation>[0]["content"]}
          locked={locked}
        />
      );
    case "action_plan":
      return (
        <ActionPlan
          content={content as Parameters<typeof ActionPlan>[0]["content"]}
          locked={locked}
          overlay={overlay}
          hairSimulation={hairSimulation}
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
