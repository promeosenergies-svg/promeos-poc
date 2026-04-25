/**
 * PROMEOS — SolTimerail
 *
 * Footer persistant 36px fixe en bas de l'AppShell.
 *
 * Contenu mono 11px :
 *   ● 14 h 32 · HP en cours jusqu'à 22 h  │  sem. 16 · avril 2026
 *   │  Traj. DT 2030 : ────── −12,4 % / −25 %  │  Sol · 3 actions en attente
 *
 * Source maquette : .timerail + .tr-item + .tr-bar + .tr-bar-fill
 *
 * Données : zéro fetch propre — les props viennent de l'AppShell qui lui-même
 * les dérive des contextes existants (ScopeContext, trajectoire DT si
 * disponible dans le contexte, sinon skip).
 */
import { useEffect, useState } from 'react';

function useCurrentTime(intervalSec = 60) {
  const [now, setNow] = useState(() => new Date());
  useEffect(() => {
    const id = setInterval(() => setNow(new Date()), intervalSec * 1000);
    return () => clearInterval(id);
  }, [intervalSec]);
  return now;
}

function formatHour(d) {
  const h = d.getHours();
  const m = d.getMinutes();
  return `${String(h).padStart(2, '0')} h ${String(m).padStart(2, '0')}`;
}

function detectTariffSlot(d) {
  const h = d.getHours();
  // Convention HP France tertiaire : 06:00 → 22:00
  if (h >= 6 && h < 22) return { slot: 'HP', color: 'var(--sol-hph-fg)', until: 22 };
  return { slot: 'HC', color: 'var(--sol-hch-fg)', until: h >= 22 ? 24 : 6 };
}

function formatWeekMonth(d) {
  const months = [
    'janvier',
    'février',
    'mars',
    'avril',
    'mai',
    'juin',
    'juillet',
    'août',
    'septembre',
    'octobre',
    'novembre',
    'décembre',
  ];
  // ISO week — minimal calc (lundi = début, semaine 1 = 1er jeudi)
  const d2 = new Date(Date.UTC(d.getFullYear(), d.getMonth(), d.getDate()));
  const dayNum = d2.getUTCDay() || 7;
  d2.setUTCDate(d2.getUTCDate() + 4 - dayNum);
  const yearStart = new Date(Date.UTC(d2.getUTCFullYear(), 0, 1));
  const week = Math.ceil(((d2 - yearStart) / 86400000 + 1) / 7);
  return `sem. ${week} · ${months[d.getMonth()]}`;
}

export default function SolTimerail({ trajectory, solBadge }) {
  const now = useCurrentTime(60);
  const tariff = detectTariffSlot(now);
  const hourStr = formatHour(now);

  return (
    <div
      role="contentinfo"
      aria-label="Barre temporelle Sol"
      style={{
        position: 'fixed',
        bottom: 0,
        left: 0,
        right: 0,
        height: 36,
        zIndex: 40,
        background: 'var(--sol-bg-panel)',
        borderTop: '1px solid var(--sol-rule)',
        padding: '0 40px',
        display: 'flex',
        alignItems: 'center',
        gap: 20,
        fontSize: 11,
        color: 'var(--sol-ink-500)',
        fontFamily: 'var(--sol-font-mono)',
        fontVariantNumeric: 'tabular-nums',
      }}
    >
      {/* Live time + tariff slot */}
      <span style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <span
          aria-hidden="true"
          style={{
            width: 6,
            height: 6,
            borderRadius: '50%',
            background: 'var(--sol-calme-fg)',
            animation: 'sol-pulse 3s ease-in-out infinite',
          }}
        />
        <span>
          {hourStr} · <strong style={{ color: tariff.color }}>{tariff.slot}</strong> en cours ·
          jusqu'à {tariff.until} h
        </span>
      </span>

      <Separator />

      <span>{formatWeekMonth(now)}</span>

      {trajectory && (
        <>
          <Separator />
          <span
            style={{
              flex: 1,
              display: 'flex',
              alignItems: 'center',
              gap: 10,
              minWidth: 0,
            }}
          >
            <span>Traj. DT {trajectory.year || 2030} :</span>
            <span
              style={{
                width: 120,
                height: 4,
                background: 'var(--sol-ink-200)',
                borderRadius: 2,
                position: 'relative',
                overflow: 'hidden',
                flexShrink: 0,
              }}
            >
              <span
                style={{
                  display: 'block',
                  height: '100%',
                  background:
                    'linear-gradient(to right, var(--sol-calme-fg), var(--sol-attention-fg))',
                  width: `${Math.min(100, Math.max(0, trajectory.progressPct || 0))}%`,
                }}
              />
            </span>
            <span>
              <strong style={{ color: 'var(--sol-ink-900)' }}>
                {trajectory.currentLabel || '—'}
              </strong>{' '}
              / {trajectory.targetLabel || '—'}
            </span>
          </span>
        </>
      )}

      <Separator />
      <span>{solBadge || 'Sol · en veille'}</span>
    </div>
  );
}

function Separator() {
  return (
    <span
      aria-hidden="true"
      style={{
        width: 1,
        height: 16,
        background: 'var(--sol-ink-200)',
      }}
    />
  );
}
