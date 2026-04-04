// 섹션 렌더러 - 섹션 ID에 따라 적절한 섹션 컴포넌트 렌더링

import type { AccessLevel, ReportSection } from "@/lib/types/report";
import { isSectionLocked } from "@/lib/utils/report";
import { Cover } from "./sections/cover";
import { ExecutiveSummary } from "./sections/executive-summary";
import { FaceStructure } from "./sections/face-structure";
import { SkinAnalysis } from "./sections/skin-analysis";
import { CoordinateMap } from "./sections/coordinate-map";
import { ActionPlan } from "./sections/action-plan";
import { CelebReference } from "./sections/celeb-reference";
import { TrendContext } from "./sections/trend-context";

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
    case "executive_summary":
      return (
        <ExecutiveSummary
          content={content as Parameters<typeof ExecutiveSummary>[0]["content"]}
          locked={locked}
        />
      );
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
    case "coordinate_map":
      return (
        <CoordinateMap
          content={content as Parameters<typeof CoordinateMap>[0]["content"]}
          locked={locked}
        />
      );
    case "action_plan":
      return (
        <ActionPlan
          content={content as Parameters<typeof ActionPlan>[0]["content"]}
          locked={locked}
        />
      );
    case "celeb_reference":
      return (
        <CelebReference
          content={content as Parameters<typeof CelebReference>[0]["content"]}
          locked={locked}
        />
      );
    case "trend_context":
      return (
        <TrendContext
          content={content as Parameters<typeof TrendContext>[0]["content"]}
          locked={locked}
        />
      );
    default:
      return null;
  }
}
