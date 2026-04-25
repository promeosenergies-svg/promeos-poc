/**
 * PROMEOS — SolHero
 *
 * Card "Sol propose" signature éditoriale : chip pulse + title + description
 * + 3 metrics horizontales mono + CTA primaire agentique + CTA secondaire ghost.
 *
 * Source maquette : .sol-hero / .sol-chip-inline / .sol-hero-title / .sol-hero-metrics
 */
import { useEffect, useMemo, useState } from 'react';

// Anime un nombre de 0 → target en `duration` ms avec ease-out cubic.
// Respecte prefers-reduced-motion (résultat instantané).
// Robuste : si la valeur affichée n'est pas parseable (ex "—" ou "aujourd'hui"),
// retourne la valeur d'origine sans tenter d'animation.
function useCountUpDisplay(displayValue, duration = 900) {
  const target = useMemo(() => {
    const str = String(displayValue ?? '');
    // Match leading number (avec espaces FR / nbsp / dot / virgule)
    const m = str.match(/(-?[\d  \s.,]+)/);
    if (!m) return null;
    const numStr = m[1].replace(/[\s  ]/g, '').replace(',', '.');
    let parsed;
    if (/^-?\d+\.\d+$/.test(numStr)) {
      parsed = parseFloat(numStr);
    } else {
      parsed = parseFloat(numStr.replace(/\./g, ''));
    }
    return isNaN(parsed) ? null : parsed;
  }, [displayValue]);

  const [progress, setProgress] = useState(target == null ? 1 : 0);

  useEffect(() => {
    if (target == null) {
      setProgress(1);
      return;
    }
    const reduce =
      typeof window !== 'undefined' &&
      window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (reduce) {
      setProgress(1);
      return;
    }
    setProgress(0);
    const start = performance.now();
    let raf;
    const step = (now) => {
      const t = Math.min((now - start) / duration, 1);
      const eased = 1 - Math.pow(1 - t, 3);
      setProgress(eased);
      if (t < 1) raf = requestAnimationFrame(step);
    };
    raf = requestAnimationFrame(step);
    return () => raf && cancelAnimationFrame(raf);
  }, [target, duration]);

  if (target == null || progress >= 1) return displayValue;
  const animated = target * progress;
  // Reformate en mimant le format d'origine
  const str = String(displayValue);
  const m = str.match(/^([-\d  \s.,]+)(.*)$/);
  if (!m) return displayValue;
  const rest = m[2];
  const hasThousand = /[  \s]/.test(m[1]);
  const decimals = (m[1].match(/[.,](\d+)$/) || [])[1]?.length || 0;
  const num = hasThousand
    ? Math.round(animated).toLocaleString('fr-FR')
    : decimals > 0
      ? animated.toFixed(decimals)
      : Math.round(animated).toString();
  return num + rest;
}

function MetricValue({ value }) {
  const animated = useCountUpDisplay(value);
  return (
    <span style={{ fontVariantNumeric: 'tabular-nums' }}>{animated}</span>
  );
}

export default function SolHero({
  chip = 'Sol propose · action agentique',
  title,
  description,
  metrics = [],
  primaryLabel = "Voir ce que j'enverrai",
  onPrimary,
  secondaryLabel = 'Plus tard',
  onSecondary,
}) {
  if (!title) return null;

  return (
    <section
      style={{
        background: 'var(--sol-bg-paper)',
        border: '1px solid var(--sol-ink-200)',
        borderLeft: '3px solid var(--sol-calme-fg)',
        padding: '18px 22px',
        borderRadius: 8,
        margin: '20px 0 24px',
        display: 'grid',
        gridTemplateColumns: '1fr auto',
        gap: 24,
        alignItems: 'center',
        boxShadow: '0 1px 2px rgba(15, 23, 42, 0.04)',
        // Entry animation : slide-up + fade-in 600ms ease-out signature.
        // Respecte prefers-reduced-motion via règle globale (index.css:1043).
        animation: 'slideInUp 600ms cubic-bezier(0.16, 1, 0.3, 1) backwards',
      }}
    >
      <div>
        <div
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: 6,
            fontFamily: 'var(--sol-font-mono)',
            fontSize: 9.5,
            textTransform: 'uppercase',
            letterSpacing: '0.1em',
            color: 'var(--sol-calme-fg)',
            fontWeight: 600,
            background: 'var(--sol-calme-bg)',
            padding: '3px 8px',
            borderRadius: 99,
            marginBottom: 10,
          }}
        >
          <span
            style={{
              width: 5,
              height: 5,
              borderRadius: '50%',
              background: 'var(--sol-calme-fg)',
              animation: 'sol-pulse 3s ease-in-out infinite',
            }}
          />
          {chip}
        </div>

        <h3
          style={{
            fontFamily: 'var(--sol-font-body)',
            fontSize: 16,
            fontWeight: 600,
            color: 'var(--sol-ink-900)',
            marginBottom: 6,
            lineHeight: 1.3,
            letterSpacing: '-0.015em',
          }}
        >
          {title}
        </h3>

        {description && (
          <p
            style={{
              fontSize: 13,
              color: 'var(--sol-ink-500)',
              lineHeight: 1.55,
              maxWidth: 520,
              margin: 0,
            }}
          >
            {description}
          </p>
        )}

        {metrics.length > 0 && (
          <div style={{ display: 'flex', gap: 18, marginTop: 10 }}>
            {metrics.map((m, i) => (
              <div key={m.label ?? m.value ?? i}>
                <div
                  style={{
                    fontFamily: 'var(--sol-font-mono)',
                    fontSize: 15,
                    fontWeight: 600,
                    color: 'var(--sol-ink-900)',
                    fontVariantNumeric: 'tabular-nums',
                  }}
                >
                  <MetricValue value={m.value} />
                </div>
                <div
                  style={{
                    fontSize: 10,
                    color: 'var(--sol-ink-500)',
                    textTransform: 'uppercase',
                    letterSpacing: '0.08em',
                  }}
                >
                  {m.label}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 8, minWidth: 180 }}>
        {onPrimary && (
          <button
            type="button"
            onClick={onPrimary}
            style={{
              fontFamily: 'var(--sol-font-body)',
              fontSize: 13,
              fontWeight: 500,
              padding: '8px 14px',
              borderRadius: 6,
              border: '1px solid transparent',
              background: 'var(--sol-calme-fg)',
              color: 'white',
              cursor: 'pointer',
              whiteSpace: 'nowrap',
              transition: 'all 120ms ease',
            }}
            onMouseEnter={(e) => (e.currentTarget.style.background = '#245047')}
            onMouseLeave={(e) => (e.currentTarget.style.background = 'var(--sol-calme-fg)')}
          >
            {primaryLabel}
          </button>
        )}
        {onSecondary && (
          <button
            type="button"
            onClick={onSecondary}
            style={{
              fontFamily: 'var(--sol-font-body)',
              fontSize: 13,
              fontWeight: 500,
              padding: '8px 14px',
              borderRadius: 6,
              border: '1px solid transparent',
              background: 'transparent',
              color: 'var(--sol-ink-500)',
              cursor: 'pointer',
              whiteSpace: 'nowrap',
            }}
            onMouseEnter={(e) => (e.currentTarget.style.color = 'var(--sol-ink-900)')}
            onMouseLeave={(e) => (e.currentTarget.style.color = 'var(--sol-ink-500)')}
          >
            {secondaryLabel}
          </button>
        )}
      </div>
    </section>
  );
}
