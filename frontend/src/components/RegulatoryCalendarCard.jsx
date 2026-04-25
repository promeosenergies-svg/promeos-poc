/**
 * PROMEOS — RegulatoryCalendarCard
 *
 * Mini-calendrier des 3 prochaines échéances réglementaires énergie B2B
 * France impactant le patrimoine tertiaire. Visibilité COMEX + exploitant
 * sur l'horizon réglementaire 2026-2030.
 *
 * Source : regulatory_calendar canonique (deadlines connues publiquement).
 * Quand le backend exposera /api/regulatory/calendar, swap d'1 ligne.
 */
import { useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { Calendar, ArrowRight } from 'lucide-react';

// Deadlines réglementaires canoniques B2B tertiaire France (recurring + ponctuelles)
const DEADLINES_CANONIQUES = [
  {
    id: 'operat-2026',
    date: '2026-09-30',
    label: 'OPERAT télédéclaration annuelle',
    framework: 'Décret Tertiaire',
    impact: 'Sites > 1 000 m² tertiaire',
    urgency: 'medium',
    path: '/conformite/tertiaire',
  },
  {
    id: 'bacs-2027',
    date: '2027-01-01',
    label: 'BACS classe C obligatoire',
    framework: 'Décret BACS',
    impact: 'Sites > 290 kW puissance nominale',
    urgency: 'high',
    path: '/conformite',
  },
  {
    id: 'aper-2028',
    date: '2028-07-01',
    label: 'APER ombrières parkings',
    framework: 'Loi APER',
    impact: 'Parkings > 1 500 m² couverts',
    urgency: 'medium',
    path: '/conformite/aper',
  },
  {
    id: 'ets2-2027',
    date: '2027-01-01',
    label: 'ETS2 carbone bâtiment + transport',
    framework: 'EU ETS2',
    impact: 'Émissions Scope 1 gaz/fioul',
    urgency: 'medium',
    path: '/conformite',
  },
  {
    id: 'dt-2030',
    date: '2030-12-31',
    label: 'Décret Tertiaire jalon -40%',
    framework: 'Décret Tertiaire',
    impact: 'Tous sites tertiaires',
    urgency: 'medium',
    path: '/conformite/tertiaire',
  },
];

const URGENCY_COLOR = {
  critical: { bg: 'var(--sol-afaire-bg, #fef2f2)', fg: 'var(--sol-afaire-fg, #b91c1c)' },
  high: { bg: 'var(--sol-attention-bg, #fef3c7)', fg: 'var(--sol-attention-fg, #b45309)' },
  medium: { bg: 'var(--sol-calme-bg, #ecfdf5)', fg: 'var(--sol-calme-fg, #047857)' },
};

function formatFRDate(iso) {
  try {
    const d = new Date(iso);
    return d.toLocaleDateString('fr-FR', { day: 'numeric', month: 'short', year: 'numeric' });
  } catch {
    return iso;
  }
}

function daysUntil(iso) {
  const target = new Date(iso);
  const today = new Date();
  return Math.ceil((target - today) / (1000 * 60 * 60 * 24));
}

export default function RegulatoryCalendarCard({ limit = 3 }) {
  const navigate = useNavigate();

  const upcoming = useMemo(() => {
    return DEADLINES_CANONIQUES.map((d) => ({ ...d, days: daysUntil(d.date) }))
      .filter((d) => d.days > 0)
      .sort((a, b) => a.days - b.days)
      .slice(0, limit);
  }, [limit]);

  if (upcoming.length === 0) return null;

  return (
    <div
      style={{
        background: 'var(--sol-bg-paper)',
        border: '1px solid var(--sol-ink-200)',
        borderRadius: 8,
        padding: 16,
      }}
    >
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 8,
          marginBottom: 14,
        }}
      >
        <Calendar size={14} style={{ color: 'var(--sol-ink-500)' }} />
        <span
          style={{
            fontFamily: 'var(--sol-font-mono)',
            fontSize: 9.5,
            textTransform: 'uppercase',
            letterSpacing: '0.1em',
            color: 'var(--sol-ink-500)',
            fontWeight: 600,
          }}
        >
          Calendrier réglementaire — {upcoming.length} prochaine{upcoming.length > 1 ? 's' : ''} échéance{upcoming.length > 1 ? 's' : ''}
        </span>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        {upcoming.map((d, idx) => {
          const colors = URGENCY_COLOR[d.urgency] || URGENCY_COLOR.medium;
          const isLast = idx === upcoming.length - 1;
          return (
            <button
              key={d.id}
              type="button"
              onClick={() => navigate(d.path)}
              style={{
                all: 'unset',
                cursor: 'pointer',
                display: 'grid',
                gridTemplateColumns: 'auto 1fr auto',
                gap: 12,
                alignItems: 'center',
                padding: '8px 0',
                borderBottom: !isLast ? '1px dashed var(--sol-ink-200)' : 'none',
              }}
              onMouseEnter={(e) =>
                (e.currentTarget.style.background = 'var(--sol-bg-canvas, #fafaf6)')
              }
              onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
            >
              {/* Days countdown badge */}
              <div
                style={{
                  minWidth: 56,
                  textAlign: 'center',
                  padding: '4px 8px',
                  borderRadius: 6,
                  background: colors.bg,
                  color: colors.fg,
                  fontFamily: 'var(--sol-font-mono)',
                  fontSize: 11,
                  fontWeight: 700,
                }}
              >
                {d.days < 30
                  ? `${d.days}j`
                  : d.days < 365
                    ? `${Math.round(d.days / 30)}m`
                    : `${Math.round(d.days / 365)}a`}
              </div>

              {/* Label + meta */}
              <div style={{ minWidth: 0 }}>
                <div
                  style={{
                    fontSize: 13,
                    fontWeight: 600,
                    color: 'var(--sol-ink-900)',
                    marginBottom: 2,
                    lineHeight: 1.3,
                  }}
                >
                  {d.label}
                </div>
                <div
                  style={{
                    fontSize: 11,
                    color: 'var(--sol-ink-500)',
                    fontFamily: 'var(--sol-font-mono)',
                    letterSpacing: '0.04em',
                  }}
                >
                  {d.framework} · {d.impact} · {formatFRDate(d.date)}
                </div>
              </div>

              <ArrowRight size={14} style={{ color: 'var(--sol-ink-400)' }} />
            </button>
          );
        })}
      </div>
    </div>
  );
}
