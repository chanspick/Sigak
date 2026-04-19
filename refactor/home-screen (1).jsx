// SIGAK — Home Screen v1.1
// TONE GUIDE v1.2. Home = Upload, single screen. No explanatory copy.
// Large centered SIGAK wordmark on top (Home-only). Minimal token counter.
const { SAGE, SAGE_SOFT, INK, PAPER, LINE, LINE_STRONG, MUTE, MUTE_2,
        PhotoPlaceholder, SageFrame } = window;

// ─── TopBar: token counter only (top-right) ───────────────
function HomeTopBar({ tokens = 12 }) {
  return (
    <div style={{
      display: 'flex', alignItems: 'center', justifyContent: 'flex-end',
      padding: '62px 20px 0',
    }}>
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

// ─── Large centered SIGAK wordmark (Home-only) ────────────
function HomeWordmark() {
  return (
    <div style={{
      padding: '26px 20px 0',
      display: 'flex', justifyContent: 'center',
    }}>
      <div style={{
        fontFamily: 'Inter, system-ui',
        fontSize: 22, fontWeight: 500,
        letterSpacing: '0.32em', color: INK,
        // optical balance: tracking pushes the block right
        paddingLeft: '0.32em',
        lineHeight: 1,
      }}>SIGAK</div>
    </div>
  );
}

// ─── Empty dropzone (0 photos) ────────────────────────────
function DropzoneEmpty({ onAdd }) {
  return (
    <div onClick={onAdd} style={{ cursor: 'pointer' }}>
      <SageFrame inset={10} tick={16} weight={1}>
        <div style={{
          aspectRatio: '1/1',
          background: 'transparent',
          display: 'flex', flexDirection: 'column',
          alignItems: 'center', justifyContent: 'center',
        }}>
          {/* plus glyph — single clean + (no decorative ring) */}
          <div style={{ position: 'relative', width: 28, height: 28 }}>
            <div style={{ position: 'absolute', left: 2, top: 13.5, width: 24, height: 1, background: INK }} />
            <div style={{ position: 'absolute', left: 13.5, top: 2, width: 1, height: 24, background: INK }} />
          </div>
          <div style={{ height: 14 }} />
          <div style={{
            fontFamily: 'Pretendard, system-ui', fontSize: 16, fontWeight: 500,
            color: INK, letterSpacing: '-0.005em',
            lineHeight: 1,
          }}>사진 올리기</div>
          <div style={{ height: 10 }} />
          <div style={{
            fontFamily: 'Pretendard, system-ui', fontSize: 11, fontWeight: 400,
            color: MUTE, letterSpacing: '0.01em',
            lineHeight: 1,
          }}>3 ~ 10장</div>
        </div>
      </SageFrame>
    </div>
  );
}

// ─── Filled grid (1..10 photos) ───────────────────────────
function DropzoneGrid({ items, onAdd, onRemove }) {
  const canAdd = items.length < 10;
  return (
    <SageFrame inset={10} tick={16} weight={1}>
      <div style={{
        display: 'flex', flexDirection: 'column',
        gap: 10,
      }}>
        <div style={{
          display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 6,
        }}>
          {items.map((it, i) => (
            <div key={i} style={{ position: 'relative' }}>
              <PhotoPlaceholder seed={it.seed} ratio="1/1" />
              {/* index stamp bottom-left */}
              <div style={{
                position: 'absolute', left: 3, bottom: 3,
                fontFamily: 'Inter, system-ui', fontSize: 9,
                fontVariantNumeric: 'tabular-nums',
                color: MUTE,
                background: 'rgba(250,250,247,0.85)',
                padding: '1px 4px',
                lineHeight: 1.2,
              }}>{String(i + 1).padStart(2, '0')}</div>
              {/* × remove top-right */}
              <button
                onClick={(e) => { e.stopPropagation(); onRemove(i); }}
                style={{
                  position: 'absolute', top: 3, right: 3,
                  width: 18, height: 18, borderRadius: 999,
                  background: INK, border: 'none', cursor: 'pointer',
                  padding: 0,
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                }}>
                <svg width="8" height="8" viewBox="0 0 8 8">
                  <path d="M1 1l6 6M7 1L1 7" stroke={PAPER} strokeWidth="1" strokeLinecap="square"/>
                </svg>
              </button>
            </div>
          ))}
          {canAdd && (
            <div onClick={onAdd} style={{
              cursor: 'pointer',
              aspectRatio: '1/1',
              border: `0.5px dashed ${SAGE}`,
              background: SAGE_SOFT,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
            }}>
              <div style={{ position: 'relative', width: 14, height: 14 }}>
                <div style={{ position: 'absolute', left: 0, top: 6.75, width: 14, height: 0.5, background: SAGE }} />
                <div style={{ position: 'absolute', top: 0, left: 6.75, width: 0.5, height: 14, background: SAGE }} />
              </div>
            </div>
          )}
        </div>

        {/* N / 10 bottom-right */}
        <div style={{
          display: 'flex', justifyContent: 'flex-end',
          fontFamily: 'Pretendard, system-ui', fontSize: 11, fontWeight: 400,
          color: MUTE, fontVariantNumeric: 'tabular-nums',
        }}>{items.length} / 10</div>
      </div>
    </SageFrame>
  );
}

// ─── Hint (only when 1-2 photos) ──────────────────────────
function Hint({ count }) {
  if (count !== 1 && count !== 2) return null;
  return (
    <div style={{
      marginTop: 16,
      fontFamily: 'Pretendard, system-ui', fontSize: 12, fontWeight: 400,
      color: MUTE, letterSpacing: '-0.005em',
    }}>3장부터 시작할 수 있어요</div>
  );
}

// ─── CTA ──────────────────────────────────────────────────
function HomeCTA({ count, onStart }) {
  const ready = count >= 3;
  return (
    <button
      disabled={!ready}
      onClick={ready ? onStart : undefined}
      style={{
        width: '100%', height: 54,
        background: ready ? INK : 'rgba(15,15,14,0.06)',
        color: ready ? PAPER : MUTE_2,
        border: 'none',
        borderRadius: 12,
        fontFamily: 'Pretendard, system-ui', fontSize: 14, fontWeight: 500,
        letterSpacing: '-0.005em',
        cursor: ready ? 'pointer' : 'default',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '0 22px',
      }}>
      <span>{ready ? '어울리는 사진 고르기' : '사진을 3장 이상 올려주세요'}</span>
      {ready && (
        <span style={{
          fontFamily: 'Inter, system-ui', fontSize: 18, color: SAGE, lineHeight: 1,
        }}>→</span>
      )}
    </button>
  );
}

// ─── Composition ──────────────────────────────────────────
function HomeScreen({ initialCount = 0, onStart }) {
  const [items, setItems] = React.useState(
    Array.from({ length: initialCount }, (_, i) => ({ seed: (i * 7 + 3) % 11 }))
  );
  const add = () => {
    if (items.length >= 10) return;
    setItems([...items, { seed: (items.length * 7 + 3) % 11 }]);
  };
  const remove = (i) => setItems(items.filter((_, j) => j !== i));

  return (
    <div style={{
      background: PAPER, minHeight: '100%', height: '100%',
      fontFamily: 'Pretendard, -apple-system, system-ui, sans-serif',
      color: INK,
      display: 'flex', flexDirection: 'column',
    }}>
      <HomeTopBar tokens={12} />
      <HomeWordmark />

      {/* main block */}
      <div style={{
        padding: '28px 20px 0',
      }}>
        {items.length === 0 ? (
          <DropzoneEmpty onAdd={add} />
        ) : (
          <DropzoneGrid items={items} onAdd={add} onRemove={remove} />
        )}
        <Hint count={items.length} />
      </div>

      {/* spacer */}
      <div style={{ flex: 1 }} />

      {/* CTA */}
      <div style={{ padding: '20px 20px 32px' }}>
        <HomeCTA count={items.length} onStart={onStart} />
      </div>
    </div>
  );
}

Object.assign(window, { HomeScreen });
