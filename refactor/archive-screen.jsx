// SIGAK — Archive / History Screen (G)
// Longitudinal record. Observational tone, no value judgments.
const { SAGE, SAGE_SOFT, INK, PAPER, LINE, LINE_STRONG, MUTE, MUTE_2,
        PhotoPlaceholder, SageFrame, TopBar } = window;

// ─── Report meta ─────────────────────────────────────────────
function ArchiveMeta({ count = 14 }) {
  return (
    <div style={{
      display: 'flex', justifyContent: 'space-between', alignItems: 'baseline',
      padding: '18px 20px 0',
    }}>
      <div style={{
        fontFamily: 'ui-monospace, Menlo, monospace', fontSize: 10,
        letterSpacing: '0.14em', color: MUTE, textTransform: 'uppercase',
      }}>ARCHIVE / 2026·04·19</div>
      <div style={{
        fontFamily: 'ui-monospace, Menlo, monospace', fontSize: 10,
        letterSpacing: '0.14em', color: MUTE, textTransform: 'uppercase',
      }}>{String(count).padStart(3,'0')}·SESSIONS</div>
    </div>
  );
}

function ArchiveHeadline({ count = 14 }) {
  return (
    <div style={{ padding: '14px 20px 22px' }}>
      <div style={{
        fontFamily: 'Pretendard, system-ui', fontSize: 10, fontWeight: 500,
        letterSpacing: '0.14em', color: SAGE, textTransform: 'uppercase',
        marginBottom: 10,
      }}>ARCHIVE — 지난 기록</div>

      <div style={{
        fontFamily: 'Pretendard, system-ui', fontSize: 22, fontWeight: 500,
        lineHeight: 1.35, letterSpacing: '-0.01em', color: INK, textWrap: 'pretty',
      }}>
        지난 {count}회의<br/>
        진단이 그린<br/>
        당신의 <span style={{ fontStyle: 'italic', fontFamily: '"Noto Serif KR", serif', fontWeight: 400 }}>궤적</span>.
      </div>
      <div style={{
        marginTop: 12,
        fontFamily: 'Pretendard, system-ui', fontSize: 12, fontWeight: 400,
        lineHeight: 1.6, color: MUTE, letterSpacing: '-0.005em',
      }}>
        Shape · Volume · Age 3축의<br/>평균 이동을 추적합니다.
      </div>
    </div>
  );
}

// ─── § 01 Trajectory — SVG line chart ──────────────────────
// 14 sessions; per-axis series (0..100)
const SERIES = {
  SHAPE: [62, 65, 63, 68, 70, 66, 72, 74, 71, 75, 76, 79, 78, 82],
  VOLUME: [70, 68, 71, 72, 69, 73, 74, 72, 76, 75, 78, 79, 77, 79],
  AGE:   [74, 75, 73, 76, 77, 75, 78, 78, 80, 81, 82, 80, 83, 84],
};

function TrajectoryChart() {
  const axes = ['SHAPE', 'VOLUME', 'AGE'];
  const [active, setActive] = React.useState('SHAPE');
  const [overlay, setOverlay] = React.useState(false);

  const W = 340, H = 140, padX = 6, padY = 12;
  const n = SERIES.SHAPE.length;

  const xFor = (i) => padX + (W - padX * 2) * (i / (n - 1));
  const yFor = (v) => padY + (H - padY * 2) * (1 - (v - 50) / 50); // 50..100 → bottom..top

  const buildPath = (series) => series.map((v, i) => `${i === 0 ? 'M' : 'L'}${xFor(i).toFixed(1)},${yFor(v).toFixed(1)}`).join(' ');

  const colorFor = (k) => k === 'SHAPE' ? SAGE : k === 'VOLUME' ? INK : MUTE_2;

  const activeData = SERIES[active];
  const startV = activeData[0];
  const endV = activeData[n - 1];
  const delta = endV - startV;
  const maxIdx = activeData.indexOf(Math.max(...activeData));
  const minIdx = activeData.indexOf(Math.min(...activeData));

  return (
    <div style={{ padding: '20px 20px 22px', borderTop: `0.5px solid ${LINE}` }}>
      <div style={{
        display: 'flex', justifyContent: 'space-between', alignItems: 'baseline',
        marginBottom: 14,
      }}>
        <div style={{
          fontFamily: 'Inter, system-ui', fontSize: 10, fontWeight: 500,
          letterSpacing: '0.16em', color: INK, textTransform: 'uppercase',
          whiteSpace: 'nowrap',
        }}>§ 01 — TRAJECTORY</div>
        <div style={{
          fontFamily: 'ui-monospace, Menlo, monospace', fontSize: 10,
          letterSpacing: '0.1em', color: MUTE,
        }}>N·14</div>
      </div>

      {/* axis tabs */}
      <div style={{ display: 'flex', gap: 0, marginBottom: 14, border: `0.5px solid ${LINE_STRONG}` }}>
        {axes.map((a, i) => (
          <button key={a} onClick={() => setActive(a)} style={{
            flex: 1, padding: '8px 0', background: active === a ? INK : PAPER,
            color: active === a ? PAPER : INK,
            border: 'none',
            borderLeft: i === 0 ? 'none' : `0.5px solid ${LINE_STRONG}`,
            fontFamily: 'Inter, system-ui', fontSize: 10, fontWeight: 500,
            letterSpacing: '0.14em', cursor: 'pointer',
          }}>{a}</button>
        ))}
        <button onClick={() => setOverlay(o => !o)} style={{
          padding: '8px 12px', background: overlay ? SAGE_SOFT : PAPER,
          border: 'none', borderLeft: `0.5px solid ${LINE_STRONG}`,
          fontFamily: 'ui-monospace, Menlo, monospace', fontSize: 10,
          letterSpacing: '0.1em', color: overlay ? SAGE : MUTE, cursor: 'pointer',
        }}>ALL</button>
      </div>

      {/* chart */}
      <div style={{ position: 'relative', border: `0.5px solid ${LINE}`, background: PAPER }}>
        <svg width="100%" viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none" style={{ display: 'block' }}>
          {/* horizontal gridlines at 60/70/80/90 */}
          {[60, 70, 80, 90].map(v => (
            <line key={v} x1={padX} x2={W - padX} y1={yFor(v)} y2={yFor(v)}
              stroke="rgba(15,15,14,0.06)" strokeWidth="0.5" />
          ))}
          {/* 14 vertical ticks */}
          {SERIES.SHAPE.map((_, i) => (
            <line key={i} x1={xFor(i)} x2={xFor(i)} y1={H - padY} y2={H - padY + 3}
              stroke="rgba(15,15,14,0.2)" strokeWidth="0.5" />
          ))}

          {/* overlay series */}
          {overlay && axes.filter(a => a !== active).map(a => (
            <path key={a} d={buildPath(SERIES[a])}
              stroke={colorFor(a)} strokeOpacity="0.35"
              strokeWidth="1" fill="none" strokeLinejoin="round" strokeLinecap="round" />
          ))}

          {/* active series */}
          <path d={buildPath(activeData)}
            stroke={colorFor(active)} strokeWidth="1.25"
            fill="none" strokeLinejoin="round" strokeLinecap="round" />

          {/* max/min markers */}
          <circle cx={xFor(maxIdx)} cy={yFor(activeData[maxIdx])} r="2.5"
            fill={PAPER} stroke={colorFor(active)} strokeWidth="1" />
          <circle cx={xFor(minIdx)} cy={yFor(activeData[minIdx])} r="2"
            fill={PAPER} stroke={MUTE} strokeWidth="0.75" />

          {/* start + end dots (end filled) */}
          <circle cx={xFor(0)} cy={yFor(activeData[0])} r="2"
            fill={PAPER} stroke={MUTE} strokeWidth="0.75" />
          <circle cx={xFor(n-1)} cy={yFor(activeData[n-1])} r="3"
            fill={colorFor(active)} />
        </svg>

        {/* corner ticks monospace */}
        <div style={{
          position: 'absolute', left: 6, top: 6,
          fontFamily: 'ui-monospace, Menlo, monospace', fontSize: 9,
          letterSpacing: '0.12em', color: MUTE_2,
        }}>100</div>
        <div style={{
          position: 'absolute', left: 6, bottom: 6,
          fontFamily: 'ui-monospace, Menlo, monospace', fontSize: 9,
          letterSpacing: '0.12em', color: MUTE_2,
        }}>50</div>
        <div style={{
          position: 'absolute', right: 6, bottom: 6,
          fontFamily: 'ui-monospace, Menlo, monospace', fontSize: 9,
          letterSpacing: '0.12em', color: MUTE_2,
        }}>NOW</div>
        <div style={{
          position: 'absolute', left: 6, bottom: 18,
          fontFamily: 'ui-monospace, Menlo, monospace', fontSize: 9,
          letterSpacing: '0.12em', color: MUTE_2,
        }}>−90d</div>
      </div>

      {/* readout below chart */}
      <div style={{
        marginTop: 14,
        display: 'grid', gridTemplateColumns: '1fr auto', gap: 12, alignItems: 'center',
      }}>
        <div style={{
          fontFamily: 'Pretendard, system-ui', fontSize: 12, fontWeight: 400,
          color: INK, letterSpacing: '-0.005em', lineHeight: 1.55,
        }}>
          최근 30일 <span style={{ fontFamily: 'Inter, system-ui', fontWeight: 500 }}>{active}</span> {delta >= 0 ? '+' : '−'}{Math.abs(delta)}<br/>
          <span style={{ color: MUTE }}>
            {active === 'SHAPE'  && '모던 쪽 이동 감지'}
            {active === 'VOLUME' && '부피 축 안정'}
            {active === 'AGE'    && '나이감 상향 이동'}
          </span>
        </div>
        <div style={{
          fontFamily: 'ui-monospace, Menlo, monospace', fontSize: 11,
          color: INK, letterSpacing: '0.08em',
          padding: '6px 10px',
          border: `0.5px solid ${delta >= 0 ? SAGE : INK}`,
          background: delta >= 0 ? SAGE_SOFT : PAPER,
          fontVariantNumeric: 'tabular-nums',
        }}>Δ {delta >= 0 ? '+' : '−'}{Math.abs(delta)}</div>
      </div>
    </div>
  );
}

// ─── § 02 Sessions list ────────────────────────────────────
const SESSIONS = [
  { date: '2026·04·19', doy: '019', score: 82, seed: 0, axis: 'Shape', delta: '+4' },
  { date: '2026·04·12', doy: '018', score: 78, seed: 3, axis: 'Age',   delta: '+3' },
  { date: '2026·04·05', doy: '017', score: 76, seed: 2, axis: 'Volume',delta: '+1' },
  { date: '2026·03·29', doy: '016', score: 74, seed: 4, axis: 'Shape', delta: '+2' },
  { date: '2026·03·22', doy: '015', score: 71, seed: 1, axis: 'Shape', delta: '−1' },
];

function SessionsList() {
  return (
    <div style={{ padding: '20px 20px 16px', borderTop: `0.5px solid ${LINE}` }}>
      <div style={{
        display: 'flex', justifyContent: 'space-between', alignItems: 'baseline',
        marginBottom: 14,
      }}>
        <div style={{
          fontFamily: 'Inter, system-ui', fontSize: 10, fontWeight: 500,
          letterSpacing: '0.16em', color: INK, textTransform: 'uppercase',
          whiteSpace: 'nowrap',
        }}>§ 02 — SESSIONS</div>
        <div style={{
          fontFamily: 'ui-monospace, Menlo, monospace', fontSize: 10,
          letterSpacing: '0.1em', color: MUTE,
        }}>05 / 14</div>
      </div>

      <div>
        {SESSIONS.map((s, i) => (
          <div key={s.date} style={{
            display: 'grid',
            gridTemplateColumns: '64px 40px 1fr auto',
            gap: 12, alignItems: 'center',
            padding: '12px 0',
            borderBottom: `0.5px solid ${LINE}`,
          }}>
            {/* date + doy */}
            <div>
              <div style={{
                fontFamily: 'ui-monospace, Menlo, monospace', fontSize: 10,
                letterSpacing: '0.1em', color: INK,
              }}>{s.date.slice(5)}</div>
              <div style={{
                fontFamily: 'ui-monospace, Menlo, monospace', fontSize: 9,
                letterSpacing: '0.12em', color: MUTE_2, marginTop: 2,
              }}>/{s.doy}</div>
            </div>

            {/* thumbnail 40x48 */}
            <div style={{ width: 40 }}>
              <PhotoPlaceholder seed={s.seed} ratio="5/6" />
            </div>

            {/* score + axis note */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
              <div style={{ display: 'flex', alignItems: 'baseline', gap: 6 }}>
                <div style={{
                  fontFamily: 'Inter, system-ui', fontSize: 20, fontWeight: 400,
                  color: INK, letterSpacing: '-0.02em', lineHeight: 1,
                  fontVariantNumeric: 'tabular-nums',
                }}>{s.score}</div>
                <div style={{
                  fontFamily: 'Inter, system-ui', fontSize: 9, fontWeight: 500,
                  letterSpacing: '0.14em', color: MUTE_2,
                }}>/100</div>
              </div>
              <div style={{
                fontFamily: 'Pretendard, system-ui', fontSize: 11, fontWeight: 400,
                color: MUTE, letterSpacing: '-0.005em',
              }}>
                <span style={{ fontFamily: 'Inter, system-ui', fontWeight: 500, color: INK }}>{s.axis}</span> {s.delta}
              </div>
            </div>

            {/* see link */}
            <div style={{
              fontFamily: 'Inter, system-ui', fontSize: 10, fontWeight: 500,
              letterSpacing: '0.16em', color: SAGE, textTransform: 'uppercase',
              cursor: 'pointer',
            }}>SEE ↗</div>
          </div>
        ))}
      </div>

      <div style={{
        padding: '14px 0 4px',
        fontFamily: 'Inter, system-ui', fontSize: 10, fontWeight: 500,
        letterSpacing: '0.14em', color: MUTE, textTransform: 'uppercase',
        cursor: 'pointer',
      }}>+ 9개 더 보기</div>
    </div>
  );
}

// ─── § 03 AIM Drift — 3 sparklines ──────────────────────────
const AIM_DRIFT = {
  '내추럴': [3.8, 3.5, 3.6, 3.2, 3.4, 3.1, 2.9, 3.0, 2.8, 2.7, 2.8, 2.6, 2.5, 2.4],
  '모던':   [4.9, 4.7, 4.8, 4.5, 4.3, 4.1, 4.0, 3.7, 3.5, 3.2, 3.0, 2.8, 2.6, 2.3],
  '큐트':   [3.0, 3.2, 3.1, 3.4, 3.3, 3.5, 3.4, 3.6, 3.8, 3.7, 3.9, 4.0, 4.1, 4.2],
};

function Sparkline({ data, highlight }) {
  const w = 96, h = 28, p = 2;
  const min = Math.min(...data), max = Math.max(...data);
  const range = Math.max(0.1, max - min);
  const pts = data.map((v, i) => {
    const x = p + (w - p*2) * (i / (data.length - 1));
    const y = p + (h - p*2) * ((v - min) / range); // lower distance = higher y visually (flipped: closer=up)
    return [x, h - y + p/2];
  });
  const d = pts.map(([x,y], i) => `${i === 0 ? 'M' : 'L'}${x.toFixed(1)},${y.toFixed(1)}`).join(' ');
  const [ex, ey] = pts[pts.length - 1];
  const [sx, sy] = pts[0];
  return (
    <svg width="100%" viewBox={`0 0 ${w} ${h}`} preserveAspectRatio="none" style={{ display: 'block' }}>
      <path d={d} stroke={highlight ? SAGE : INK} strokeWidth="1" fill="none" strokeLinejoin="round" strokeLinecap="round" />
      <circle cx={sx} cy={sy} r="1.25" fill={PAPER} stroke={MUTE} strokeWidth="0.5" />
      <circle cx={ex} cy={ey} r="2" fill={highlight ? SAGE : INK} />
    </svg>
  );
}

function AimDrift() {
  // "closer" = lower distance value; "nearest" = smallest end value
  const aims = Object.entries(AIM_DRIFT).map(([k, series]) => ({
    k, series,
    start: series[0], end: series[series.length - 1],
    delta: series[series.length - 1] - series[0],
  }));
  const nearest = aims.reduce((a, b) => (a.end < b.end ? a : b));

  return (
    <div style={{ padding: '20px 20px 20px', borderTop: `0.5px solid ${LINE}` }}>
      <div style={{
        display: 'flex', justifyContent: 'space-between', alignItems: 'baseline',
        marginBottom: 14,
      }}>
        <div style={{
          fontFamily: 'Inter, system-ui', fontSize: 10, fontWeight: 500,
          letterSpacing: '0.16em', color: INK, textTransform: 'uppercase',
          whiteSpace: 'nowrap',
        }}>§ 03 — AIM DRIFT</div>
        <div style={{
          fontFamily: 'ui-monospace, Menlo, monospace', fontSize: 10,
          letterSpacing: '0.1em', color: MUTE,
        }}>DIST · 90d</div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 8 }}>
        {aims.map(a => {
          const highlight = a.k === nearest.k;
          return (
            <div key={a.k} style={{
              padding: 10,
              border: `0.5px solid ${highlight ? SAGE : LINE_STRONG}`,
              background: highlight ? SAGE_SOFT : PAPER,
            }}>
              <div style={{
                fontFamily: 'Pretendard, system-ui', fontSize: 11, fontWeight: 500,
                color: INK, letterSpacing: '-0.005em', marginBottom: 4,
              }}>{a.k}</div>
              <div style={{ height: 28, marginBottom: 6 }}>
                <Sparkline data={a.series} highlight={highlight} />
              </div>
              <div style={{
                display: 'flex', justifyContent: 'space-between', alignItems: 'baseline',
                fontFamily: 'ui-monospace, Menlo, monospace', fontSize: 10,
                letterSpacing: '0.08em',
              }}>
                <span style={{ color: MUTE_2 }}>{a.start.toFixed(1)}</span>
                <span style={{ color: INK }}>{a.end.toFixed(1)}</span>
              </div>
            </div>
          );
        })}
      </div>

      <div style={{
        marginTop: 14,
        padding: '10px 12px',
        background: SAGE_SOFT,
        border: `0.5px solid ${SAGE}`,
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
      }}>
        <div style={{
          fontFamily: 'Pretendard, system-ui', fontSize: 12, fontWeight: 400,
          color: INK, letterSpacing: '-0.005em',
        }}>
          가장 가까워진 추구미 <span style={{ fontFamily: 'Inter, system-ui', fontWeight: 500 }}>{nearest.k}</span>
        </div>
        <div style={{
          fontFamily: 'ui-monospace, Menlo, monospace', fontSize: 11,
          color: INK, letterSpacing: '0.08em',
        }}>−{Math.abs(nearest.delta).toFixed(1)}</div>
      </div>
    </div>
  );
}

// ─── Footer CTA ─────────────────────────────────────────────
function ArchiveFooter() {
  return (
    <div>
      <div style={{
        padding: '18px 20px 12px',
        borderTop: `0.5px solid ${LINE}`,
      }}>
        <button style={{
          width: '100%', height: 54,
          background: INK, color: PAPER, border: 'none',
          borderRadius: 12, cursor: 'pointer',
          fontFamily: 'Pretendard, system-ui', fontSize: 14, fontWeight: 500,
          letterSpacing: '-0.005em',
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          padding: '0 20px',
        }}>
          <span>새 판정 시작</span>
          <span style={{
            fontFamily: 'Inter, system-ui', fontSize: 18, color: SAGE,
          }}>→</span>
        </button>
      </div>
      <div style={{
        padding: '0 20px 28px',
        fontFamily: 'ui-monospace, Menlo, monospace', fontSize: 10,
        letterSpacing: '0.12em', color: MUTE_2, textTransform: 'uppercase',
      }}>FREE · 오늘 1회 남음</div>
    </div>
  );
}

function ArchiveScreen() {
  return (
    <div style={{
      background: PAPER, minHeight: '100%',
      fontFamily: 'Pretendard, -apple-system, system-ui, sans-serif',
      color: INK, paddingBottom: 20,
    }}>
      <TopBar tokens={9} />
      <ArchiveMeta count={14} />
      <ArchiveHeadline count={14} />
      <TrajectoryChart />
      <SessionsList />
      <AimDrift />
      <ArchiveFooter />
    </div>
  );
}

Object.assign(window, { ArchiveScreen });
