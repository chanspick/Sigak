// SIGAK — Shared tokens + primitives
// Loaded first. Exposes: color tokens, PhotoPlaceholder, SageFrame, TopBar, ReportMeta

const SAGE       = '#8B9D7D';
const SAGE_SOFT  = '#E8ECE2';
const INK        = '#0F0F0E';
const PAPER      = '#FAFAF7';
const LINE       = 'rgba(15,15,14,0.12)';
const LINE_STRONG= 'rgba(15,15,14,0.22)';
const MUTE       = 'rgba(15,15,14,0.55)';
const MUTE_2     = 'rgba(15,15,14,0.38)';

// Medal palette (v1.1)
const GOLD_STROKE   = '#B8A05E';
const GOLD_FILL     = '#E8DCC0';
const SILVER_STROKE = '#9A9A96';
const SILVER_FILL   = '#E8E8E4';
const BRONZE_STROKE = '#8B6F47';
const BRONZE_FILL   = '#D4B896';

// ─── PhotoPlaceholder ──────────────────────────────────────
// Deterministic, paper-toned, diagonal-stripe placeholder so we never
// need stock imagery. Different seeds → slight tonal variation.
function PhotoPlaceholder({ seed = 0, ratio = '4/5' }) {
  const tones = [
    { bg: '#E6E2D6', stripe: 'rgba(15,15,14,0.06)' },
    { bg: '#D8DDD0', stripe: 'rgba(15,15,14,0.07)' },
    { bg: '#E2DCD0', stripe: 'rgba(15,15,14,0.05)' },
    { bg: '#D0D6CB', stripe: 'rgba(15,15,14,0.06)' },
    { bg: '#E8E3D5', stripe: 'rgba(15,15,14,0.05)' },
    { bg: '#DCD7C8', stripe: 'rgba(15,15,14,0.06)' },
    { bg: '#D5DBCC', stripe: 'rgba(15,15,14,0.06)' },
    { bg: '#E0DBCD', stripe: 'rgba(15,15,14,0.07)' },
    { bg: '#D2D8C9', stripe: 'rgba(15,15,14,0.06)' },
    { bg: '#E4DFD1', stripe: 'rgba(15,15,14,0.05)' },
    { bg: '#DEDACA', stripe: 'rgba(15,15,14,0.06)' },
  ];
  const t = tones[((seed % tones.length) + tones.length) % tones.length];
  const angle = 28 + ((seed * 13) % 24); // 28..52deg
  return (
    <div style={{
      width: '100%',
      aspectRatio: ratio,
      background: `repeating-linear-gradient(${angle}deg, ${t.bg} 0 14px, ${t.stripe} 14px 15px)`,
      position: 'relative',
      overflow: 'hidden',
    }} />
  );
}

// ─── SageFrame ─────────────────────────────────────────────
// Thin sage corner ticks around content. Used sparingly — only for the
// "selected" hero moment.
function SageFrame({ children, inset = 8, tick = 14, weight = 1 }) {
  const corner = (style) => ({
    position: 'absolute', width: tick, height: tick,
    ...style,
  });
  return (
    <div style={{ position: 'relative', padding: inset }}>
      {/* TL */}
      <div style={corner({ left: 0, top: 0 })}>
        <div style={{ position: 'absolute', left: 0, top: 0, width: tick, height: weight, background: SAGE }} />
        <div style={{ position: 'absolute', left: 0, top: 0, width: weight, height: tick, background: SAGE }} />
      </div>
      {/* TR */}
      <div style={corner({ right: 0, top: 0 })}>
        <div style={{ position: 'absolute', right: 0, top: 0, width: tick, height: weight, background: SAGE }} />
        <div style={{ position: 'absolute', right: 0, top: 0, width: weight, height: tick, background: SAGE }} />
      </div>
      {/* BL */}
      <div style={corner({ left: 0, bottom: 0 })}>
        <div style={{ position: 'absolute', left: 0, bottom: 0, width: tick, height: weight, background: SAGE }} />
        <div style={{ position: 'absolute', left: 0, bottom: 0, width: weight, height: tick, background: SAGE }} />
      </div>
      {/* BR */}
      <div style={corner({ right: 0, bottom: 0 })}>
        <div style={{ position: 'absolute', right: 0, bottom: 0, width: tick, height: weight, background: SAGE }} />
        <div style={{ position: 'absolute', right: 0, bottom: 0, width: weight, height: tick, background: SAGE }} />
      </div>
      <div style={{ position: 'relative' }}>{children}</div>
    </div>
  );
}

// ─── TopBar (legacy v0.3, used by Upload / Counterfactual / Archive) ─
function TopBar({ tokens = 12 }) {
  return (
    <div style={{
      display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      padding: '62px 20px 12px',
      background: PAPER,
      borderBottom: `0.5px solid ${LINE}`,
    }}>
      <div style={{
        fontFamily: 'Inter, system-ui', fontSize: 11, fontWeight: 500,
        letterSpacing: '0.24em', color: INK,
      }}>SIGAK</div>
      <div style={{
        display: 'flex', alignItems: 'center', gap: 7,
        padding: '5px 10px 5px 8px',
        border: `0.5px solid ${INK}`,
        borderRadius: 999,
      }}>
        <div style={{ position: 'relative', width: 11, height: 11 }}>
          <div style={{ position: 'absolute', inset: 0, borderRadius: '50%', border: `1px solid ${INK}` }} />
          <div style={{ position: 'absolute', left: 2.75, top: 2.75, width: 5.5, height: 5.5, borderRadius: '50%', background: SAGE }} />
        </div>
        <div style={{
          fontFamily: 'Inter, system-ui', fontSize: 11, fontWeight: 500,
          letterSpacing: '0.04em', color: INK,
          fontVariantNumeric: 'tabular-nums',
        }}>{tokens}</div>
      </div>
    </div>
  );
}

// ─── ReportMeta (legacy v0.3, used by Upload) ─────────────
function ReportMeta({ kind = 'SESSION', count = 0, countLabel = 'CAND' }) {
  return (
    <div style={{
      display: 'flex', justifyContent: 'space-between', alignItems: 'baseline',
      padding: '14px 20px 0',
    }}>
      <div style={{
        fontFamily: 'ui-monospace, Menlo, monospace', fontSize: 10,
        letterSpacing: '0.14em', color: MUTE, textTransform: 'uppercase',
      }}>{kind} / 2026·04·19</div>
      <div style={{
        fontFamily: 'ui-monospace, Menlo, monospace', fontSize: 10,
        letterSpacing: '0.14em', color: MUTE, textTransform: 'uppercase',
        fontVariantNumeric: 'tabular-nums',
      }}>{String(count).padStart(3,'0')}·{countLabel}</div>
    </div>
  );
}

Object.assign(window, {
  SAGE, SAGE_SOFT, INK, PAPER, LINE, LINE_STRONG, MUTE, MUTE_2,
  GOLD_STROKE, GOLD_FILL, SILVER_STROKE, SILVER_FILL, BRONZE_STROKE, BRONZE_FILL,
  PhotoPlaceholder, SageFrame, TopBar, ReportMeta,
});
