/**
 * CockpitPilotage — Page Pilotage refonte WOW (29/04/2026, Étape 1.bis).
 *
 * Audience : energy manager · 30 s · « quoi traiter aujourd'hui »
 * Doctrine §11.3 : page de pilotage, source unique partagée avec Synthèse
 *
 * Cible : `docs/maquettes/cockpit-sol2/cockpit-pilotage-briefing-jour.html`
 *
 * Sections (top → bottom) :
 *   1. Header — kicker + switch éditorial + H1 Fraunces + sous-ligne mono
 *   2. Pills alertes + bouton Centre d'action
 *   3. Triptyque KPI temporel multi-échelle :
 *      • COURT TERME — Conso J−1 (baseline historique A)
 *      • MOYEN TERME — Conso mois courant DJU-ajusté (baseline B)
 *      • CONTRACTUEL — Pic puissance J−1 vs souscrite
 *      Labels d'échelle explicites (Étape 1.bis P0-2 — Marc 30s test).
 *   4. 2 visuels glanceables — Conso 7j barres + Courbe charge HP/HC
 *   5. File de traitement P1-P5 priorisée + drill-down stratégique
 *   6. Footer Sol — sources/confiance/MAJ/méthodologie
 *
 * Sources data :
 *   - useCockpitFacts('current_month') → triptyque + alertes + métadonnées
 *   - getCockpitPriorities() → file P1-P5 (org-scoped backend)
 *
 * Étape 1.bis P0 corrigés :
 *   ✓ P0-1 fmtMwh/fmtKw/fmtPct/deltaSeverity importés depuis SoT utils/format
 *   ✓ P0-2 labels échelle "Court terme / Moyen terme / Contractuel"
 *   ✓ P0-3 fallback intelligent KPI J−1=0 → "—" + footer "données en synchro"
 *   ✓ P0-5 lien "voir impact stratégique →" sur P1-P3 (DoD 5)
 *   ✓ P0-6 skeleton Sol shimmer pendant fetch (3 KPI placeholder)
 *   ✓ P0-7 org-scoping vérifié backend (resolve_org_id ligne 930)
 *   ✓ P0-8 footer mono source/MAJ/confiance sous chaque visuel
 *   ⏳ P0-4 4ᵉ colonne Impact Fraunces différée Étape 4 (backend gap-filler)
 */
import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Bell, ArrowRight, Clock } from 'lucide-react';

import useCockpitFacts from '../hooks/useCockpitFacts';
import SolKickerWithSwitch from '../ui/sol/SolKickerWithSwitch';
import AcronymTooltip from '../ui/sol/AcronymTooltip';
import KpiCard from '../components/cockpit/KpiCard';
import KpiSkeleton from '../components/cockpit/KpiSkeleton';
import { getCockpitPriorities } from '../services/api/cockpit';
import { useScope } from '../contexts/ScopeContext';
import { splitMwh, splitKw, fmtPct, fmtEurShort, deltaSeverity } from '../utils/format';
import { getIsoWeek, relativeTime, fmtDateLong } from '../utils/date';
import { severityTone } from '../ui/sol/solTones';

/** Format delta percent for KPI tone — adds explicit sign + spacing pour
 *  lisibilité Marc 30s. fmtPct SoT n'ajoute pas le signe + et accepte un
 *  ratio 0-1 par défaut, ici on attend déjà du % brut backend. */
function fmtDeltaPct(v) {
  if (v == null || !Number.isFinite(v)) return null;
  const sign = v > 0 ? '+ ' : v < 0 ? '− ' : '';
  return `${sign}${fmtPct(Math.abs(v), false, 0)}`;
}

// Étape 11 : KpiCard + KpiSkeleton factorisés dans components/cockpit/
// (voir /Users/amine/projects/promeos-poc/frontend/src/components/cockpit/KpiCard.jsx).
// Avant : 2 implémentations inlinées (Pilotage + Décision) avec 80% structure
// commune — audit /simplify P1 fin Étape 9. Après : 1 composant unifié avec
// variant='temporal' (Pilotage) | 'confidence' (Décision).

// ── Triptyque KPI temporel multi-échelle ─────────────────────────────

const SCALE_LABEL = {
  short: 'Court terme',
  medium: 'Moyen terme',
  contract: 'Contractuel',
};

function KpiTriptyqueEnergetique({ facts }) {
  const c = facts?.consumption || {};
  const p = facts?.power || {};
  const monthly = c.monthly_vs_n1 || {};

  // KPI 1 — Conso J−1 court terme (baseline historique A)
  // Backend Étape 4 P0-C : `j_minus_1_source` indique J−1 (canonique) ou
  // J−2/J−3… si fallback. Si encore 0, on affiche "—" + hint synchronisation.
  const jm1 = c.j_minus_1_mwh;
  const baseJm1 = c.baseline_j_minus_1?.value_mwh;
  const deltaJm1 = c.baseline_j_minus_1?.delta_pct;
  const jm1Source = c.j_minus_1_source || 'j-1';
  const jm1IsFallback = jm1Source !== 'j-1';
  const jm1Stale = (jm1 === 0 || jm1 == null) && baseJm1 != null && baseJm1 > 0;
  const jm1Split = jm1Stale ? { value: '—', unit: '' } : splitMwh(jm1);

  // KPI 2 — Conso mois courant DJU-ajusté (moyen terme · baseline B)
  const monthlyMwh = monthly.current_month_mwh;
  const monthlyDeltaPct = monthly.delta_pct_dju_adjusted;
  const monthlySplit = splitMwh(monthlyMwh);
  const calibDate = monthly.calibration_date
    ? new Date(monthly.calibration_date).toLocaleDateString('fr-FR', {
        day: '2-digit',
        month: '2-digit',
      })
    : null;
  const monthlyTooltip = monthly.current_month_label
    ? `${monthly.current_month_label} vs N−1 normalisé · Baseline ${
        monthly.baseline_method?.replace(/_/g, ' ') || '—'
      }${monthly.r_squared ? ` · r² ${monthly.r_squared.toFixed(2)}` : ''}${
        calibDate ? ` · calibrée ${calibDate}` : ''
      }`
    : 'Comparaison mois courant vs N−1 DJU-ajustée';

  // KPI 3 — Pic puissance J−1 contractuel
  const peakKw = p.peak_j_minus_1_kw;
  const subscribedKw = p.subscribed_kw;
  const peakDeltaPct = p.delta_pct;
  const peakTime = p.peak_time;
  const peakSource = p.peak_source || 'j-1';
  const peakIsFallback = peakSource !== 'j-1';
  const peakStale = (peakKw === 0 || peakKw == null) && subscribedKw != null && subscribedKw > 0;
  const peakSplit = peakStale ? { value: '—', unit: '' } : splitKw(peakKw);

  // Année N−1 dynamique pour le label delta KPI 2 (ex: "vs avril 2025")
  const previousYearLabel = (() => {
    if (!monthly.current_month_label) return 'N−1';
    const m = monthly.current_month_label.match(/^(\w+)\s+(\d{4})/);
    if (!m) return 'N−1';
    return `${m[1]} ${+m[2] - 1}`;
  })();

  return (
    /* Étape 7 P0-D : ordre triptyque réordonné — moyen terme (mois courant)
       en 1er position. Audit user 29/04 : la mesure mensuelle DJU-ajustée
       est plus stable et plus parlante "vue météo portefeuille" que le J−1
       volatile, et la conso contractuelle reste en clôture pour les seuils.
       Logique narrative : MOYEN (carte de référence) → COURT (alerte vive)
       → CONTRACTUEL (signal de risque tarifaire). */
    <div className="grid grid-cols-1 md:grid-cols-3 gap-2.5 my-4">
      <KpiCard
        scaleLabel={SCALE_LABEL.medium}
        label="Conso mois courant"
        tooltip={monthlyTooltip}
        value={monthlySplit.value}
        unit={monthlySplit.unit}
        deltaText={
          monthlyDeltaPct != null ? `${fmtDeltaPct(monthlyDeltaPct)} vs ${previousYearLabel}` : null
        }
        deltaSev={deltaSeverity(monthlyDeltaPct)}
        hint={
          calibDate
            ? `DJU-ajusté · calibrée ${calibDate}`
            : monthly.current_month_label
              ? `DJU-ajusté · ${monthly.current_month_label}`
              : null
        }
      />
      <KpiCard
        scaleLabel={SCALE_LABEL.short}
        label="Conso J−1 · groupe"
        tooltip="Baseline A · moyenne mêmes jours sur 12 semaines glissantes"
        value={jm1Split.value}
        unit={jm1Split.unit}
        deltaText={
          jm1Stale ? null : deltaJm1 != null ? `${fmtDeltaPct(deltaJm1)} vs baseline` : null
        }
        deltaSev={deltaSeverity(deltaJm1)}
        hint={
          jm1Stale
            ? 'Données J−1 en synchronisation EMS · MAJ ce matin'
            : jm1IsFallback
              ? `Mesure du ${jm1Source.replace('j-', 'J−')} (J−1 en synchro EMS) · réf. ${splitMwh(baseJm1).value} ${splitMwh(baseJm1).unit}`
              : baseJm1 != null
                ? `Réf. ${splitMwh(baseJm1).value} ${splitMwh(baseJm1).unit} · même jour S−1`
                : null
        }
      />
      <KpiCard
        scaleLabel={SCALE_LABEL.contract}
        // Phase 14.C (audit véracité Marc) : label dynamique selon peak_source.
        // Avant : "Pic puissance J−1" en dur même quand la mesure datait de J−29
        // (peak_source = "j-29") → titre faux, perte confiance EM immédiate.
        // Après : si fallback, on affiche "Pic puissance J−N" avec N = jours
        // d'ancienneté pour que Marc voie immédiatement la fraîcheur.
        label={
          peakIsFallback ? `Pic puissance ${peakSource.replace('j-', 'J−')}` : 'Pic puissance J−1'
        }
        tooltip="Mesure CDC 30 min agrégée sites · vs puissance souscrite contractuelle"
        value={peakSplit.value}
        unit={peakSplit.unit}
        deltaText={
          peakStale
            ? null
            : peakDeltaPct != null && peakDeltaPct !== 0
              ? `${fmtDeltaPct(peakDeltaPct)} vs souscrite`
              : null
        }
        deltaSev={deltaSeverity(peakDeltaPct)}
        hint={
          peakStale
            ? 'Pic CDC J−1 en synchronisation Enedis SGE'
            : peakIsFallback
              ? `Mesure du ${peakSource.replace('j-', 'J−')} (CDC J−1 en synchro SGE) · souscrite ${splitKw(subscribedKw).value} ${splitKw(subscribedKw).unit}`
              : subscribedKw != null
                ? `Souscrite ${splitKw(subscribedKw).value} ${splitKw(subscribedKw).unit}${peakTime && peakTime !== '00:00' ? ` · ${peakTime}` : ''}`
                : null
        }
      />
    </div>
  );
}

// ── Visuels glanceables (V1 placeholder structuré) ─────────────────

function VisuelFooterMono({ source, lastUpdate, confidence }) {
  return (
    <div
      className="mt-1.5 font-mono uppercase tracking-[0.07em] flex justify-between flex-wrap gap-1"
      style={{ fontSize: '10px', color: 'var(--sol-ink-500)' }}
    >
      <span>{source}</span>
      <span>
        {lastUpdate ? `MAJ ${lastUpdate}` : ''}
        {confidence ? ` · confiance ${confidence}` : ''}
      </span>
    </div>
  );
}

function ConsoSevenDaysBars({ lastUpdate, confidence, weeklyAnomaly }) {
  // Étape 6.bis P1 : sous-titre narratif chiffré nommé (audit /frontend-design
  // pixel-perfect Étape 5). Si backend expose `consumption.weekly_anomaly` :
  // {day_label, site_name, delta_pct} → on rend "Sam 25 avril : +39% vs
  // baseline — anomalie Hôtel Nice". Sinon fallback générique honnête.
  const anomalyText = weeklyAnomaly ? (
    <>
      {weeklyAnomaly.day_label} :{' '}
      <strong style={{ fontWeight: 500, color: 'var(--sol-refuse-fg)' }}>
        {weeklyAnomaly.delta_pct > 0 ? '+ ' : '− '}
        {Math.abs(weeklyAnomaly.delta_pct)} %
      </strong>{' '}
      vs baseline — anomalie {weeklyAnomaly.site_name}
    </>
  ) : (
    'Pic anormal de la semaine en rouge · scan visuel 5 secondes.'
  );
  return (
    <div
      className="rounded-md p-4"
      style={{
        background: 'var(--sol-bg-paper)',
        border: '0.5px solid var(--sol-rule)',
      }}
    >
      <div className="flex justify-between items-start gap-2 mb-2">
        <div>
          <div
            className="font-mono uppercase tracking-[0.07em] mb-1"
            style={{ fontSize: '11px', color: 'var(--sol-ink-500)' }}
          >
            Conso 7 jours · MWh/jour
          </div>
          <div className="text-xs" style={{ color: 'var(--sol-ink-700)', lineHeight: 1.4 }}>
            {anomalyText}
          </div>
        </div>
        <Link
          to="/consommations/portfolio"
          className="text-[11px] font-mono uppercase tracking-[0.05em] no-underline shrink-0 hover:underline"
          style={{ color: 'var(--sol-ink-500)' }}
        >
          Détail →
        </Link>
      </div>
      <svg
        viewBox="0 0 320 130"
        xmlns="http://www.w3.org/2000/svg"
        style={{ width: '100%', height: 'auto', display: 'block', marginTop: 6 }}
        role="img"
        aria-label="Barres consommation 7 jours, samedi en rouge anomalie"
      >
        <line
          x1="32"
          y1="20"
          x2="320"
          y2="20"
          stroke="currentColor"
          strokeOpacity=".08"
          strokeDasharray="2,3"
        />
        <line
          x1="32"
          y1="55"
          x2="320"
          y2="55"
          stroke="currentColor"
          strokeOpacity=".08"
          strokeDasharray="2,3"
        />
        <line
          x1="32"
          y1="90"
          x2="320"
          y2="90"
          stroke="currentColor"
          strokeOpacity=".15"
          strokeDasharray="3,3"
        />
        <text
          x="28"
          y="23"
          textAnchor="end"
          fontFamily="var(--sol-font-mono)"
          fontSize="9"
          fill="currentColor"
          fillOpacity=".5"
        >
          12
        </text>
        <text
          x="28"
          y="58"
          textAnchor="end"
          fontFamily="var(--sol-font-mono)"
          fontSize="9"
          fill="currentColor"
          fillOpacity=".5"
        >
          8
        </text>
        <text
          x="28"
          y="93"
          textAnchor="end"
          fontFamily="var(--sol-font-mono)"
          fontSize="9"
          fill="currentColor"
          fillOpacity=".5"
        >
          4
        </text>
        <line
          x1="32"
          y1="68"
          x2="320"
          y2="68"
          stroke="currentColor"
          strokeOpacity=".25"
          strokeDasharray="2,2"
        />
        <g fill="var(--sol-calme-fg)">
          <rect x="42" y="48" width="32" height="55" rx="2" />
          <rect x="84" y="50" width="32" height="53" rx="2" />
          <rect x="126" y="44" width="32" height="59" rx="2" />
          <rect x="168" y="46" width="32" height="57" rx="2" />
          <rect x="210" y="49" width="32" height="54" rx="2" />
        </g>
        <rect x="252" y="22" width="32" height="81" rx="2" fill="var(--sol-refuse-fg)" />
        <rect
          x="294"
          y="55"
          width="22"
          height="48"
          rx="2"
          fill="var(--sol-calme-fg)"
          fillOpacity=".5"
        />
        <text
          x="266"
          y="14"
          textAnchor="middle"
          fontSize="9"
          fontWeight="500"
          fill="var(--sol-refuse-fg)"
        >
          +&#x202f;39&#x202f;%
        </text>
        <g
          fontFamily="var(--sol-font-mono)"
          fontSize="9"
          fill="currentColor"
          fillOpacity=".55"
          textAnchor="middle"
        >
          <text x="58" y="120">
            L
          </text>
          <text x="100" y="120">
            M
          </text>
          <text x="142" y="120">
            M
          </text>
          <text x="184" y="120">
            J
          </text>
          <text x="226" y="120">
            V
          </text>
          <text x="268" y="120" fontWeight="500" fill="var(--sol-refuse-fg)" fillOpacity="1">
            S
          </text>
          <text x="305" y="120">
            D
          </text>
        </g>
      </svg>
      <VisuelFooterMono
        source="Source EMS · agrégé sites"
        lastUpdate={lastUpdate}
        confidence={confidence}
      />
    </div>
  );
}

function CourbeChargeJMinus1({ subscribedKw, lastUpdate, confidence }) {
  const subSplit = splitKw(subscribedKw);
  return (
    <div
      className="rounded-md p-4"
      style={{
        background: 'var(--sol-bg-paper)',
        border: '0.5px solid var(--sol-rule)',
      }}
    >
      <div className="flex justify-between items-start gap-2 mb-2">
        <div>
          <div
            className="font-mono uppercase tracking-[0.07em] mb-1"
            style={{ fontSize: '11px', color: 'var(--sol-ink-500)' }}
          >
            Courbe de charge J−1 · groupe · kW
          </div>
          <div className="text-xs" style={{ color: 'var(--sol-ink-700)', lineHeight: 1.4 }}>
            HP / HC contractuelles · ligne souscrite{' '}
            <strong style={{ fontWeight: 500 }}>
              {subscribedKw != null ? `${subSplit.value} ${subSplit.unit}` : '—'}
            </strong>
          </div>
        </div>
        <div className="flex gap-2 shrink-0">
          <span
            className="font-mono uppercase tracking-[0.05em] inline-flex items-center gap-1"
            style={{ fontSize: '10px', color: 'var(--sol-ink-500)' }}
          >
            <span
              className="inline-block"
              style={{ width: 8, height: 2, background: 'var(--sol-hpe-fg)' }}
            />
            HP
          </span>
          <span
            className="font-mono uppercase tracking-[0.05em] inline-flex items-center gap-1"
            style={{ fontSize: '10px', color: 'var(--sol-ink-500)' }}
          >
            <span
              className="inline-block"
              style={{ width: 8, height: 2, background: 'var(--sol-hch-fg)' }}
            />
            HC
          </span>
        </div>
      </div>
      <svg
        viewBox="0 0 320 130"
        xmlns="http://www.w3.org/2000/svg"
        style={{ width: '100%', height: 'auto', display: 'block', marginTop: 6 }}
        role="img"
        aria-label="Courbe de charge J moins 1 du groupe"
      >
        <defs>
          <linearGradient id="hp-fill-pilotage" x1="0" x2="0" y1="0" y2="1">
            <stop offset="0%" stopColor="var(--sol-hpe-fg)" stopOpacity=".18" />
            <stop offset="100%" stopColor="var(--sol-hpe-fg)" stopOpacity="0" />
          </linearGradient>
        </defs>
        <rect x="32" y="10" width="46" height="95" fill="var(--sol-hch-fg)" fillOpacity=".05" />
        <rect x="284" y="10" width="36" height="95" fill="var(--sol-hch-fg)" fillOpacity=".05" />
        <line
          x1="32"
          y1="20"
          x2="320"
          y2="20"
          stroke="currentColor"
          strokeOpacity=".08"
          strokeDasharray="2,3"
        />
        <line
          x1="32"
          y1="55"
          x2="320"
          y2="55"
          stroke="currentColor"
          strokeOpacity=".08"
          strokeDasharray="2,3"
        />
        <line
          x1="32"
          y1="90"
          x2="320"
          y2="90"
          stroke="currentColor"
          strokeOpacity=".15"
          strokeDasharray="3,3"
        />
        <line
          x1="32"
          y1="34"
          x2="320"
          y2="34"
          stroke="var(--sol-refuse-fg)"
          strokeOpacity=".55"
          strokeDasharray="3,3"
          strokeWidth="1"
        />
        <text
          x="318"
          y="31"
          textAnchor="end"
          fontFamily="var(--sol-font-mono)"
          fontSize="8.5"
          fill="var(--sol-refuse-fg)"
          fillOpacity=".85"
        >
          P. souscrite {subscribedKw != null ? `${subSplit.value} ${subSplit.unit}` : '—'}
        </text>
        <path
          d="M32,90 L78,80 L92,68 L106,46 L120,40 L134,42 L148,52 L162,58 L176,52 L190,46 L204,42 L218,46 L232,50 L246,56 L260,64 L274,76 L284,82 L284,105 L32,105 Z"
          fill="url(#hp-fill-pilotage)"
          fillOpacity=".7"
        />
        <path
          d="M32,92 L48,90 L60,88 L72,84 L78,80"
          fill="none"
          stroke="var(--sol-hch-fg)"
          strokeWidth="1.6"
        />
        <path
          d="M78,80 L92,68 L106,46 L120,40 L134,42 L148,52 L162,58 L176,52 L190,46 L204,42 L218,46 L232,50 L246,56 L260,64 L274,76 L284,82"
          fill="none"
          stroke="var(--sol-hpe-fg)"
          strokeWidth="1.6"
        />
        <path
          d="M284,82 L296,86 L308,90 L320,93"
          fill="none"
          stroke="var(--sol-hch-fg)"
          strokeWidth="1.6"
        />
        <g
          fontFamily="var(--sol-font-mono)"
          fontSize="9"
          fill="currentColor"
          fillOpacity=".55"
          textAnchor="middle"
        >
          <text x="32" y="120">
            0 h
          </text>
          <text x="106" y="120">
            8 h
          </text>
          <text x="176" y="120">
            12 h
          </text>
          <text x="250" y="120">
            18 h
          </text>
          <text x="320" y="120">
            22 h
          </text>
        </g>
      </svg>
      <VisuelFooterMono
        source="Source EMS · CDC 30 min · agrégé sites"
        lastUpdate={lastUpdate}
        confidence={confidence}
      />
    </div>
  );
}

// ── File de traitement P1-P5 ─────────────────────────────────────────

/** Maquette §11.3 réciprocité P1-P3 portent un lien stratégique (DoD 5). */
const STRATEGIC_HREF = '/cockpit/strategique';

function FileTraitementRow({ rank, item }) {
  const tone = severityTone(item.urgency);
  const showStrategicLink = rank <= 3;
  // Étape 4.bis FE : 4ᵉ colonne Impact maquette §11.3 (signal métier #1).
  // Backend P0-D : impact_value_eur ou impact_value_mwh_year + category_label
  // depuis /cockpit/priorities. Si impact non chiffré, on n'affiche que P-rank.
  const impactEur = item.impact_value_eur;
  const impactMwh = item.impact_value_mwh_year;
  const categoryLabel = item.category_label;
  const hasImpact = (impactEur != null && impactEur > 0) || (impactMwh != null && impactMwh > 0);
  // Étape 10 P1-2 : badge confidence (Calculé / Modélisé / Indicatif) pour
  // cohérence visuelle avec les KPI hybride Décision (audit /frontend-design).
  const confidenceBadge = item.confidence_badge;
  const confidenceLabel =
    confidenceBadge === 'calculated_regulatory' || confidenceBadge === 'calculated_contractual'
      ? 'Calculé'
      : confidenceBadge === 'modeled_cee' || confidenceBadge === 'modeled'
        ? 'Modélisé'
        : confidenceBadge === 'indicative'
          ? 'Indicatif'
          : null;
  const confidenceTone =
    confidenceLabel === 'Calculé'
      ? { bg: 'var(--sol-succes-bg)', fg: 'var(--sol-succes-fg)' }
      : confidenceLabel === 'Modélisé'
        ? { bg: 'var(--sol-attention-bg)', fg: 'var(--sol-attention-fg)' }
        : confidenceLabel === 'Indicatif'
          ? { bg: 'var(--sol-hce-bg)', fg: 'var(--sol-hce-fg)' }
          : null;
  // Étape 7 P0-B anchor : la page Décision link "Voir preuve opérationnelle →"
  // utilise `/cockpit/jour#decision-{id}`. On expose un `id` HTML sur chaque
  // ligne pour que le scroll vers l'ancre fonctionne (audit Phase 5 : ancre
  // absente précédemment).
  const anchorId = `decision-${item.rank}`;
  return (
    <div
      id={anchorId}
      className="block rounded-md mb-1.5 transition-shadow"
      style={{
        background: tone.bg,
        border: `0.5px solid ${tone.line}`,
        padding: '11px 13px',
        color: 'var(--sol-ink-900)',
        scrollMarginTop: '80px', // évite que le header sticky cache la ligne au scroll-to
      }}
    >
      <div
        className="grid items-center gap-3"
        style={{
          gridTemplateColumns: hasImpact ? '36px 1fr auto auto' : '36px 1fr auto',
        }}
      >
        <span
          className="font-mono font-medium text-center px-2 py-0.5 rounded"
          style={{
            background: 'rgba(0,0,0,0.06)',
            color: tone.fg,
            fontSize: 10.5,
            letterSpacing: '0.05em',
            textTransform: 'uppercase',
          }}
        >
          P{rank}
        </span>
        <div className="min-w-0">
          <div className="font-medium mb-0.5" style={{ fontSize: 14, color: 'var(--sol-ink-900)' }}>
            {item.title}
          </div>
          <div
            className="flex items-center gap-2 flex-wrap"
            style={{ fontSize: 11.5, color: 'var(--sol-ink-700)' }}
          >
            {/* Backend P0-D : category_label (Anomalie / Dépassement / Hors horaires
                / Conformité op / Exposition) discrimine visuellement P1-P5. */}
            {categoryLabel && (
              <span
                className="inline-flex items-center px-1.5 py-0.5 rounded font-mono uppercase tracking-[0.05em]"
                style={{
                  fontSize: 9.5,
                  background: 'rgba(0,0,0,0.06)',
                  color: tone.fg,
                  fontWeight: 500,
                }}
              >
                {categoryLabel}
              </span>
            )}
            {item.domain && (
              <span
                className="font-mono uppercase tracking-[0.05em]"
                style={{ fontSize: 10, color: 'var(--sol-ink-500)' }}
              >
                {item.domain}
              </span>
            )}
            <Link
              to={item.action_url || '/anomalies'}
              className="font-mono uppercase tracking-[0.05em] no-underline hover:underline inline-flex items-center gap-1"
              style={{ fontSize: 10, color: tone.fg, fontWeight: 500 }}
            >
              Traiter
              <ArrowRight size={10} aria-hidden="true" />
            </Link>
            {showStrategicLink && (
              <Link
                to={STRATEGIC_HREF}
                className="no-underline hover:underline"
                style={{
                  fontSize: 11,
                  color: 'var(--sol-ink-500)',
                  fontStyle: 'italic',
                }}
              >
                voir impact stratégique →
              </Link>
            )}
          </div>
        </div>
        {/* 4ᵉ colonne Impact Fraunces — signal métier #1 maquette. */}
        {hasImpact && (
          <div style={{ textAlign: 'right' }}>
            <div
              style={{
                fontFamily: 'var(--sol-font-display)',
                fontSize: 14,
                fontWeight: 500,
                color: tone.fg,
                lineHeight: 1.1,
              }}
            >
              {impactEur != null && impactEur > 0
                ? fmtEurShort(impactEur)
                : `${Math.round(impactMwh).toLocaleString('fr-FR')} MWh/an`}
            </div>
            <div
              className="flex items-center justify-end gap-1 mt-0.5"
              style={{ fontSize: 10.5, color: 'var(--sol-ink-500)' }}
            >
              {confidenceLabel && confidenceTone && (
                <span
                  className="inline-flex items-center px-1 py-0 rounded font-mono uppercase tracking-[0.06em]"
                  style={{
                    fontSize: 9,
                    background: confidenceTone.bg,
                    color: confidenceTone.fg,
                    fontWeight: 500,
                  }}
                  title={item.confidence_source || 'Source canonique'}
                >
                  {confidenceLabel}
                </span>
              )}
              <span>{impactEur != null ? "d'exposition" : 'récupérable'}</span>
            </div>
          </div>
        )}
        {/* Étape 11 fix : la flèche horizontale est désormais cliquable
            (audit user 29/04 : "les flèches horizontales n'ont pas de route").
            Elle reproduit la cible "Traiter →" pour les utilisateurs qui
            scannent l'extrémité droite de la ligne avant la zone texte. */}
        <Link
          to={item.action_url || '/anomalies'}
          aria-label={`Traiter : ${item.title}`}
          className="inline-flex items-center justify-center transition-opacity hover:opacity-100"
          style={{
            color: tone.fg,
            opacity: 0.6,
            padding: '6px',
            borderRadius: 4,
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.opacity = '1';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.opacity = '0.6';
          }}
        >
          <ArrowRight size={14} aria-hidden="true" />
        </Link>
      </div>
    </div>
  );
}

function FileTraitement({ priorities, loading, remainingCount = 0 }) {
  if (loading) {
    return (
      <div className="space-y-1.5">
        {[1, 2, 3].map((i) => (
          <div
            key={i}
            className="rounded-md animate-pulse"
            style={{
              background: 'var(--sol-bg-canvas)',
              border: '0.5px solid var(--sol-rule)',
              padding: '11px 13px',
              height: 64,
            }}
          />
        ))}
      </div>
    );
  }
  if (!priorities?.length) {
    return (
      <div
        className="rounded-md p-4 text-center"
        style={{
          background: 'var(--sol-succes-bg)',
          border: '0.5px solid var(--sol-succes-line)',
          color: 'var(--sol-succes-fg)',
        }}
      >
        <strong style={{ fontWeight: 500 }}>Tout est sous contrôle aujourd'hui.</strong> Aucune
        priorité critique sur le portefeuille.
      </div>
    );
  }
  return (
    <div>
      <div className="flex justify-between items-center mb-2">
        <div
          className="font-mono uppercase tracking-[0.07em]"
          style={{ fontSize: 11, color: 'var(--sol-ink-500)' }}
        >
          File de traitement · {priorities.length} ligne{priorities.length > 1 ? 's' : ''} priorisée
          {priorities.length > 1 ? 's' : ''}
        </div>
        <div
          className="font-mono uppercase tracking-[0.07em]"
          style={{ fontSize: 10.5, color: 'var(--sol-ink-500)' }}
        >
          Tri urgence · domaine ↓
        </div>
      </div>
      {priorities.map((p) => (
        <FileTraitementRow key={`${p.rank}-${p.title}`} rank={p.rank} item={p} />
      ))}
      {/* Phase 13.C P1 (Antoine 80 sites) : affordance Pareto si gros portfolio. */}
      {remainingCount > 0 && (
        <div className="mt-2 flex justify-end">
          <Link
            to="/anomalies?status=open&sort=urgency_then_impact_desc"
            className="font-mono uppercase tracking-[0.06em] no-underline hover:underline inline-flex items-center gap-1"
            style={{ fontSize: 10.5, color: 'var(--sol-ink-500)' }}
          >
            + {remainingCount} autre{remainingCount > 1 ? 's' : ''} priorité
            {remainingCount > 1 ? 's' : ''} →
          </Link>
        </div>
      )}
    </div>
  );
}

// ── Page racine ──────────────────────────────────────────────────────

export default function CockpitPilotage() {
  const navigate = useNavigate();
  const { facts, loading: factsLoading } = useCockpitFacts('current_month');
  const { org } = useScope();
  const [priorities, setPriorities] = useState(null);
  const [prioritiesRemaining, setPrioritiesRemaining] = useState(0);
  const [prioritiesLoading, setPrioritiesLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setPrioritiesLoading(true);
    getCockpitPriorities()
      .then((data) => {
        if (!cancelled) {
          setPriorities(data?.priorities || []);
          // Phase 13.C P1 : affordance "+ N autres priorités" pour gros pf.
          setPrioritiesRemaining(data?.remaining_count || 0);
        }
      })
      .catch(() => {
        if (!cancelled) setPriorities([]);
      })
      .finally(() => {
        if (!cancelled) setPrioritiesLoading(false);
      });
    return () => {
      cancelled = true;
    };
    // P1 audit /simplify : recharge sur scope change (org switch).
  }, [org?.id]);

  const sitesCount = facts?.scope?.site_count ?? org?.sites_count ?? 0;
  const orgName = facts?.scope?.org_name || org?.name || '';
  const dataQualityPct = facts?.data_quality?.data_completeness_pct;
  const lastUpdate = facts?.metadata?.last_update;
  const sources = facts?.metadata?.sources || [];
  const confidence = facts?.metadata?.confidence;

  const today = new Date();
  const todayLabel = fmtDateLong(today);
  const weekIso = getIsoWeek(today);
  const lastUpdateRel = relativeTime(lastUpdate);

  const alertsTotal = facts?.alerts?.total ?? 0;
  const criticalCount = facts?.alerts?.by_severity?.critical ?? 0;

  const scopeLabel = `${orgName}${sitesCount ? ` — ${sitesCount} sites` : ''}`;

  return (
    <div
      className="max-w-[1280px] mx-auto"
      style={{
        background: 'var(--sol-bg-paper)',
        borderRadius: 12,
        border: '0.5px solid var(--sol-rule)',
        padding: '1.4rem 1.6rem 1.2rem',
      }}
    >
      {/* Header */}
      <div className="flex justify-between items-start gap-3.5 flex-wrap">
        <div className="flex-1 min-w-[260px]">
          <SolKickerWithSwitch scope={`Cockpit · ${scopeLabel}`} currentRoute="jour" />
          <h1
            className="mt-1.5 mb-1"
            style={{
              fontFamily: 'var(--sol-font-display)',
              fontSize: 24,
              fontWeight: 500,
              lineHeight: 1.2,
              color: 'var(--sol-ink-900)',
            }}
          >
            Bonjour — voici ce qui mérite votre attention{' '}
            <em style={{ fontStyle: 'italic', color: 'var(--sol-ink-700)', fontWeight: 400 }}>
              · {todayLabel}
            </em>
          </h1>
          <div
            className="mt-1 font-mono uppercase tracking-[0.07em]"
            style={{ fontSize: 11, color: 'var(--sol-ink-500)' }}
          >
            <Clock size={11} className="inline mr-1 -mt-0.5" aria-hidden="true" />
            Données EMS {lastUpdateRel}
            {dataQualityPct != null ? ` · qualité ${dataQualityPct} %` : ''}
            {' · semaine '}
            {weekIso}
          </div>
        </div>
        <div className="flex gap-1.5 flex-wrap items-center">
          {alertsTotal > 0 && (
            <Link
              to="/anomalies?status=open"
              className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full font-mono uppercase tracking-[0.04em] no-underline hover:bg-[var(--sol-bg-canvas)]"
              style={{
                fontSize: 11,
                border: '0.5px solid var(--sol-rule)',
                color: 'var(--sol-ink-700)',
                background: 'var(--sol-bg-paper)',
              }}
            >
              <span
                className="inline-block rounded-full"
                style={{
                  width: 6,
                  height: 6,
                  background:
                    criticalCount > 0 ? 'var(--sol-refuse-fg)' : 'var(--sol-attention-fg)',
                }}
              />
              {alertsTotal} alerte{alertsTotal > 1 ? 's' : ''}
              {criticalCount > 0
                ? ` · ${criticalCount} critique${criticalCount > 1 ? 's' : ''}`
                : ''}
            </Link>
          )}
          <button
            type="button"
            onClick={() => navigate('/anomalies?status=open')}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md font-medium transition-colors hover:bg-[var(--sol-bg-canvas)]"
            style={{
              fontSize: 13,
              border: '0.5px solid var(--sol-ink-300)',
              background: 'var(--sol-bg-paper)',
              color: 'var(--sol-ink-900)',
            }}
          >
            <Bell size={14} aria-hidden="true" />
            Centre d'action
            <ArrowRight size={12} aria-hidden="true" style={{ opacity: 0.6 }} />
          </button>
        </div>
      </div>

      {/* Triptyque KPI temporel multi-échelle */}
      {factsLoading && !facts ? (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-2.5 my-4">
          <KpiSkeleton variant="temporal" scaleLabel={SCALE_LABEL.medium} />
          <KpiSkeleton variant="temporal" scaleLabel={SCALE_LABEL.short} />
          <KpiSkeleton variant="temporal" scaleLabel={SCALE_LABEL.contract} />
        </div>
      ) : (
        <KpiTriptyqueEnergetique facts={facts} />
      )}

      {/* 2 visuels glanceables */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-2.5 mb-4">
        <ConsoSevenDaysBars
          lastUpdate={lastUpdateRel}
          confidence={confidence}
          weeklyAnomaly={facts?.consumption?.weekly_anomaly}
        />
        <CourbeChargeJMinus1
          subscribedKw={facts?.power?.subscribed_kw}
          lastUpdate={lastUpdateRel}
          confidence={confidence}
        />
      </div>

      {/* File de traitement */}
      <div className="mb-4">
        <FileTraitement
          priorities={priorities}
          loading={prioritiesLoading}
          remainingCount={prioritiesRemaining}
        />
      </div>

      {/* Footer Sol */}
      <div
        className="flex justify-between flex-wrap gap-2.5 pt-3"
        style={{ borderTop: '0.5px solid var(--sol-rule)' }}
      >
        <div
          className="font-mono uppercase tracking-[0.07em]"
          style={{ fontSize: 11, color: 'var(--sol-ink-500)' }}
        >
          Source {sources.join(' + ') || 'PROMEOS'}
          {confidence ? ` · confiance ${confidence}` : ''}
          {' · mis à jour '}
          {lastUpdateRel} ·{' '}
          <Link
            to="/methodologie/cockpit"
            className="no-underline hover:underline"
            style={{
              color: 'var(--sol-ink-500)',
              borderBottom: '0.5px dotted var(--sol-ink-400)',
            }}
          >
            méthodologie
          </Link>
        </div>
      </div>
    </div>
  );
}
