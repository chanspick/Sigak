// SIGAK — Result Screen v1.2
// TONE GUIDE v1.1. Three tier rows uniform (GOLD 1, SILVER 3, BRONZE 5).
// GOLD lightbox + SILVER/BRONZE → smooth scroll + pulse Pro block.
const { SAGE, SAGE_SOFT, INK, PAPER, LINE, MUTE, MUTE_2,
        GOLD_STROKE, GOLD_FILL, SILVER_STROKE, SILVER_FILL,
        BRONZE_STROKE, BRONZE_FILL,
        PhotoPlaceholder, SageFrame } = window;

// ─── Light TopBar ──────────────────────────────────────────
function ResultTopBar({ tokens = 12 }) {
  return (
    <div style={{
      display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      padding: '62px 20px 0',
    }}>
      <button style={{
        width: 24, height: 24, padding: 0, background: 'transparent',
        border: 'none', cursor: 'pointer',
        display: 'flex', alignItems: 'center', justifyContent: 'flex-start',
      }}>
        <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
          <path d="M9 2L4 7l5 5" stroke={INK} strokeWidth="1" strokeLinecap="round" strokeLinejoin="round"/>
        </svg>
      </button>
      <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
        <div style={{ position: 'relative', width: 10, height: 10 }}>
          <div style={{ position: 'absolute', inset: 0, borderRadius: '50%', border: `1px solid ${INK}` }} />
          <div style={{ position: 'absolute', left: 2.5, top: 2.5, width: 5, height: 5, borderRadius: '50%', background: SAGE }} />
        </div>
        <div style={{
          fontFamily: 'Inter, system-ui', fontSize: 11, fontWeight: 400,
          color: INK, letterSpacing: '0.02em',
          fontVariantNumeric: 'tabular-nums',
        }}>{tokens}</div>
      </div>
    </div>
  );
}

function DateLine() {
  return (
    <div style={{
      padding: '26px 20px 0',
      fontFamily: 'Pretendard, system-ui', fontSize: 12, fontWeight: 400,
      color: MUTE, letterSpacing: '-0.005em',
    }}>4월 19일</div>
  );
}

function Headline() {
  return (
    <div style={{ padding: '12px 20px 0' }}>
      <h1 style={{
        margin: 0,
        fontFamily: 'Pretendard, system-ui', fontSize: 34, fontWeight: 500,
        lineHeight: 1.25, letterSpacing: '-0.02em', color: INK,
        textWrap: 'pretty',
      }}>
        이 중에서는,<br/>
        이 한 <span style={{
          fontFamily: '"Noto Serif KR", serif', fontStyle: 'italic',
          fontWeight: 400,
        }}>장</span>.
      </h1>
    </div>
  );
}

// ─── Medal (uniform 14px across all tiers in v1.2) ────────
function Medal({ tier = 'gold' }) {
  const palette = {
    gold:   { stroke: GOLD_STROKE,   fill: GOLD_FILL },
    silver: { stroke: SILVER_STROKE, fill: SILVER_FILL },
    bronze: { stroke: BRONZE_STROKE, fill: BRONZE_FILL },
  }[tier];
  const d = 14;
  const r = (d - 1) / 2;
  return (
    <svg width={d} height={d} viewBox={`0 0 ${d} ${d}`} style={{ display: 'block' }}>
      <circle cx={d/2} cy={d/2} r={r} fill={palette.fill} stroke={palette.stroke} strokeWidth="1" />
    </svg>
  );
}

function MedalLabel({ tier, count }) {
  const labels = { gold: 'GOLD', silver: 'SILVER', bronze: 'BRONZE' };
  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 8,
      lineHeight: 1,
    }}>
      <Medal tier={tier} />
      <span style={{
        fontFamily: 'Inter, system-ui', fontSize: 10, fontWeight: 500,
        letterSpacing: '0.14em', color: INK, textTransform: 'uppercase',
      }}>{labels[tier]}</span>
      {count != null && (
        <span style={{
          fontFamily: 'Inter, system-ui', fontSize: 10, fontWeight: 500,
          letterSpacing: '0.04em', color: MUTE,
          fontVariantNumeric: 'tabular-nums',
        }}>· {count}</span>
      )}
    </div>
  );
}

// ─── Reading ───────────────────────────────────────────────
function Reading() {
  return (
    <div style={{
      padding: '18px 20px 0',
      maxWidth: 280,
      fontFamily: 'Pretendard, system-ui', fontSize: 14, fontWeight: 400,
      lineHeight: 1.7, color: INK, letterSpacing: '-0.005em',
      textWrap: 'pretty',
    }}>
      구도와 표정의 균형이 좋아요.<br/>
      내추럴에 잘 맞고요.
    </div>
  );
}

// ─── Tier rows (GOLD = 1 selected + reading, SILVER/BRONZE = blurred) ──
function GoldRow({ seed, onTap }) {
  const [pressed, setPressed] = React.useState(false);
  return (
    <div style={{ padding: '44px 20px 0' }}>
      <MedalLabel tier="gold" count={1} />
      {/* one cell same width as silver/bronze cell: (402 - 40 - 32)/5 = 66px */}
      <div style={{
        marginTop: 11,
        display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 8,
      }}>
        <div
          onClick={onTap}
          onPointerDown={() => setPressed(true)}
          onPointerUp={() => setPressed(false)}
          onPointerLeave={() => setPressed(false)}
          style={{
            cursor: 'pointer',
            transform: pressed ? 'scale(0.98)' : 'scale(1)',
            transition: 'transform 150ms ease-out',
            transformOrigin: 'center',
          }}>
          <SageFrame inset={5} tick={9} weight={1}>
            <PhotoPlaceholder seed={seed} ratio="1/1" />
          </SageFrame>
        </div>
        {/* 4 empty cells preserve alignment */}
        <div /><div /><div /><div />
      </div>
      <Reading />
    </div>
  );
}

function BlurredCell({ seed, onTap }) {
  const [hot, setHot] = React.useState(false);
  return (
    <div
      onClick={onTap}
      onPointerEnter={() => setHot(true)}
      onPointerLeave={() => setHot(false)}
      onPointerDown={() => setHot(true)}
      onPointerUp={() => setHot(false)}
      style={{
        cursor: 'pointer',
        overflow: 'hidden',
        borderRadius: 2,
        aspectRatio: '1/1',
      }}>
      <div style={{
        width: '100%', height: '100%',
        filter: hot ? 'blur(8px)' : 'blur(10px)',
        transform: 'scale(1.15)',
        transformOrigin: 'center',
        transition: 'filter 200ms ease-out',
      }}>
        <PhotoPlaceholder seed={seed} ratio="1/1" />
      </div>
    </div>
  );
}

function TierRow({ tier, count, seeds, marginTop, onTap }) {
  return (
    <div style={{ padding: `${marginTop}px 20px 0` }}>
      <MedalLabel tier={tier} count={count} />
      <div style={{
        marginTop: 11,
        display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 8,
      }}>
        {Array.from({ length: 5 }, (_, i) => {
          if (i >= count) return <div key={i} />;
          return <BlurredCell key={i} seed={seeds[i]} onTap={onTap} />;
        })}
      </div>
    </div>
  );
}

// ─── Pro Unlock Block (id for scroll target + pulse) ──────
function ProUnlockBlock({ pulseKey }) {
  const ref = React.useRef(null);
  React.useEffect(() => {
    if (!pulseKey || !ref.current) return;
    const el = ref.current;
    el.animate(
      [
        { opacity: 1 },
        { opacity: 0.78 },
        { opacity: 1 },
        { opacity: 0.85 },
        { opacity: 1 },
      ],
      { duration: 900, easing: 'ease-out' }
    );
  }, [pulseKey]);

  return (
    <div id="sigak-pro-block" style={{ padding: '52px 20px 0' }}>
      <div ref={ref} style={{
        background: SAGE_SOFT,
        borderRadius: 10,
        padding: '20px 22px',
        cursor: 'pointer',
      }}>
        <div style={{
          fontFamily: 'Inter, system-ui', fontSize: 10, fontWeight: 500,
          letterSpacing: '0.14em', color: SAGE, textTransform: 'uppercase',
        }}>PRO</div>

        <div style={{
          marginTop: 12,
          fontFamily: 'Pretendard, system-ui', fontSize: 19, fontWeight: 500,
          lineHeight: 1.35, letterSpacing: '-0.015em', color: INK,
          textWrap: 'pretty',
        }}>가려진 것들</div>

        <div style={{
          marginTop: 6,
          fontFamily: 'Pretendard, system-ui', fontSize: 13, fontWeight: 400,
          lineHeight: 1.55, color: INK, letterSpacing: '-0.005em',
        }}>silver, bronze 사진과 전체 진단까지.</div>

        <div style={{
          marginTop: 14,
          display: 'flex', alignItems: 'center', justifyContent: 'flex-end',
          gap: 12,
        }}>
          <span style={{
            fontFamily: 'Inter, system-ui', fontSize: 16, color: INK, lineHeight: 1,
          }}>→</span>
          <span style={{
            display: 'flex', alignItems: 'center', gap: 5,
            fontFamily: 'Inter, system-ui', fontSize: 11, fontWeight: 400,
            color: INK, letterSpacing: '0.02em',
            fontVariantNumeric: 'tabular-nums',
          }}>
            <span style={{ position: 'relative', display: 'inline-block', width: 9, height: 9 }}>
              <span style={{ position: 'absolute', inset: 0, borderRadius: '50%', border: `1px solid ${INK}` }} />
              <span style={{ position: 'absolute', left: 2.25, top: 2.25, width: 4.5, height: 4.5, borderRadius: '50%', background: SAGE }} />
            </span>
            7
          </span>
        </div>
      </div>
    </div>
  );
}

// ─── Footer actions ───────────────────────────────────────
function FooterActions() {
  const items = ['다시 판정', '공유', '저장'];
  return (
    <div style={{
      padding: '52px 20px 32px',
      display: 'flex', gap: 20,
    }}>
      {items.map(t => (
        <div key={t} style={{
          fontFamily: 'Pretendard, system-ui', fontSize: 13, fontWeight: 400,
          color: MUTE, letterSpacing: '-0.005em', cursor: 'pointer',
        }}>{t}</div>
      ))}
    </div>
  );
}

// ─── GOLD lightbox ────────────────────────────────────────
function GoldLightbox({ seed, onClose }) {
  React.useEffect(() => {
    const onKey = (e) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose]);

  return (
    <div
      onClick={onClose}
      style={{
        position: 'absolute', inset: 0,
        background: 'rgba(15,15,14,0.85)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        padding: '40px 24px',
        zIndex: 50,
        animation: 'sigak-fade 220ms ease-out both',
      }}>
      {/* close */}
      <button
        onClick={(e) => { e.stopPropagation(); onClose(); }}
        style={{
          position: 'absolute', top: 56, right: 20,
          width: 32, height: 32, borderRadius: 999,
          background: 'transparent', border: `0.5px solid rgba(250,250,247,0.5)`,
          cursor: 'pointer', padding: 0,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
        }}>
        <svg width="11" height="11" viewBox="0 0 11 11">
          <path d="M1 1l9 9M10 1L1 10" stroke={PAPER} strokeWidth="1" strokeLinecap="round"/>
        </svg>
      </button>

      <div onClick={(e) => e.stopPropagation()} style={{ width: '100%', maxWidth: 320 }}>
        <SageFrame inset={10} tick={16} weight={1}>
          <PhotoPlaceholder seed={seed} ratio="4/5" />
        </SageFrame>
      </div>
    </div>
  );
}

// ─── Composition ───────────────────────────────────────────
function ResultScreen() {
  const [lightbox, setLightbox] = React.useState(false);
  const [pulseKey, setPulseKey] = React.useState(0);

  const goldSeed = 0;
  const silverSeeds = [3, 5, 2];
  const bronzeSeeds = [4, 7, 1, 9, 6];

  const onLockedTap = () => {
    const el = document.getElementById('sigak-pro-block');
    if (el) {
      // smooth scroll within the iOS device viewport (closest scrollable ancestor)
      let scroller = el.parentElement;
      while (scroller && scroller !== document.body) {
        const oy = getComputedStyle(scroller).overflowY;
        if (oy === 'auto' || oy === 'scroll') break;
        scroller = scroller.parentElement;
      }
      if (scroller && scroller !== document.body) {
        const top = el.offsetTop - 80;
        scroller.scrollTo({ top, behavior: 'smooth' });
      } else {
        const r = el.getBoundingClientRect();
        window.scrollTo({ top: window.scrollY + r.top - 80, behavior: 'smooth' });
      }
    }
    setPulseKey(k => k + 1);
  };

  return (
    <div style={{
      position: 'relative',
      background: PAPER, minHeight: '100%',
      fontFamily: 'Pretendard, -apple-system, system-ui, sans-serif',
      color: INK,
    }}>
      <style>{`@keyframes sigak-fade { from { opacity: 0 } to { opacity: 1 } }`}</style>

      <ResultTopBar tokens={12} />
      <DateLine />
      <Headline />
      <GoldRow seed={goldSeed} onTap={() => setLightbox(true)} />
      <TierRow tier="silver" count={3} seeds={silverSeeds} marginTop={36} onTap={onLockedTap} />
      <TierRow tier="bronze" count={5} seeds={bronzeSeeds} marginTop={24} onTap={onLockedTap} />
      <ProUnlockBlock pulseKey={pulseKey} />
      <FooterActions />

      {lightbox && <GoldLightbox seed={goldSeed} onClose={() => setLightbox(false)} />}
    </div>
  );
}

Object.assign(window, { ResultScreen });
