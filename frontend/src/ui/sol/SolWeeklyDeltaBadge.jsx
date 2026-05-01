/**
 * SolWeeklyDeltaBadge — chip stylisé pour push événementiel "+X vs S-1".
 *
 * Sprint Refonte Narrative dynamique — Phase 4.bis.B (audit P1-7 wiring).
 *
 * Audit Ergonomie : « Push +X vs S-1 noyé typographiquement dans <p>
 * monochrome. Aucun chevron up/down, aucune sémantique delta. Pour un
 * CFO qui survole en 7s, le signal le plus saillant de la semaine est
 * invisible. »
 *
 * Ce composant rend le payload `primary_push` (Phase 4.0.B) en chip
 * sémantique : flèche up/down + clause + couleur tonale (TENSION pour
 * up sur exposure, CALME pour down).
 *
 * Display-only — aucun calcul métier (Doctrine §8.1 règle d'or).
 *
 * Props :
 *   primaryPush: {
 *     metric: string,      // "exposure_eur" | "potential_mwh_year" | ...
 *     clause: string,      // "+ 18 % vs semaine précédente"
 *     magnitude: number,   // 18000 (pour tri / debug)
 *   } | null
 *
 * Si `primaryPush` est `null` (silence éditorial Option 3.C), le composant
 * ne rend rien.
 */
import { ArrowDown, ArrowUp, Minus } from 'lucide-react';

// Doctrine §11.3 — métriques où "up" est négatif (tension) vs neutre.
// exposure_eur, sites_in_drift = on monte = mauvais signal → TENSION.
// potential_mwh_year, compliance_score = on monte = bon signal → CALME.
const METRIC_UP_IS_BAD = {
  exposure_eur: true,
  sites_in_drift: true,
  potential_mwh_year: false,
  compliance_score: false,
};

function _detectDirection(clause) {
  // La clause est formattée par BE format_push_clause :
  //   "+ 18 % vs semaine précédente" → up
  //   "− 10 % vs semaine précédente" → down (minus Unicode)
  //   "0 % vs ..." → stable
  if (!clause || typeof clause !== 'string') return 'stable';
  const trimmed = clause.trim();
  if (trimmed.startsWith('+')) return 'up';
  if (trimmed.startsWith('−') || trimmed.startsWith('-')) return 'down';
  return 'stable';
}

function _toneForPush(metric, direction) {
  if (direction === 'stable') return 'neutral';
  const upIsBad = METRIC_UP_IS_BAD[metric] ?? true; // fallback conservateur
  if (direction === 'up' && upIsBad) return 'tension';
  if (direction === 'down' && !upIsBad) return 'tension'; // exemple: score baisse
  return 'calme';
}

// Phase 8.A — différenciation a11y daltonienne (audit final P1) :
// la couleur seule ne suffit pas (~8% deutéranopes/protanopes voient
// rouge/vert identiques). On ajoute un `borderStyle` distinct (dashed
// pour tension, solid pour calme) ET un préfixe `srLabel` pour
// lecteur d'écran qui différencie sémantiquement.
const TONE_STYLES = {
  tension: {
    bg: 'bg-[var(--sol-refuse-bg)]',
    fg: 'text-[var(--sol-refuse-fg)]',
    border: 'border-[var(--sol-refuse-line)]',
    borderStyle: 'border-dashed',
    srLabel: 'tension',
  },
  calme: {
    bg: 'bg-[var(--sol-calme-bg)]',
    fg: 'text-[var(--sol-calme-fg)]',
    border: 'border-[var(--sol-calme-line)]',
    borderStyle: 'border-solid',
    srLabel: 'positif',
  },
  neutral: {
    bg: 'bg-[var(--sol-ink-100)]',
    fg: 'text-[var(--sol-ink-700)]',
    border: 'border-[var(--sol-line)]',
    borderStyle: 'border-solid',
    srLabel: 'neutre',
  },
};

export default function SolWeeklyDeltaBadge({ primaryPush, className = '' }) {
  if (!primaryPush || !primaryPush.clause) return null;

  const direction = _detectDirection(primaryPush.clause);
  const tone = _toneForPush(primaryPush.metric, direction);
  const styles = TONE_STYLES[tone];

  const Icon = direction === 'up' ? ArrowUp : direction === 'down' ? ArrowDown : Minus;

  return (
    <span
      data-testid="sol-weekly-delta-badge"
      data-metric={primaryPush.metric}
      data-direction={direction}
      data-tone={tone}
      className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full border ${styles.bg} ${styles.fg} ${styles.border} ${styles.borderStyle} text-xs font-medium ${className}`}
      role="status"
      aria-label={`Signal ${styles.srLabel}, variation hebdomadaire : ${primaryPush.clause}`}
    >
      {/* Phase 8.A — préfixe lecteur d'écran a11y daltonisme : annonce
          le tone sémantique en plus de la couleur visuelle. */}
      <span className="sr-only">{styles.srLabel} :</span>
      <Icon size={12} aria-hidden="true" className="shrink-0" />
      <span className="tabular-nums">{primaryPush.clause}</span>
    </span>
  );
}
