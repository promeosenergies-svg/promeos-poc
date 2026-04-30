/**
 * KpiCard — Composant unifié KPI hero Cockpit dual sol2 (Étape 11 · 29/04/2026).
 *
 * Factorise les 2 implémentations inlinées précédentes :
 *   - CockpitPilotage `<KpiCard>` (variant temporal, kicker scaleLabel court/moyen/contractuel)
 *   - CockpitDecision `<KpiHybrideCard>` (variant confidence, badge Calculé/Modélisé + drill-down)
 *
 * Audit /simplify P1 fin Étape 9 : les 2 composants partageaient ~80 % de la
 * structure (label mono uppercase, valeur Fraunces 28-32px, footer hint mono).
 * Cette unification respecte la règle DRY tout en gardant les variants
 * doctrinalement distincts (échelle temporelle Pilotage vs niveau de confiance
 * Décision).
 *
 * Props polymorphiques :
 *   - variant: 'temporal' | 'confidence' (défaut : 'temporal')
 *   - label : string (Conso mois courant / Trajectoire 2030 / etc)
 *   - tooltip : string optionnel — underline pointillé sur le label
 *   - value : string|number — valeur principale (Fraunces 28-32px)
 *   - unit : string optionnel (MWh/an, kW, /100, k€, ...)
 *   - hint : string optionnel — sous-ligne mono (méthode baseline, source, …)
 *
 * Variant 'temporal' (Pilotage) :
 *   - scaleLabel : "Court terme" | "Moyen terme" | "Contractuel"
 *   - deltaText : string — "+ 5 % vs avril 2025"
 *   - deltaSev : "neutral"|"warning"|"danger" → couleur
 *
 * Variant 'confidence' (Décision) :
 *   - badge : "calculated_regulatory"|"modeled_cee"|"indicative" → label + ton
 *   - source : string — "RegOps · Décret 2019-771"
 *   - drillHref : string optionnel — link footer
 *   - drillLabel : string — "Voir 3 sites NC →"
 */
import { memo } from 'react';
import { Link } from 'react-router-dom';

import { confidenceTone } from '../../ui/sol/solTones';
import JargonText from '../../ui/sol/JargonText';

const TEMPORAL_DELTA_FG = {
  neutral: 'var(--sol-ink-700)',
  warning: 'var(--sol-attention-fg)',
  danger: 'var(--sol-refuse-fg)',
};

const VALUE_FONT_SIZE_BY_VARIANT = {
  temporal: 28, // Pilotage briefing 30s — KPI dense scan rapide
  confidence: 32, // Décision CODIR 3min — KPI hero impact viscéral
};

const UNIT_FONT_SIZE_BY_VARIANT = {
  temporal: 14,
  confidence: 16,
};

function KpiCardImpl({
  variant = 'temporal',
  // Props communes
  label,
  tooltip,
  value,
  unit,
  hint,
  // Variant temporal
  scaleLabel,
  deltaText,
  deltaSev = 'neutral',
  // Variant confidence
  badge,
  source,
  drillHref,
  drillLabel,
}) {
  const isTemporal = variant === 'temporal';
  const tone = !isTemporal && badge ? confidenceTone(badge) : null;
  const deltaFg = isTemporal ? TEMPORAL_DELTA_FG[deltaSev || 'neutral'] : null;
  const valueFontSize = VALUE_FONT_SIZE_BY_VARIANT[variant] || 28;
  const unitFontSize = UNIT_FONT_SIZE_BY_VARIANT[variant] || 14;

  return (
    <div
      className={isTemporal ? 'rounded-lg p-4' : 'rounded-md p-4'}
      style={{ background: 'var(--sol-bg-canvas)' }}
    >
      {/* Étape 1.bis P0-2 — label d'échelle temporelle Pilotage uniquement. */}
      {isTemporal && scaleLabel && (
        <div
          className="font-mono uppercase tracking-[0.08em] mb-2"
          style={{
            fontSize: '9.5px',
            color: 'var(--sol-ink-400)',
            letterSpacing: '0.1em',
          }}
        >
          {scaleLabel}
        </div>
      )}

      {/* Label avec underline pointillée tooltip natif (Étape 7 P0-E). */}
      <div
        className={`font-mono uppercase tracking-[0.07em] ${isTemporal ? 'text-[11px] mb-1.5' : 'mb-2'}`}
        style={{ fontSize: isTemporal ? undefined : 11, color: 'var(--sol-ink-500)' }}
      >
        {tooltip ? (
          <span
            tabIndex={0}
            title={tooltip}
            aria-label={tooltip}
            className="cursor-help"
            style={{ borderBottom: '1px dotted var(--sol-ink-400)' }}
          >
            {label}
          </span>
        ) : (
          label
        )}
      </div>

      {/* Valeur Fraunces + unité body + delta text si applicable */}
      <div className="flex items-baseline gap-2 flex-wrap">
        <div
          style={{
            fontFamily: 'var(--sol-font-display)',
            fontSize: valueFontSize,
            fontWeight: 500,
            lineHeight: 1,
            color: 'var(--sol-ink-900)',
          }}
        >
          {value}
          {unit && (
            <span className="ml-1" style={{ fontSize: unitFontSize, color: 'var(--sol-ink-700)' }}>
              {unit}
            </span>
          )}
        </div>
        {isTemporal && deltaText && (
          <div className="text-xs font-medium" style={{ color: deltaFg }}>
            {deltaText}
          </div>
        )}
      </div>

      {/* Variant confidence : badge Calculé/Modélisé + source */}
      {!isTemporal && tone && (
        <div className="flex items-center gap-1.5 flex-wrap mt-2">
          <span
            className="inline-flex items-center px-1.5 py-0.5 rounded font-mono uppercase tracking-[0.06em]"
            style={{
              fontSize: 9.5,
              background: tone.bg,
              color: tone.fg,
              fontWeight: 500,
            }}
          >
            {tone.label}
          </span>
          {source && (
            <span
              className="font-mono uppercase tracking-[0.05em]"
              style={{ fontSize: 10.5, color: 'var(--sol-ink-500)' }}
            >
              {/* Phase 17.ter.C — auto-tooltip acronymes connus dans la
                  source (ex "REGOPS · DT + BACS + APER PONDÉRÉ" → DT/BACS/
                  APER deviennent hovorables/focusables). */}
              <JargonText>{source}</JargonText>
            </span>
          )}
        </div>
      )}

      {/* Variant temporal : hint mono auto-explicatif (méthode baseline, …) */}
      {isTemporal && hint && (
        <div
          className="mt-1.5 font-mono uppercase tracking-[0.07em]"
          style={{ fontSize: '10.5px', color: 'var(--sol-ink-500)' }}
        >
          <JargonText>{hint}</JargonText>
        </div>
      )}

      {/* Variant confidence : drill-down link footer */}
      {!isTemporal && drillHref && (
        <div className="mt-1.5">
          <Link
            to={drillHref}
            className="font-mono uppercase tracking-[0.05em] no-underline hover:underline inline-flex items-center gap-1"
            style={{ fontSize: 11, color: 'var(--sol-ink-700)' }}
          >
            {drillLabel} →
          </Link>
        </div>
      )}
    </div>
  );
}

// Phase 13.E — React.memo : KpiCard reçoit des props primitives stables
// (label, value, unit, hint, badge, source). Wrap mémoïsation : évite les
// re-renders quand un parent re-render mais ces props n'ont pas changé.
// Triptyque KPI hero × 6 KPIs cumulés Pilotage + Décision = gain visible.
const KpiCard = memo(KpiCardImpl);
export default KpiCard;
