"use client";

// 캐스팅 풀 대시보드 — 에이전시용 B2B 페이지
// 옵트인한 유저 목록 조회 + 프로필 상세 + 매칭 요청

import { useState, useEffect, useCallback } from "react";
import { useSearchParams } from "next/navigation";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "";

// --- 타입 정의 ---

interface Coordinates {
  shape: number;
  volume: number;
  age: number;
}

interface CastingUser {
  user_id: string;
  name: string;
  gender: string;
  face_shape: string;
  image_type: string;
  coordinates: Coordinates;
  skin_tone: string;
  opted_at: string;
  report_id: string;
  has_photo: boolean;
  photo_url: string | null;
}

interface CastingUserDetail extends CastingUser {
  sections: Record<string, unknown>;
  overlay_url: string | null;
}

interface PoolResponse {
  total: number;
  users: CastingUser[];
}

// --- 좌표축 라벨 ---

const AXIS_LABELS: Record<keyof Coordinates, string> = {
  shape: "골격",
  volume: "존재감",
  age: "무드",
};

// --- 얼굴형 옵션 ---

const FACE_SHAPE_OPTIONS = [
  "얼굴형 전체",
  "둥근형",
  "타원형",
  "긴형",
  "각진형",
  "역삼각형",
  "하트형",
  "다이아몬드형",
];

// --- 좌표 바 컴포넌트 ---

function CoordinateBar({
  axis,
  value,
  compact = false,
}: {
  axis: keyof Coordinates;
  value: number;
  compact?: boolean;
}) {
  // -1 ~ +1 → 0% ~ 100% (undefined/NaN 방어)
  const safeValue = typeof value === "number" && !isNaN(value) ? value : 0;
  const pct = ((safeValue + 1) / 2) * 100;

  if (compact) {
    return (
      <div className="flex items-center gap-1.5">
        <span className="text-[10px] text-[var(--color-muted)] w-10 shrink-0">
          {AXIS_LABELS[axis]}
        </span>
        <div className="w-20 h-[6px] bg-black/[0.06] relative">
          <div
            className="absolute inset-y-0 left-0 bg-[var(--color-fg)]"
            style={{ width: `${pct}%` }}
          />
        </div>
        <span className="text-[10px] text-[var(--color-muted)] w-8 text-right tabular-nums">
          {safeValue > 0 ? "+" : ""}
          {safeValue.toFixed(1)}
        </span>
      </div>
    );
  }

  return (
    <div className="flex items-center gap-3">
      <span className="text-[11px] text-[var(--color-muted)] w-12 shrink-0">
        {AXIS_LABELS[axis]}
      </span>
      <div className="flex-1 h-[6px] bg-black/[0.06] relative">
        <div
          className="absolute inset-y-0 left-0 bg-[var(--color-fg)]"
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="text-[11px] text-[var(--color-muted)] w-10 text-right tabular-nums">
        {value > 0 ? "+" : ""}
        {value.toFixed(1)}
      </span>
    </div>
  );
}

// --- 프로필 모달 ---

function CastingProfileModal({
  userId,
  adminKey,
  onClose,
}: {
  userId: string;
  adminKey: string;
  onClose: () => void;
}) {
  const [detail, setDetail] = useState<CastingUserDetail | null>(null);
  const [loading, setLoading] = useState(true);

  // 매칭 요청 폼 상태
  const [agencyName, setAgencyName] = useState("");
  const [purpose, setPurpose] = useState("");
  const [fee, setFee] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [matchSent, setMatchSent] = useState(false);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await fetch(
          `${API_URL}/api/v1/admin/casting-pool/${userId}?admin_key=${encodeURIComponent(adminKey)}`
        );
        if (!res.ok) return;
        const data = await res.json();
        if (!cancelled) setDetail(data);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [userId, adminKey]);

  async function handleMatchRequest() {
    if (!agencyName.trim()) return;
    setSubmitting(true);
    try {
      const params = new URLSearchParams({
        admin_key: adminKey,
        agency_name: agencyName.trim(),
        purpose: purpose.trim(),
        fee: fee.trim(),
      });
      const res = await fetch(
        `${API_URL}/api/v1/admin/casting-pool/${userId}/match-request?${params}`,
        { method: "POST" }
      );
      if (res.ok) {
        setMatchSent(true);
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div
      className="fixed inset-0 z-[200] flex items-center justify-center bg-black/50"
      onClick={onClose}
    >
      <div
        className="bg-[var(--color-bg)] w-full max-w-lg max-h-[90vh] overflow-y-auto mx-4"
        onClick={(e) => e.stopPropagation()}
      >
        {/* 헤더 */}
        <div className="flex items-center justify-between px-6 py-5 border-b border-[var(--color-border)]">
          <span className="text-xs font-bold tracking-[3px]">프로필</span>
          <button
            onClick={onClose}
            className="text-[11px] text-[var(--color-muted)] hover:text-[var(--color-fg)] transition-colors cursor-pointer"
          >
            닫기
          </button>
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-20">
            <div className="w-5 h-5 border-2 border-[var(--color-border)] border-t-[var(--color-fg)] animate-spin" />
          </div>
        ) : detail ? (
          <div className="px-6 py-5">
            {/* 사진 */}
            {(detail.photo_url || detail.overlay_url) && (
              <div className="flex gap-3 mb-6">
                {detail.photo_url && (
                  <div className="w-28 h-36 bg-black/[0.04] overflow-hidden">
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img src={`${API_URL}${detail.photo_url}`} alt="원본" className="w-full h-full object-cover" />
                  </div>
                )}
                {detail.overlay_url && (
                  <div className="w-28 h-36 bg-black/[0.04] overflow-hidden">
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img src={`${API_URL}${detail.overlay_url}`} alt="오버레이" className="w-full h-full object-cover" />
                  </div>
                )}
              </div>
            )}

            {/* 이름 + 성별 */}
            <div className="flex items-baseline gap-3 mb-6">
              <span className="text-lg font-bold">{detail.name}</span>
              <span className="text-[11px] text-[var(--color-muted)]">
                {detail.gender === "female" ? "여성" : detail.gender === "male" ? "남성" : detail.gender}
              </span>
            </div>

            {/* 요약 테이블 */}
            <div className="space-y-3 mb-6">
              {[
                { label: "얼굴형", value: detail.face_shape },
                { label: "이미지 유형", value: detail.image_type },
                { label: "피부톤", value: detail.skin_tone },
              ].map((row) => (
                <div key={row.label} className="flex items-center justify-between">
                  <span className="text-[11px] text-[var(--color-muted)]">{row.label}</span>
                  <span className="text-[12px] font-medium">{row.value}</span>
                </div>
              ))}
            </div>

            {/* 좌표 바 */}
            <div className="space-y-2 mb-6">
              {(Object.keys(AXIS_LABELS) as (keyof Coordinates)[]).map((axis) => (
                <CoordinateBar
                  key={axis}
                  axis={axis}
                  value={detail.coordinates[axis]}
                />
              ))}
            </div>

            {/* 매칭 요청 */}
            <div className="border-t border-[var(--color-border)] pt-5">
              <span className="text-[10px] font-medium tracking-[2px] text-[var(--color-muted)] uppercase">
                매칭 요청
              </span>

              {matchSent ? (
                <div className="mt-4 space-y-1">
                  <p className="text-[13px] font-medium">
                    매칭 요청이 전송되었습니다
                  </p>
                  <p className="text-[11px] text-[var(--color-muted)]">
                    SIGAK 팀이 확인 후 연락드리겠습니다
                  </p>
                </div>
              ) : (
                <div className="mt-4 space-y-3">
                  <div>
                    <label className="block text-[11px] text-[var(--color-muted)] mb-1">
                      에이전시/제작사명
                    </label>
                    <input
                      type="text"
                      value={agencyName}
                      onChange={(e) => setAgencyName(e.target.value)}
                      className="w-full h-10 px-3 text-[13px] bg-transparent border border-[var(--color-border)] outline-none focus:border-[var(--color-fg)] transition-colors"
                    />
                  </div>
                  <div>
                    <label className="block text-[11px] text-[var(--color-muted)] mb-1">
                      목적 (캐스팅/광고/모델 등)
                    </label>
                    <input
                      type="text"
                      value={purpose}
                      onChange={(e) => setPurpose(e.target.value)}
                      className="w-full h-10 px-3 text-[13px] bg-transparent border border-[var(--color-border)] outline-none focus:border-[var(--color-fg)] transition-colors"
                    />
                  </div>
                  <div>
                    <label className="block text-[11px] text-[var(--color-muted)] mb-1">
                      회당 출연료 (예: ₩500,000)
                    </label>
                    <input
                      type="text"
                      value={fee}
                      onChange={(e) => setFee(e.target.value)}
                      placeholder="₩"
                      className="w-full h-10 px-3 text-[13px] bg-transparent border border-[var(--color-border)] outline-none focus:border-[var(--color-fg)] transition-colors"
                    />
                  </div>
                  <button
                    onClick={handleMatchRequest}
                    disabled={!agencyName.trim() || submitting}
                    className="w-full h-10 text-[12px] font-medium tracking-[1px] bg-[var(--color-fg)] text-[var(--color-bg)] disabled:opacity-30 transition-opacity cursor-pointer disabled:cursor-not-allowed"
                  >
                    {submitting ? "전송 중..." : "매칭 요청 보내기"}
                  </button>
                </div>
              )}
            </div>
          </div>
        ) : (
          <div className="flex items-center justify-center py-20 text-[12px] text-[var(--color-muted)]">
            프로필을 불러올 수 없습니다
          </div>
        )}
      </div>
    </div>
  );
}

// --- 메인 컴포넌트 ---

export function CastingPool() {
  const searchParams = useSearchParams();

  // 인증 상태
  const [adminKey, setAdminKey] = useState("");
  const [keyInput, setKeyInput] = useState("");
  const [authenticated, setAuthenticated] = useState(false);
  const [authError, setAuthError] = useState(false);

  // 데이터 상태
  const [users, setUsers] = useState<CastingUser[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [faceShape, setFaceShape] = useState("얼굴형 전체");

  // 탭: pool | matches
  const [tab, setTab] = useState<"pool" | "matches">("pool");

  // 매칭 현황
  interface MatchItem {
    notification_id: string;
    user_id: string;
    user_name: string;
    agency_name: string;
    purpose: string;
    fee: string;
    response: string;
    requested_at: string;
    responded_at: string | null;
  }
  const [matches, setMatches] = useState<MatchItem[]>([]);
  const [matchFilter, setMatchFilter] = useState("all");
  const [matchLoading, setMatchLoading] = useState(false);

  // 모달 상태
  const [selectedUserId, setSelectedUserId] = useState<string | null>(null);

  // URL 파라미터에서 키 읽기
  useEffect(() => {
    const key = searchParams.get("key");
    if (key) {
      setAdminKey(key);
      setKeyInput(key);
      // 키가 있으면 자동으로 풀 조회 시도
      fetchPool(key, "얼굴형 전체");
    }
  }, [searchParams]);

  const fetchPool = useCallback(
    async (key: string, shape: string) => {
      setLoading(true);
      setAuthError(false);
      try {
        const params = new URLSearchParams({ admin_key: key });
        if (shape !== "얼굴형 전체") {
          params.set("face_shape", shape);
        }
        const res = await fetch(
          `${API_URL}/api/v1/admin/casting-pool?${params}`
        );
        if (res.status === 403) {
          setAuthError(true);
          setAuthenticated(false);
          return;
        }
        if (!res.ok) return;
        const data: PoolResponse = await res.json();
        setUsers(data.users);
        setTotal(data.total);
        setAuthenticated(true);
        setAdminKey(key);
      } finally {
        setLoading(false);
      }
    },
    []
  );

  const fetchMatches = useCallback(async (key: string) => {
    setMatchLoading(true);
    try {
      const res = await fetch(`${API_URL}/api/v1/admin/casting-matches?admin_key=${encodeURIComponent(key)}`);
      if (res.ok) {
        const data = await res.json();
        setMatches(data.matches);
      }
    } finally {
      setMatchLoading(false);
    }
  }, []);

  // 필터 변경 시 재조회
  useEffect(() => {
    if (authenticated && adminKey) {
      fetchPool(adminKey, faceShape);
    }
  }, [faceShape, authenticated, adminKey, fetchPool]);

  // 매칭 탭 전환 시 로드
  useEffect(() => {
    if (tab === "matches" && authenticated && adminKey) {
      fetchMatches(adminKey);
    }
  }, [tab, authenticated, adminKey, fetchMatches]);

  // 키 입력 폼 제출
  function handleKeySubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!keyInput.trim()) return;
    fetchPool(keyInput.trim(), faceShape);
  }

  // --- 로그인 전: 키 입력 화면 ---
  if (!authenticated) {
    return (
      <div className="min-h-screen bg-[var(--color-bg)] flex items-center justify-center">
        <form
          onSubmit={handleKeySubmit}
          className="w-full max-w-xs px-[var(--spacing-page-x-mobile)]"
        >
          <div className="text-center mb-8">
            <p className="text-xs font-bold tracking-[5px]">SIGAK</p>
            <p className="text-[10px] tracking-[2.5px] text-[var(--color-muted)] mt-1">
              CASTING POOL
            </p>
          </div>

          <input
            type="password"
            value={keyInput}
            onChange={(e) => setKeyInput(e.target.value)}
            placeholder="관리자 키를 입력하세요"
            className="w-full h-10 px-3 text-[13px] bg-transparent border border-[var(--color-border)] outline-none focus:border-[var(--color-fg)] transition-colors mb-3"
          />

          {authError && (
            <p className="text-[11px] text-[var(--color-danger)] mb-3">
              유효하지 않은 키입니다
            </p>
          )}

          <button
            type="submit"
            disabled={loading || !keyInput.trim()}
            className="w-full h-10 text-[12px] font-medium tracking-[2px] bg-[var(--color-fg)] text-[var(--color-bg)] disabled:opacity-30 transition-opacity cursor-pointer disabled:cursor-not-allowed"
          >
            {loading ? "확인 중..." : "접속"}
          </button>
        </form>
      </div>
    );
  }

  // --- 로그인 후: 대시보드 ---
  return (
    <div className="min-h-screen bg-[var(--color-bg)]">
      {/* 헤더 */}
      <nav className="sticky top-0 z-[100] flex items-center justify-between px-[var(--spacing-page-x-mobile)] md:px-[var(--spacing-page-x)] h-[60px] bg-[var(--color-fg)] text-[var(--color-bg)]">
        <span className="text-xs font-bold tracking-[5px]">SIGAK</span>
        <div className="flex items-center gap-4">
          <button onClick={() => setTab("pool")} className={`text-[10px] font-medium tracking-[1.5px] transition-opacity cursor-pointer ${tab === "pool" ? "opacity-100" : "opacity-40 hover:opacity-70"}`}>
            POOL
          </button>
          <button onClick={() => setTab("matches")} className={`text-[10px] font-medium tracking-[1.5px] transition-opacity cursor-pointer ${tab === "matches" ? "opacity-100" : "opacity-40 hover:opacity-70"}`}>
            MATCHES
          </button>
        </div>
      </nav>

      {/* 콘텐츠 */}
      <div className="px-[var(--spacing-page-x-mobile)] md:px-[var(--spacing-page-x)] py-8">

        {/* ── MATCHES 탭 ── */}
        {tab === "matches" && (
          <div>
            {/* 필터 */}
            <div className="flex items-center gap-2 mb-6">
              {[
                { key: "all", label: "전체" },
                { key: "pending", label: "대기" },
                { key: "accept", label: "수락" },
                { key: "decline", label: "거절" },
              ].map((f) => (
                <button
                  key={f.key}
                  onClick={() => setMatchFilter(f.key)}
                  className={`px-3 py-1.5 text-[11px] font-medium tracking-[0.5px] border transition-colors cursor-pointer ${
                    matchFilter === f.key
                      ? "border-[var(--color-fg)] bg-[var(--color-fg)] text-[var(--color-bg)]"
                      : "border-[var(--color-border)] text-[var(--color-muted)] hover:border-[var(--color-fg)]"
                  }`}
                >
                  {f.label}
                </button>
              ))}
            </div>

            {matchLoading ? (
              <div className="flex items-center justify-center py-20">
                <div className="w-5 h-5 border-2 border-[var(--color-border)] border-t-[var(--color-fg)] animate-spin" />
              </div>
            ) : matches.filter((m) => matchFilter === "all" || m.response === matchFilter).length === 0 ? (
              <div className="text-center py-20 text-[12px] text-[var(--color-muted)]">
                매칭 요청이 없습니다
              </div>
            ) : (
              <div className="space-y-3">
                {matches
                  .filter((m) => matchFilter === "all" || m.response === matchFilter)
                  .map((m) => (
                    <div key={m.notification_id} className="border border-[var(--color-border)] px-5 py-4">
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-[13px] font-medium">{m.user_name || m.user_id.slice(0, 8)}</span>
                        <span className={`text-[10px] font-bold tracking-[1px] px-2 py-0.5 ${
                          m.response === "accept"
                            ? "bg-green-100 text-green-700"
                            : m.response === "decline"
                              ? "bg-red-50 text-red-500"
                              : "bg-black/[0.06] text-[var(--color-muted)]"
                        }`}>
                          {m.response === "accept" ? "수락" : m.response === "decline" ? "거절" : "대기"}
                        </span>
                      </div>
                      <div className="flex gap-4 text-[11px] text-[var(--color-muted)]">
                        <span>{m.agency_name}</span>
                        {m.purpose && <span>{m.purpose}</span>}
                        {m.fee && <span className="font-medium text-[var(--color-fg)]">{m.fee}</span>}
                      </div>
                      <p className="text-[10px] text-[var(--color-muted)] mt-1.5">
                        {m.requested_at ? new Date(m.requested_at).toLocaleDateString("ko-KR") : ""}
                        {m.responded_at && ` · 응답 ${new Date(m.responded_at).toLocaleDateString("ko-KR")}`}
                      </p>
                    </div>
                  ))}
              </div>
            )}
          </div>
        )}

        {/* ── POOL 탭 ── */}
        {tab === "pool" && <>
        {/* 필터 + 카운트 */}
        <div className="flex items-center justify-between mb-6">
          <select
            value={faceShape}
            onChange={(e) => setFaceShape(e.target.value)}
            className="h-9 px-3 text-[12px] bg-transparent border border-[var(--color-border)] outline-none cursor-pointer appearance-none pr-8"
            style={{
              backgroundImage: `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='10' height='6' viewBox='0 0 10 6'%3E%3Cpath d='M0 0l5 6 5-6z' fill='%23666'/%3E%3C/svg%3E")`,
              backgroundRepeat: "no-repeat",
              backgroundPosition: "right 10px center",
            }}
          >
            {FACE_SHAPE_OPTIONS.map((opt) => (
              <option key={opt} value={opt}>
                {opt}
              </option>
            ))}
          </select>

          <span className="text-[11px] text-[var(--color-muted)]">
            {total}명 등록
          </span>
        </div>

        {/* 로딩 */}
        {loading && (
          <div className="flex items-center justify-center py-20">
            <div className="w-5 h-5 border-2 border-[var(--color-border)] border-t-[var(--color-fg)] animate-spin" />
          </div>
        )}

        {/* 빈 상태 */}
        {!loading && users.length === 0 && (
          <div className="flex items-center justify-center py-20">
            <span className="text-[12px] text-[var(--color-muted)]">
              등록된 유저가 없습니다
            </span>
          </div>
        )}

        {/* 유저 카드 목록 */}
        {!loading && users.length > 0 && (
          <div className="space-y-3">
            {users.map((user) => (
              <button
                key={user.user_id}
                onClick={() => setSelectedUserId(user.user_id)}
                className="w-full text-left border border-[var(--color-border)] bg-transparent px-5 py-4 hover:border-[var(--color-fg)] transition-colors cursor-pointer"
              >
                <div className="flex gap-4">
                  {/* 썸네일 */}
                  {user.photo_url && (
                    <div className="w-16 h-20 shrink-0 bg-black/[0.04] overflow-hidden">
                      {/* eslint-disable-next-line @next/next/no-img-element */}
                      <img
                        src={`${API_URL}${user.photo_url}`}
                        alt=""
                        className="w-full h-full object-cover"
                      />
                    </div>
                  )}
                  <div className="flex-1 min-w-0">
                    {/* 1행: 이름 + 날짜 */}
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-[13px] font-medium">{user.name}</span>
                      <span className="text-[10px] text-[var(--color-muted)]">
                        {new Date(user.opted_at).toLocaleDateString("ko-KR")}
                      </span>
                    </div>

                    {/* 2행: 얼굴형 + 피부톤 */}
                    <p className="text-[11px] text-[var(--color-muted)] mb-3">
                      {user.face_shape} · {user.skin_tone}
                    </p>

                    {/* 좌표 바 */}
                    <div className="space-y-1">
                      {(Object.keys(AXIS_LABELS) as (keyof Coordinates)[]).map(
                        (axis) => (
                          <CoordinateBar
                            key={axis}
                            axis={axis}
                            value={user.coordinates[axis]}
                            compact
                          />
                        )
                      )}
                    </div>
                  </div>
                </div>
              </button>
            ))}
          </div>
        )}
        </>}
      </div>

      {/* 프로필 모달 */}
      {selectedUserId && (
        <CastingProfileModal
          userId={selectedUserId}
          adminKey={adminKey}
          onClose={() => setSelectedUserId(null)}
        />
      )}
    </div>
  );
}
