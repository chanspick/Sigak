import { useState, useEffect, useCallback } from "react";

const API = "/api/v1";

/* ─── Mock Data (remove when backend is live) ─── */
const MOCK_QUEUE = [
  { id: "u1", name: "김서연", tier: "basic", status: "booked", booking_date: "2026-04-15", booking_time: "14:00", has_interview: false, has_photos: false, has_report: false },
  { id: "u2", name: "이준혁", tier: "creator", status: "interviewed", booking_date: "2026-04-15", booking_time: "15:00", has_interview: true, has_photos: true, has_report: false },
  { id: "u3", name: "박지민 · 최우진", tier: "wedding", status: "reported", booking_date: "2026-04-16", booking_time: "10:00", has_interview: true, has_photos: true, has_report: true },
  { id: "u4", name: "정하은", tier: "basic", status: "booked", booking_date: "2026-04-16", booking_time: "11:00", has_interview: false, has_photos: false, has_report: false },
  { id: "u5", name: "오민수", tier: "creator", status: "interviewed", booking_date: "2026-04-17", booking_time: "14:00", has_interview: true, has_photos: false, has_report: false },
];

const MOCK_STATS = {
  total_bookings: 12, interviewed: 8, reports_sent: 5, feedbacks_received: 3,
  avg_satisfaction: 4.3, avg_usefulness: 4.1, nps_target: 4.2, nps_met: false,
  b2b_opt_in_count: 2, b2b_opt_in_rate: 66.7, repurchase_rate: 100,
};

const TIER_MAP = { basic: "시선", creator: "Creator", wedding: "Wedding" };
const STATUS_MAP = {
  booked: "예약됨", interviewed: "인터뷰 완료",
  analyzing: "분석 중", reported: "리포트 발송", feedback_done: "피드백 완료",
};
const STATUS_ORDER = ["booked", "interviewed", "analyzing", "reported", "feedback_done"];

/* ─── QUESTIONS ─── */
const CORE_QUESTIONS = [
  { key: "self_perception", label: "자기 인식", placeholder: "본인이 생각하는 자기 이미지는? (주변에서 뭐라고 하는지도)", rows: 3 },
  { key: "desired_image", label: "추구미", placeholder: "되고 싶은 이미지? 자유롭게 표현 (\"뉴진스 같은데 좀 더 성숙\")", rows: 3 },
  { key: "reference_celebs", label: "레퍼런스 셀럽", placeholder: "닮고 싶은 / 닮았다는 말 듣는 셀럽 (여러 명 OK)", rows: 2 },
  { key: "style_keywords", label: "스타일 키워드", placeholder: "본인 스타일을 키워드로? (시크, 캐주얼, 모던 등)", rows: 2 },
  { key: "current_concerns", label: "현재 고민", placeholder: "외모에서 바꾸고 싶은 점은?", rows: 3 },
  { key: "daily_routine", label: "일상 루틴", placeholder: "평소 메이크업/스타일링 루틴 (안 하면 안 한다고)", rows: 2 },
];

const WEDDING_QUESTIONS = [
  { key: "wedding_concept", label: "웨딩 컨셉", placeholder: "원하는 웨딩 분위기/컨셉?", rows: 2 },
  { key: "dress_preference", label: "드레스 선호", placeholder: "드레스 라인 선호? (A라인, 머메이드 등)", rows: 2 },
];

const CREATOR_QUESTIONS = [
  { key: "content_style", label: "콘텐츠 스타일", placeholder: "콘텐츠 장르/분위기?", rows: 2 },
  { key: "target_audience", label: "타겟 시청자", placeholder: "타겟 시청자층은?", rows: 2 },
  { key: "brand_tone", label: "채널 톤", placeholder: "채널이 추구하는 톤/이미지?", rows: 2 },
];


export default function App() {
  const [view, setView] = useState("queue"); // queue | entry | stats
  const [queue, setQueue] = useState(MOCK_QUEUE);
  const [stats, setStats] = useState(MOCK_STATS);
  const [selectedUser, setSelectedUser] = useState(null);

  const openEntry = (user) => { setSelectedUser(user); setView("entry"); };
  const backToQueue = () => { setView("queue"); setSelectedUser(null); };

  return (
    <div style={S.root}>
      <style>{CSS}</style>

      {/* ── NAV ── */}
      <nav style={S.nav}>
        <span style={S.logo}>SIGAK</span>
        <span style={S.navSub}>INTERVIEWER DASHBOARD</span>
        <div style={{ flex: 1 }} />
        <button style={{ ...S.navTab, opacity: view === "queue" ? 1 : 0.4 }} onClick={() => setView("queue")}>대기열</button>
        <button style={{ ...S.navTab, opacity: view === "stats" ? 1 : 0.4 }} onClick={() => setView("stats")}>지표</button>
      </nav>

      <div style={S.container}>
        {view === "queue" && <QueueView queue={queue} onSelect={openEntry} />}
        {view === "entry" && selectedUser && <EntryView user={selectedUser} onBack={backToQueue} />}
        {view === "stats" && <StatsView stats={stats} />}
      </div>
    </div>
  );
}


/* ─── QUEUE VIEW ─── */
function QueueView({ queue, onSelect }) {
  const groups = {};
  queue.forEach(u => {
    const d = u.booking_date;
    if (!groups[d]) groups[d] = [];
    groups[d].push(u);
  });

  return (
    <div>
      <h2 style={S.pageTitle}>대기열</h2>
      <p style={S.pageSub}>인터뷰 예정 및 진행 중인 유저</p>
      <div style={S.rule} />
      {Object.entries(groups).map(([date, users]) => (
        <div key={date}>
          <p style={S.dateLabel}>{date.replace("2026-", "")}</p>
          {users.map(u => (
            <div key={u.id} style={S.queueRow} onClick={() => onSelect(u)}>
              <div style={S.queueLeft}>
                <span style={S.queueName}>{u.name}</span>
                <span style={S.queueMeta}>{TIER_MAP[u.tier]} · {u.booking_time}</span>
              </div>
              <div style={S.queueRight}>
                <span style={{
                  ...S.statusBadge,
                  background: u.status === "booked" ? "rgba(0,0,0,0.06)" :
                              u.status === "reported" ? "rgba(0,0,0,0.85)" : "rgba(0,0,0,0.12)",
                  color: u.status === "reported" ? "#F3F0EB" : "#000",
                }}>{STATUS_MAP[u.status]}</span>
                <div style={S.dots}>
                  <span style={{ ...S.dot, background: u.has_interview ? "#000" : "rgba(0,0,0,0.1)" }} title="인터뷰" />
                  <span style={{ ...S.dot, background: u.has_photos ? "#000" : "rgba(0,0,0,0.1)" }} title="사진" />
                  <span style={{ ...S.dot, background: u.has_report ? "#000" : "rgba(0,0,0,0.1)" }} title="리포트" />
                </div>
              </div>
            </div>
          ))}
          <div style={S.rule} />
        </div>
      ))}
    </div>
  );
}


/* ─── ENTRY VIEW (Interview Data Input) ─── */
function EntryView({ user, onBack }) {
  const [form, setForm] = useState({});
  const [photos, setPhotos] = useState([]);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  const set = (key, val) => setForm(f => ({ ...f, [key]: val }));

  const tierQuestions = user.tier === "wedding" ? WEDDING_QUESTIONS
    : user.tier === "creator" ? CREATOR_QUESTIONS : [];

  const allQuestions = [...CORE_QUESTIONS, ...tierQuestions];

  const filledCount = allQuestions.filter(q => form[q.key]?.trim()).length;
  const progress = Math.round((filledCount / allQuestions.length) * 100);

  const handleSave = async () => {
    setSaving(true);
    // POST /api/v1/interview/{user.id}
    // POST /api/v1/photos/{user.id} (if photos)
    await new Promise(r => setTimeout(r, 1200));
    setSaving(false);
    setSaved(true);
  };

  const handleAnalyze = async () => {
    setSaving(true);
    // POST /api/v1/analyze/{user.id}
    await new Promise(r => setTimeout(r, 2000));
    setSaving(false);
    alert("분석 완료 — 리포트 생성됨");
  };

  return (
    <div>
      <button style={S.backBtn} onClick={onBack}>← 대기열</button>

      <div style={S.entryHeader}>
        <div>
          <h2 style={S.pageTitle}>{user.name}</h2>
          <p style={S.pageSub}>{TIER_MAP[user.tier]} · {user.booking_date.replace("2026-", "")} {user.booking_time}</p>
        </div>
        <div style={S.progressWrap}>
          <span style={S.progressText}>{progress}%</span>
          <div style={S.progressBar}>
            <div style={{ ...S.progressFill, width: `${progress}%` }} />
          </div>
        </div>
      </div>

      <div style={S.rule} />

      {/* Questions */}
      <div style={S.formSection}>
        <p style={S.sectionLabel}>인터뷰 응답</p>
        {allQuestions.map(q => (
          <div key={q.key} style={S.field}>
            <label style={S.fieldLabel}>{q.label}</label>
            <textarea
              style={S.textarea}
              rows={q.rows}
              placeholder={q.placeholder}
              value={form[q.key] || ""}
              onChange={e => set(q.key, e.target.value)}
            />
          </div>
        ))}
      </div>

      <div style={S.rule} />

      {/* Notes */}
      <div style={S.formSection}>
        <p style={S.sectionLabel}>알바 메모</p>
        <textarea
          style={S.textarea}
          rows={4}
          placeholder="인터뷰 중 특이사항, 분위기, 추가 관찰 사항"
          value={form.raw_notes || ""}
          onChange={e => set("raw_notes", e.target.value)}
        />
      </div>

      <div style={S.rule} />

      {/* Photo upload */}
      <div style={S.formSection}>
        <p style={S.sectionLabel}>사진 업로드</p>
        <p style={S.fieldHint}>정면 1장 + 45도 측면 2장 권장</p>
        <input
          type="file"
          accept="image/*"
          multiple
          onChange={e => setPhotos([...e.target.files])}
          style={S.fileInput}
        />
        {photos.length > 0 && (
          <p style={S.fieldHint}>{photos.length}장 선택됨</p>
        )}
      </div>

      <div style={S.rule} />

      {/* Actions */}
      <div style={S.actions}>
        {!saved ? (
          <button style={S.primaryBtn} onClick={handleSave} disabled={saving || filledCount === 0}>
            {saving ? "저장 중..." : "인터뷰 데이터 저장"}
          </button>
        ) : (
          <button style={S.primaryBtn} onClick={handleAnalyze} disabled={saving}>
            {saving ? "분석 중..." : "→ 분석 파이프라인 실행"}
          </button>
        )}
      </div>
    </div>
  );
}


/* ─── STATS VIEW (Hypothesis Validation) ─── */
function StatsView({ stats }) {
  return (
    <div>
      <h2 style={S.pageTitle}>가설 검증 지표</h2>
      <p style={S.pageSub}>트랙아웃 2주 스프린트 대시보드</p>
      <div style={S.rule} />

      {/* H1: Market */}
      <div style={S.statsSection}>
        <p style={S.sectionLabel}>H1 — MARKET</p>
        <div style={S.statsGrid}>
          <StatCard label="총 예약" value={stats.total_bookings} unit="건" />
          <StatCard label="인터뷰 완료" value={stats.interviewed} unit="건" />
          <StatCard label="리포트 발송" value={stats.reports_sent} unit="건" />
        </div>
      </div>

      {/* H2: Product */}
      <div style={S.statsSection}>
        <p style={S.sectionLabel}>H2 — PRODUCT</p>
        <div style={S.statsGrid}>
          <StatCard label="만족도 평균" value={stats.avg_satisfaction} unit="/ 5"
            alert={stats.avg_satisfaction < 4.2} />
          <StatCard label="유용성 평균" value={stats.avg_usefulness} unit="/ 5"
            target="목표 4.2" alert={stats.avg_usefulness < 4.2} />
          <StatCard label="피드백 수집" value={stats.feedbacks_received} unit="건" />
        </div>
      </div>

      {/* H4: Growth */}
      <div style={S.statsSection}>
        <p style={S.sectionLabel}>H4 — GROWTH</p>
        <div style={S.statsGrid}>
          <StatCard label="B2B Opt-in" value={stats.b2b_opt_in_rate} unit="%" />
          <StatCard label="재구매 의향" value={stats.repurchase_rate} unit="%" />
        </div>
      </div>
    </div>
  );
}

function StatCard({ label, value, unit, target, alert }) {
  return (
    <div style={S.statCard}>
      <p style={S.statLabel}>{label}</p>
      <p style={{ ...S.statValue, color: alert ? "#A32D2D" : "#000" }}>
        {typeof value === "number" && value % 1 !== 0 ? value.toFixed(1) : value}
        <span style={S.statUnit}>{unit}</span>
      </p>
      {target && <p style={S.statTarget}>{target}</p>}
    </div>
  );
}


/* ─── STYLES ─── */
const S = {
  root: {
    background: "#F3F0EB", color: "#000", minHeight: "100vh",
    fontFamily: "'Pretendard Variable', Pretendard, -apple-system, sans-serif",
  },
  nav: {
    position: "sticky", top: 0, zIndex: 100,
    display: "flex", alignItems: "center", gap: 16,
    padding: "0 40px", height: 56,
    background: "#000", color: "#F3F0EB",
  },
  logo: { fontSize: 12, fontWeight: 700, letterSpacing: 5 },
  navSub: { fontSize: 10, fontWeight: 500, letterSpacing: 2.5, opacity: 0.4 },
  navTab: {
    background: "none", border: "none", color: "#F3F0EB",
    fontSize: 11, fontWeight: 600, letterSpacing: 1.5,
    cursor: "pointer", padding: "8px 16px", transition: "opacity 0.2s",
  },
  container: { maxWidth: 720, margin: "0 auto", padding: "32px 40px 80px" },
  pageTitle: {
    fontFamily: "'Noto Serif KR', serif",
    fontSize: "clamp(22px, 3vw, 30px)", fontWeight: 400, lineHeight: 1.3,
  },
  pageSub: { fontSize: 13, opacity: 0.4, marginTop: 6 },
  rule: { height: 1, background: "#000", opacity: 0.08, margin: "24px 0" },
  dateLabel: { fontSize: 11, fontWeight: 600, letterSpacing: 1.5, opacity: 0.3, marginBottom: 10 },
  queueRow: {
    display: "flex", justifyContent: "space-between", alignItems: "center",
    padding: "14px 0", cursor: "pointer", transition: "opacity 0.15s",
  },
  queueLeft: { display: "flex", flexDirection: "column", gap: 4 },
  queueName: { fontSize: 15, fontWeight: 600 },
  queueMeta: { fontSize: 12, opacity: 0.4 },
  queueRight: { display: "flex", alignItems: "center", gap: 12 },
  statusBadge: {
    fontSize: 10, fontWeight: 600, letterSpacing: 0.5,
    padding: "4px 10px", borderRadius: 4,
  },
  dots: { display: "flex", gap: 4 },
  dot: { width: 8, height: 8, borderRadius: "50%", transition: "background 0.2s" },
  backBtn: {
    background: "none", border: "none", fontSize: 13, fontWeight: 500,
    cursor: "pointer", opacity: 0.5, padding: 0, marginBottom: 24,
    fontFamily: "'Pretendard Variable', sans-serif",
  },
  entryHeader: {
    display: "flex", justifyContent: "space-between", alignItems: "flex-end",
  },
  progressWrap: { textAlign: "right" },
  progressText: { fontSize: 11, fontWeight: 600, opacity: 0.4, letterSpacing: 1 },
  progressBar: {
    width: 120, height: 4, background: "rgba(0,0,0,0.06)",
    borderRadius: 2, marginTop: 6, overflow: "hidden",
  },
  progressFill: {
    height: "100%", background: "#000", borderRadius: 2,
    transition: "width 0.3s ease",
  },
  formSection: { padding: "4px 0" },
  sectionLabel: {
    fontSize: 10, fontWeight: 700, letterSpacing: 2.5,
    opacity: 0.3, marginBottom: 16, textTransform: "uppercase",
  },
  field: { marginBottom: 20 },
  fieldLabel: {
    display: "block", fontSize: 12, fontWeight: 600,
    letterSpacing: 0.5, opacity: 0.6, marginBottom: 8,
  },
  fieldHint: { fontSize: 11, opacity: 0.3, marginBottom: 8 },
  textarea: {
    width: "100%", padding: "12px 14px",
    fontFamily: "'Pretendard Variable', sans-serif", fontSize: 14, lineHeight: 1.6,
    background: "transparent", border: "1px solid rgba(0,0,0,0.1)",
    outline: "none", resize: "vertical", transition: "border-color 0.2s",
    borderRadius: 0,
  },
  fileInput: { fontSize: 13, marginTop: 4 },
  actions: { padding: "16px 0" },
  primaryBtn: {
    width: "100%", padding: 16,
    fontFamily: "'Pretendard Variable', sans-serif",
    fontSize: 14, fontWeight: 700,
    background: "#000", color: "#F3F0EB",
    border: "none", cursor: "pointer", transition: "opacity 0.2s",
    letterSpacing: 0.5,
  },
  statsSection: { marginBottom: 32 },
  statsGrid: {
    display: "grid", gridTemplateColumns: "repeat(3, 1fr)",
    gap: 0, border: "1px solid rgba(0,0,0,0.08)",
  },
  statCard: {
    padding: "20px 22px",
    borderRight: "1px solid rgba(0,0,0,0.08)",
  },
  statLabel: {
    fontSize: 10, fontWeight: 600, letterSpacing: 1.5,
    opacity: 0.3, marginBottom: 10,
  },
  statValue: {
    fontFamily: "'Noto Serif KR', serif",
    fontSize: "clamp(24px, 3vw, 32px)", fontWeight: 300, lineHeight: 1,
  },
  statUnit: {
    fontFamily: "'Pretendard Variable', sans-serif",
    fontSize: 12, fontWeight: 400, opacity: 0.35, marginLeft: 4,
  },
  statTarget: { fontSize: 10, opacity: 0.3, marginTop: 6 },
};


const CSS = `
@import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable-dynamic-subset.min.css');
@import url('https://fonts.googleapis.com/css2?family=Noto+Serif+KR:wght@200;300;400;600&display=swap');
* { box-sizing: border-box; margin: 0; padding: 0; }
body { background: #F3F0EB; }
::selection { background: #000; color: #F3F0EB; }
textarea:focus { border-color: #000 !important; }
button:disabled { opacity: 0.3; cursor: not-allowed; }
button:hover:not(:disabled) { opacity: 0.8; }
.sigak-stats:last-child { border-right: none; }
`;
