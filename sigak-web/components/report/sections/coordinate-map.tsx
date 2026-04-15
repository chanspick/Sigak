// 미감 좌표계 섹션 (standard 잠금)
// 블러 시: 축 이름/격자 선명, 점/수치/화살표 블러
// 공개 시: axes, position, target 전체 표시

const AXIS_DESCRIPTIONS: Record<string, string> = {
  "골격": "턱선, 광대, 눈매가 만드는 골격의 형태",
  "존재감": "이목구비의 선명도",
  "무드": "전체적인 분위기의 방향",
};

interface CoordinateMapContent {
  axes: string[];
  position: number[];
  target: number[];
}

interface CoordinateMapProps {
  content: CoordinateMapContent;
  locked: boolean;
}

// 미감 좌표계 - 4축 분석 결과를 시각적으로 표시
export function CoordinateMap({ content, locked }: CoordinateMapProps) {
  return (
    <section className="py-10 border-b border-[var(--color-border)]">
      {/* 섹션 헤더 */}
      <h2 className="text-xs font-semibold tracking-[3px] uppercase text-[var(--color-muted)] mb-6">
        COORDINATE MAP
      </h2>

      {/* 축 이름 리스트 - 항상 선명 (블러 위) */}
      <div className="flex flex-wrap gap-3 mb-6">
        {content.axes.map((axis) => (
          <span
            key={axis}
            className="px-3 py-1 text-xs font-medium tracking-[1px] border border-[var(--color-border)] rounded-full"
          >
            {axis}
          </span>
        ))}
      </div>

      {/* 상세 수치 영역 - 잠금 시 블러 처리 */}
      <div className={locked ? "select-none" : ""}>
        <div className="relative">
          {/* 좌표 그리드 */}
          <div className="grid grid-cols-2 gap-4">
            {content.axes.map((axis, idx) => (
              <div
                key={axis}
                className="p-4 border border-[var(--color-border)] rounded-lg"
              >
                {/* 축 라벨 + 설명 */}
                <p className="text-xs text-[var(--color-muted)] mb-0.5">
                  {axis}
                </p>
                {AXIS_DESCRIPTIONS[axis] && (
                  <p className="text-[11px] text-[var(--color-muted)] opacity-40 mb-2">
                    {AXIS_DESCRIPTIONS[axis]}
                  </p>
                )}
                {/* 현재 위치 바 */}
                <div className="h-2 bg-[var(--color-border)] rounded-full mb-2 overflow-hidden">
                  <div
                    className="h-full bg-[var(--color-fg)] rounded-full transition-all duration-500"
                    style={{ width: `${(content.position[idx] ?? 0) * 100}%` }}
                  />
                </div>
                {/* 수치 표시 */}
                <div className="flex justify-between text-xs">
                  <span>
                    현재{" "}
                    <span className="font-bold">
                      {((content.position[idx] ?? 0) * 100).toFixed(0)}
                    </span>
                  </span>
                  <span className="text-[var(--color-muted)]">
                    목표{" "}
                    <span className="font-medium">
                      {((content.target[idx] ?? 0) * 100).toFixed(0)}
                    </span>
                  </span>
                </div>
              </div>
            ))}
          </div>

          {/* 블러 오버레이 - 수치 영역만 덮음 */}
          {locked && (
            <div className="absolute inset-0 blur-overlay blur-fade-out rounded-lg" />
          )}
        </div>
      </div>
    </section>
  );
}
