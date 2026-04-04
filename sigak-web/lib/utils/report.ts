import type { AccessLevel, UnlockLevel, ReportSection } from "@/lib/types/report";

// 리포트 유틸리티

/** 섹션이 현재 access_level에서 잠겨있는지 확인 */
export function isSectionLocked(section: ReportSection, accessLevel: AccessLevel): boolean {
  if (!section.locked) return false;

  if (section.unlock_level === "standard") {
    return !["standard", "full_pending", "full"].includes(accessLevel);
  }
  if (section.unlock_level === "full") {
    return accessLevel !== "full";
  }
  return section.locked;
}

/** 현재 access_level에서 pending 상태인지 확인 */
export function isPendingLevel(accessLevel: AccessLevel, level: UnlockLevel): boolean {
  if (level === "standard") return accessLevel === "standard_pending";
  if (level === "full") return accessLevel === "full_pending";
  return false;
}

/** PaywallGate를 표시해야 하는 레벨 목록 반환 */
export function getPaywallGateLevels(accessLevel: AccessLevel): UnlockLevel[] {
  switch (accessLevel) {
    case "free":
      return ["standard", "full"];
    case "standard_pending":
      return ["standard", "full"];
    case "standard":
      return ["full"];
    case "full_pending":
      return ["full"];
    case "full":
      return [];
    default:
      return ["standard", "full"];
  }
}

/** 특정 unlock_level 그룹의 마지막 섹션 ID 반환 */
export function getLastSectionOfLevel(
  sections: ReportSection[],
  level: UnlockLevel,
): string | null {
  const filtered = sections.filter((s) => s.unlock_level === level);
  return filtered.length > 0 ? filtered[filtered.length - 1].id : null;
}
