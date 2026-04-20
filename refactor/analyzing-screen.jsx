// SIGAK — Analyzing Screen v0.3 (restored)
// 4-step pipeline, PROGRESS bar, RUN meta, § 01 PIPELINE section,
// "5장의 후보를 진단 중입니다" headline, footer disclaimer.
const { SAGE, SAGE_SOFT, INK, PAPER, LINE, LINE_STRONG, MUTE, MUTE_2,
        TopBar, ReportMeta } = window;

// ─── pipeline definition ──────────────────────────────────
const STEPS = [
  { id: '001', ko: '후보 정렬',     en: 'ORDERING CANDIDATES' },
  { id: '002', ko: '구도 분석',     en: 'COMPOSITION READ'    },
  { id: '003', ko: '표정 해석',     en: 'EXPRESSION READ'     },
  { id: '004', ko: '교차 비교',     en: 'CROSS-COMPARE'       },
];

// ─── small bits ───────────────────────────────────────────
function Dot({ state }) {
  // state: 'done' | 'active' | 'idle'
  if (state === 'done') {
    return (
      <div style={{
        width: 8, height: 8, borderRadius: '50%',
        background: SAGE, flexShrink: 0,
      }} />
    );
  }
  if (state === 'active') {
    return (
      <div style={{
        width: 8, height: 8, borderRadius: '50%',
        border: `1px solid ${SAGE}`,
        background: 'transparent',
        flexShrink: 0,
        animation: 'sigak-active-pulse 1000ms ease-in-out infinite',
      }} />
    );
  }
  return (
    <div style={{
      width: 8, height: 8, borderRadius: '50%',
      border: `1px solid ${LINE_STRONG}`,
      background: 'transparent',
      flexShrink: 0,
    }} />
  );
}

function StepRow({ step, index, state }) {
  const muted = state === 'idle';
  const done  = state === 'done';
  return (
    <div style={{
      display: 'grid',
      gridTemplateColumns: '16px 44px 1fr auto',
      alignItems: 'center',
      gap: 12,
      padding: '13px 0',
      borderBottom: `0.5px solid ${LINE}`,
    }}>
      <Dot state={state} />
      <div style={{
        fontFamily: 'ui-monospace, Menlo, monospace', fontSize: 10,
        letterSpacing: '0.14em', color: muted ? MUTE_2 : MUTE,
        fontVariantNumeric: 'tabular-nums',
      }}>/{step.id}</div>
      <div style={{
        fontFamily: 'Pretendard, system-ui', fontSize: 15,
        fontWeight: done ? 400 : 500,
        letterSpacing: '-0.01em',
        color: muted ? MUTE : INK,
      }}>{step.ko}</div>
      <div style={{
        fontFamily: 'Inter, system-ui', fontSize: 10,
        letterSpacing: '0.14em', color: muted ? MUTE_2 : MUTE,
        textTransform: 'uppercase',
      }}>{step.en}</div>
    </div>
  );
}

function ProgressBar({ pct }) {
  return (
    <div style={{ padding: '0 20px' }}>
      <div style={{
        display: 'flex', justifyContent: 'space-between', alignItems: 'baseline',
        marginBottom: 8,
      }}>
        <div style={{
          fontFamily: 'Inter, system-ui', fontSize: 10, fontWeight: 500,
          letterSpacing: '0.22em', color: MUTE,
        }}>PROGRESS</div>
        <div style={{
          fontFamily: 'ui-monospace, Menlo, monospace', fontSize: 11,
          letterSpacing: '0.04em', color: INK,
          fontVariantNumeric: 'tabular-nums',
        }}>{String(pct).padStart(3, ' ')}%</div>
      </div>
      <div style={{
        width: '100%', height: 2,
        background: 'rgba(15,15,14,0.08)',
      }}>
        <div style={{
          width: `${pct}%`, height: '100%',
          background: SAGE,
          transition: 'width 260ms ease-out',
        }} />
      </div>
    </div>
  );
}

function Section({ id, title, children }) {
  return (
    <div>
      <div style={{
        padding: '0 20px',
        display: 'flex', alignItems: 'baseline', gap: 10,
        marginBottom: 6,
      }}>
        <div style={{
          fontFamily: 'ui-monospace, Menlo, monospace', fontSize: 10,
          letterSpacing: '0.14em', color: MUTE,
        }}>§ {id}</div>
        <div style={{
          fontFamily: 'Inter, system-ui', fontSize: 10, fontWeight: 500,
          letterSpacing: '0.22em', color: INK, textTransform: 'uppercase',
        }}>— {title}</div>
      </div>
      <div style={{ padding: '0 20px' }}>{children}</div>
    </div>
  );
}

// ─── main ─────────────────────────────────────────────────
function AnalyzingScreen() {
  // progress 0 → 100 over ~4.4s, active step advances at 25/50/75/100
  const [pct, setPct] = React.useState(0);
  React.useEffect(() => {
    const start = performance.now();
    const DUR = 4400;
    let raf;
    const tick = (t) => {
      const p = Math.min(1, (t - start) / DUR);
      // ease-out cubic
      const eased = 1 - Math.pow(1 - p, 3);
      setPct(Math.round(eased * 100));
      if (p < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, []);

  const activeIdx = pct >= 100 ? 3 : pct >= 75 ? 3 : pct >= 50 ? 2 : pct >= 25 ? 1 : 0;
  const stateFor = (i) => {
    if (pct >= 100) return 'done';
    if (i < activeIdx) return 'done';
    if (i === activeIdx) return 'active';
    return 'idle';
  };

  return (
    <div style={{
      minHeight: '100%', background: PAPER,
      fontFamily: 'Pretendard, -apple-system, system-ui, sans-serif',
      color: INK,
      paddingBottom: 40,
    }}>
      <style>{`
        @keyframes sigak-active-pulse {
          0%, 100% { opacity: 0.4; }
          50%      { opacity: 1; }
        }
      `}</style>

      <TopBar tokens={12} />
      <ReportMeta kind="RUN" count={5} countLabel="CAND" />

      {/* Headline */}
      <div style={{ padding: '22px 20px 0' }}>
        <h1 style={{
          margin: 0,
          fontFamily: 'Pretendard, system-ui',
          fontSize: 26, fontWeight: 500, lineHeight: 1.3,
          letterSpacing: '-0.02em', color: INK,
          textWrap: 'pretty',
        }}>
          5장의 후보를<br/>
          진단 중입니다.
        </h1>
      </div>

      {/* Progress */}
      <div style={{ padding: '32px 0 0' }}>
        <ProgressBar pct={pct} />
      </div>

      {/* § 01 — PIPELINE */}
      <div style={{ padding: '40px 0 0' }}>
        <Section id="01" title="Pipeline">
          <div>
            {STEPS.map((s, i) => (
              <StepRow key={s.id} step={s} index={i} state={stateFor(i)} />
            ))}
          </div>
        </Section>
      </div>

      {/* Footer disclaimer */}
      <div style={{ padding: '36px 20px 0' }}>
        <div style={{
          fontFamily: 'Pretendard, system-ui', fontSize: 11,
          lineHeight: 1.7, color: MUTE, letterSpacing: '-0.005em',
          textWrap: 'pretty',
        }}>
          SIGAK의 판정은 해석이지 정답이 아닙니다.<br/>
          결과는 당신의 판단을 돕기 위한 참고입니다.
        </div>
      </div>
    </div>
  );
}

Object.assign(window, { AnalyzingScreen });
