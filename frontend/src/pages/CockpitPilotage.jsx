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
import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { Bell, ArrowRight, Clock } from 'lucide-react';

import useCockpitFacts from '../hooks/useCockpitFacts';
import SolKickerWithSwitch from '../ui/sol/SolKickerWithSwitch';
import AcronymTooltip from '../ui/sol/AcronymTooltip';
import KpiCard from '../components/cockpit/KpiCard';
import KpiSkeleton from '../components/cockpit/KpiSkeleton';
// Sprint Grammaire v1 Phase 2 BRIEFING — primitifs Sol v1.1 doctrine §5
import { DecisionEvidenceCard, SolPageFooter, Term } from '../components/grammar';
// Phase 3.0 P2 — adaptateurs canoniques action→DEC (SoT cross-vues)
// Phase 3.1 — toDecSeverityBriefing pour tonalité calme BRIEFING (audit UI 09/05)
import {
  buildEvidenceFallback,
  priorityLabel as decPriorityLabel,
  toDecSeverityBriefing,
} from '../components/grammar/decisionAdapters';
import { getCockpitPriorities } from '../services/api/cockpit';
import { useScope } from '../contexts/ScopeContext';
import { splitMwh, splitKw, fmtPct, fmtEurShort, deltaSeverity } from '../utils/format';
import { getIsoWeek, relativeTime, fmtDateLong } from '../utils/date';
import { confidenceTone, severityTone } from '../ui/sol/solTones';

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

// /simplify Phase 30+ : regex au scope module (réutilisées dans 2 IIFE).
// Évite la ré-allocation regex à chaque render et permet à useMemo de
// rester stable sur référence.
const REGEX_EARLY_MONTH = /\(j\s+1-(\d+)\)/;
const REGEX_J_MINUS_X = /^j-(\d+)$/;
// Phase 29 fallback acceptable = jour de mesure ≤ 3 jours
const PEAK_CONNECTOR_DAYS_THRESHOLD = 3;

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
  // Phase 29 (audit anomalies seed 2026-05-01) : si current_month_label
  // contient `(j 1-X)` avec X ≤ 3, on est en début de mois et la comparaison
  // vs N-1 est mathématiquement vraie mais business-faussée (0 MWh seedé
  // sur 1 jour ne dit rien sur la tendance mensuelle). On affiche un
  // état honnête "Données en cours d'agrégation" au lieu du delta 0 %.
  const monthlyEarlyMonth = useMemo(() => {
    if (!monthly.current_month_label) return null;
    const m = monthly.current_month_label.match(REGEX_EARLY_MONTH);
    if (!m) return null;
    const daysIn = parseInt(m[1], 10);
    return daysIn <= 3 ? daysIn : null;
  }, [monthly.current_month_label]);
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
  // Phase 29 : seuil "fallback acceptable" = 3 jours. Au-delà (peak_source
  // = j-7, j-30, j-99...), la mesure est trop ancienne pour être présentée
  // comme "synchro J-1 en cours" → on affiche un badge CONNECTEUR À
  // VÉRIFIER pour signaler honnêtement qu'il y a un problème de fraîcheur.
  // /simplify Phase 30+ : si format inconnu (`unknown`, `manual`...), on
  // retourne null et on déclenche le badge connecteur (audit code-reviewer
  // P1 : fallback silencieux à 1 cachait les formats inattendus).
  const peakDaysOld = useMemo(() => {
    const m = peakSource.match(REGEX_J_MINUS_X);
    return m ? parseInt(m[1], 10) : null;
  }, [peakSource]);
  const peakConnectorIssue = peakDaysOld === null || peakDaysOld > PEAK_CONNECTOR_DAYS_THRESHOLD;
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
        tooltip={
          monthlyEarlyMonth
            ? `Début de mois — ${monthlyEarlyMonth} jour(s) seedé(s) seulement. Comparaison vs N−1 différée jusqu'à 4+ jours pour rester honnête.`
            : monthlyTooltip
        }
        value={monthlySplit.value}
        unit={monthlySplit.unit}
        deltaText={
          // Phase 29 : si début de mois (≤ 3 jours), on suspend le delta
          // pour éviter d'afficher "0 % vs N−1" trompeur (numérateur 0/0).
          monthlyEarlyMonth
            ? null
            : monthlyDeltaPct != null
              ? `${fmtDeltaPct(monthlyDeltaPct)} vs ${previousYearLabel}`
              : null
        }
        deltaSev={monthlyEarlyMonth ? null : deltaSeverity(monthlyDeltaPct)}
        hint={
          monthlyEarlyMonth
            ? `Données en cours d'agrégation · ${monthlyEarlyMonth} jour(s) seedé(s)`
            : calibDate
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
            : peakConnectorIssue
              ? `⚠ Connecteur à vérifier · ${peakDaysOld === null ? `format ${peakSource} inattendu` : `dernière mesure il y a ${peakDaysOld} jours`} (souscrite ${splitKw(subscribedKw).value} ${splitKw(subscribedKw).unit})`
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

// Phase 26.bis (hot-fix UX 2026-05-01) : extraction des 7 valeurs jour pour
// permettre les tooltips `<title>` natifs au hover (avant : SVG sans
// info au survol). Les hauteurs sont préservées 1:1 pour ne pas régresser
// le rendu visuel V1. Les MWh sont calculés depuis l'échelle SVG :
// y=20 ⇒ 12 MWh / y=55 ⇒ 8 MWh / y=90 ⇒ 4 MWh / y=103 ⇒ 0 MWh.
// Cohérent avec backend `_facts.consumption.j_minus_1_mwh`/`surconso_7d_mwh` ;
// passage à un breakdown réel `_facts.consumption.weekly_breakdown[]` prévu
// Phase 27 (sortie placeholder).
// Phase 27 : `_CONSO_7D_DAYS` désormais utilisé seulement comme PLACEHOLDER
// (1er render avant que useCockpitFacts ait répondu). Quand le backend
// répond, `_projectBreakdownToBars` ci-dessous projette les vraies valeurs
// `_facts.consumption.weekly_breakdown[]` en bars dynamiques.
const _CONSO_7D_DAYS = [
  { letter: 'L', label: 'Lundi', x: 42, y: 48, h: 55 },
  { letter: 'M', label: 'Mardi', x: 84, y: 50, h: 53 },
  { letter: 'M', label: 'Mercredi', x: 126, y: 44, h: 59 },
  { letter: 'J', label: 'Jeudi', x: 168, y: 46, h: 57 },
  { letter: 'V', label: 'Vendredi', x: 210, y: 49, h: 54 },
  { letter: 'S', label: 'Samedi', x: 252, y: 22, h: 81, anomaly: true, deltaPct: 39 },
  { letter: 'D', label: 'Dimanche', x: 294, y: 55, h: 48, faded: true, lowConfidence: true },
];
const _CONSO_7D_Y_BASELINE = 103;
const _CONSO_7D_Y_TOP = 20;
// PLACEHOLDER — plancher minimum axe Y SVG (MWh) uniquement si weeklyBreakdown absent
// ou si toutes les valeurs réelles sont inférieures à ce seuil d'affichage.
// Le path data-driven (_projectBreakdownToBars) est prioritaire : il calcule
// Math.max(_CONSO_7D_MWH_TOP, ...valeurs_backend) pour une échelle dynamique.
// Ne pas interpréter comme seuil métier — pur paramètre de lisibilité SVG.
const _CONSO_7D_MWH_TOP = 12;
const _CONSO_7D_X_START = 42;
const _CONSO_7D_X_PITCH = 42;

function _conso7dMwh(y) {
  return (
    ((_CONSO_7D_Y_BASELINE - y) / (_CONSO_7D_Y_BASELINE - _CONSO_7D_Y_TOP)) * _CONSO_7D_MWH_TOP
  );
}

/** Phase 27 — projette `weekly_breakdown[]` backend en bars SVG.
 *  Échelle Y dynamique : max(MWh observé, 12) pour préserver la lisibilité
 *  même si tous les jours sont sous 12 MWh, et étire si un jour dépasse
 *  (ex: anomalie réelle). Retourne null si pas de breakdown (fallback
 *  placeholder). */
function _projectBreakdownToBars(breakdown) {
  if (!Array.isArray(breakdown) || breakdown.length === 0) return null;
  const maxMwh = Math.max(_CONSO_7D_MWH_TOP, ...breakdown.map((d) => d?.mwh || 0));
  return breakdown.map((d, idx) => {
    const ratio = maxMwh > 0 ? Math.max(0, Math.min(1, (d.mwh || 0) / maxMwh)) : 0;
    const h = Math.round((_CONSO_7D_Y_BASELINE - _CONSO_7D_Y_TOP) * ratio);
    const y = _CONSO_7D_Y_BASELINE - h;
    return {
      letter: d.day_letter || '?',
      label: d.day_label || '',
      dayIso: d.day_iso || '',
      x: _CONSO_7D_X_START + idx * _CONSO_7D_X_PITCH,
      y,
      h: Math.max(2, h), // hauteur min 2px pour rester visible si MWh ≈ 0
      mwh: d.mwh || 0,
      baselineMwh: d.baseline_mwh || 0,
      deltaPct: d.delta_pct || 0,
      anomaly: !!d.is_anomaly,
      faded: !!d.low_confidence,
      lowConfidence: !!d.low_confidence,
    };
  });
}

function ConsoSevenDaysBars({ lastUpdate, confidence, weeklyAnomaly, weeklyBreakdown }) {
  // Phase 27 : si le backend a fourni `weekly_breakdown`, on rend les vraies
  // valeurs MWh ; sinon fallback placeholder Phase 26.bis (pour le 1er render
  // avant que useCockpitFacts ait répondu).
  const projected = _projectBreakdownToBars(weeklyBreakdown);
  const days = projected || _CONSO_7D_DAYS;
  const isDataDriven = projected !== null;
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
    'Pic anormal de la semaine en rouge · scan visuel 5 secondes. Survolez chaque barre pour le détail.'
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
        {/* Phase 27 : si `weeklyBreakdown` backend dispo (isDataDriven=true),
            on rend les vraies valeurs MWh + delta vs baseline. Sinon fallback
            placeholder Phase 26.bis. Tooltip <title> identique dans les 2 cas. */}
        {days.map((day) => {
          // En data-driven : MWh = day.mwh réel ; en placeholder : inférence pixel.
          const mwh = isDataDriven ? day.mwh : _conso7dMwh(day.y);
          const mwhLabel = `${mwh.toFixed(1).replace('.', ',')} MWh`;
          // Phase 27 : delta réel + nom complet jour + date ISO si data-driven.
          const dateSuffix =
            isDataDriven && day.dayIso
              ? ` (${new Date(day.dayIso).toLocaleDateString('fr-FR', { day: '2-digit', month: 'short' })})`
              : '';
          const deltaPart =
            day.anomaly && day.deltaPct !== 0
              ? ` — anomalie ${day.deltaPct > 0 ? '+ ' : '− '}${Math.abs(day.deltaPct)} % vs baseline`
              : day.lowConfidence
                ? ' — confiance faible (jour non ouvré)'
                : '';
          const baselinePart =
            isDataDriven && day.baselineMwh > 0
              ? ` · baseline ${day.baselineMwh.toFixed(1).replace('.', ',')} MWh`
              : '';
          const tooltipText = `${day.label}${dateSuffix} : ${mwhLabel}${baselinePart}${deltaPart}`;
          let fill = 'var(--sol-calme-fg)';
          let fillOpacity = 1;
          if (day.anomaly) fill = 'var(--sol-refuse-fg)';
          if (day.faded) fillOpacity = 0.5;
          const width = day.lowConfidence ? 22 : 32;
          return (
            <rect
              key={day.letter + day.x}
              x={day.x}
              y={day.y}
              width={width}
              height={day.h}
              rx="2"
              fill={fill}
              fillOpacity={fillOpacity}
              style={{ cursor: 'help' }}
            >
              <title>{tooltipText}</title>
            </rect>
          );
        })}
        {/* Phase 27 : labels delta + lettres jour rendus depuis le data set
            (vrai delta % des anomalies au lieu de "+ 39 %" hardcodé). */}
        {days
          .filter((d) => d.anomaly && d.deltaPct !== 0)
          .map((day) => (
            <text
              key={`anom-${day.x}`}
              x={day.x + 16}
              y="14"
              textAnchor="middle"
              fontSize="9"
              fontWeight="500"
              fill="var(--sol-refuse-fg)"
            >
              {day.deltaPct > 0 ? '+ ' : '− '}
              {Math.abs(day.deltaPct)}
              {' %'}
            </text>
          ))}
        <g
          fontFamily="var(--sol-font-mono)"
          fontSize="9"
          fill="currentColor"
          fillOpacity=".55"
          textAnchor="middle"
        >
          {days.map((day) => {
            const isAnomaly = day.anomaly;
            return (
              <text
                key={`label-${day.x}`}
                x={day.x + 16}
                y="120"
                fontWeight={isAnomaly ? '500' : undefined}
                fill={isAnomaly ? 'var(--sol-refuse-fg)' : undefined}
                fillOpacity={isAnomaly ? 1 : undefined}
              >
                {day.letter}
              </text>
            );
          })}
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

// Phase 27.bis (hot-fix UX 2026-05-01) — points clés courbe charge J-1 pour
// tooltips natifs au hover (avant : courbe path SVG sans aucune info au
// survol, signalé par utilisateur même symptôme que Conso 7 jours).
// Format : [{ x, y, hour, kw_ratio, label }] où kw_ratio = fraction de
// puissance souscrite (0.0 à 1.0), label = heure au format "8 h".
// Le path SVG actuel est placeholder (coordonnées hardcodées HP/HC) —
// passage à un breakdown réel `_facts.power.hourly_breakdown[]` prévu
// followup Phase 31 (cohérent avec Phase 27 weekly_breakdown).
const _CHARGE_J1_KEY_POINTS = [
  { x: 36, y: 90, hour: '0 h', kwRatio: 0.0, period: 'HC' },
  { x: 86, y: 80, hour: '4 h', kwRatio: 0.18, period: 'HC' },
  { x: 114, y: 46, hour: '8 h', kwRatio: 0.79, period: 'HP' },
  { x: 142, y: 42, hour: '10 h', kwRatio: 0.86, period: 'HP' },
  { x: 170, y: 58, hour: '12 h', kwRatio: 0.57, period: 'HP' },
  { x: 198, y: 46, hour: '14 h', kwRatio: 0.79, period: 'HP' },
  { x: 226, y: 46, hour: '16 h', kwRatio: 0.79, period: 'HP' },
  { x: 254, y: 56, hour: '17 h', kwRatio: 0.61, period: 'HP' },
  { x: 282, y: 76, hour: '19 h', kwRatio: 0.25, period: 'HP' },
  { x: 304, y: 86, hour: '20 h', kwRatio: 0.07, period: 'HP→HC' },
  { x: 340, y: 95, hour: '23 h', kwRatio: 0.0, period: 'HC' },
];

// /simplify Phase 30+ : peak constant immuable (input never changes)
// → hoist au scope module pour éviter le reduce à chaque render.
const _CHARGE_J1_PEAK_POINT = _CHARGE_J1_KEY_POINTS.reduce(
  (best, p) => (p.kwRatio > best.kwRatio ? p : best),
  _CHARGE_J1_KEY_POINTS[0]
);

// Phase 31 : geom SVG pour la courbe data-driven (24h plot area).
// L'axe Y est dynamique (max kW observé) ; l'axe X est divisé en 24
// buckets uniformes entre x_min et x_max.
const _CHARGE_J1_X_MIN = 36;
const _CHARGE_J1_X_MAX = 340;
const _CHARGE_J1_Y_BASELINE = 90; // y=90 = 0 kW
const _CHARGE_J1_Y_TOP = 22; // y=22 = max kW (= souscrite)

/** Phase 31 — projette `power.hourly_breakdown[]` (24 entries) en path SVG.
 *  Échelle Y dynamique : max(kw observé, subscribed_kw) pour préserver la
 *  ligne souscrite visible. Retourne `null` si pas de breakdown
 *  (fallback placeholder). */
function _projectHourlyToPath(hourlyBreakdown, subscribedKw) {
  if (!Array.isArray(hourlyBreakdown) || hourlyBreakdown.length === 0) return null;
  const maxKw = Math.max(subscribedKw || 0, ...hourlyBreakdown.map((h) => h.kw || 0));
  if (maxKw <= 0) return null;
  const xRange = _CHARGE_J1_X_MAX - _CHARGE_J1_X_MIN;
  const yRange = _CHARGE_J1_Y_BASELINE - _CHARGE_J1_Y_TOP;
  return hourlyBreakdown.map((h, idx) => {
    const ratio = (h.kw || 0) / maxKw;
    const x = _CHARGE_J1_X_MIN + (idx / 23) * xRange; // 23 = 24-1 (intervalles)
    const y = _CHARGE_J1_Y_BASELINE - ratio * yRange;
    return {
      x: Math.round(x * 10) / 10,
      y: Math.round(y * 10) / 10,
      kw: h.kw || 0,
      kwRatio: h.kw_ratio || (subscribedKw > 0 ? h.kw / subscribedKw : 0),
      hour: h.hour_label || `${h.hour} h`,
      hourNum: h.hour,
      period: h.period || 'HP',
    };
  });
}

function CourbeChargeJMinus1({ subscribedKw, lastUpdate, confidence, hourlyBreakdown }) {
  const subSplit = splitKw(subscribedKw);
  // Phase 31 : si breakdown backend dispo, on projette les vraies kW.
  // Sinon fallback placeholder Phase 27.bis (pour 1er render avant fetch).
  const projected = _projectHourlyToPath(hourlyBreakdown, subscribedKw);
  const isDataDriven = projected !== null;
  const keyPoints = projected || _CHARGE_J1_KEY_POINTS;
  const peakPoint = isDataDriven
    ? keyPoints.reduce((best, p) => (p.kwRatio > best.kwRatio ? p : best), keyPoints[0])
    : _CHARGE_J1_PEAK_POINT;
  const peakKw = isDataDriven
    ? peakPoint.kw
    : subscribedKw != null
      ? subscribedKw * peakPoint.kwRatio
      : null;
  const peakKwLabel =
    peakKw != null
      ? subSplit.unit === 'MW'
        ? `${(peakKw / 1000).toFixed(2).replace('.', ',')} MW`
        : `${Math.round(peakKw)} kW`
      : '—';
  const margePct = subscribedKw && peakKw ? Math.round((1 - peakKw / subscribedKw) * 100) : null;
  const summaryTitle =
    subscribedKw != null
      ? `Pic ${peakKwLabel} à ${peakPoint.hour} · souscrite ${subSplit.value} ${subSplit.unit} · marge ${margePct >= 0 ? '+' : ''}${margePct} %`
      : 'Courbe de charge J-1 — données indisponibles';

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
            Courbe de charge J−1 · groupe · {subSplit.unit || 'kW'}
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
      {/* Phase 14.bis (régression utilisateur 29/04 fin Phase 14) :
          - viewBox élargi 360×140 + plot-area 36→340 pour libérer marge gauche
            (axe Y kW) et marge droite (label "22 h" clipped en textAnchor middle
            à x=320 = bord viewBox).
          - Ajout axe Y avec graduations kW/MW (4 ticks : 0 / souscrite × 0.33 /
            ×0.66 / souscrite). Référence visible = la dashed rouge P. souscrite.
          - Axe X : "0 h" textAnchor=start, "22 h" textAnchor=end pour éviter
            tout débordement viewBox sur extrémités.
          - "P. souscrite X MW" déplacé à droite avec padding (x=336 textAnchor=end). */}
      <svg
        viewBox="0 0 360 140"
        xmlns="http://www.w3.org/2000/svg"
        style={{ width: '100%', height: 'auto', display: 'block', marginTop: 6, cursor: 'help' }}
        role="img"
        aria-label="Courbe de charge J moins 1 du groupe"
      >
        {/* Phase 27.bis hot-fix : tooltip natif global au survol du SVG. */}
        <title>{summaryTitle}</title>
        <defs>
          <linearGradient id="hp-fill-pilotage" x1="0" x2="0" y1="0" y2="1">
            <stop offset="0%" stopColor="var(--sol-hpe-fg)" stopOpacity=".18" />
            <stop offset="100%" stopColor="var(--sol-hpe-fg)" stopOpacity="0" />
          </linearGradient>
        </defs>
        {/* HC zones (matin avant 8h + soir après 22h) : background grisé */}
        <rect x="36" y="10" width="50" height="95" fill="var(--sol-hch-fg)" fillOpacity=".05" />
        <rect x="304" y="10" width="36" height="95" fill="var(--sol-hch-fg)" fillOpacity=".05" />
        {/* Grid horizontale (3 niveaux de référence) */}
        <line
          x1="36"
          y1="20"
          x2="340"
          y2="20"
          stroke="currentColor"
          strokeOpacity=".08"
          strokeDasharray="2,3"
        />
        <line
          x1="36"
          y1="55"
          x2="340"
          y2="55"
          stroke="currentColor"
          strokeOpacity=".08"
          strokeDasharray="2,3"
        />
        <line
          x1="36"
          y1="90"
          x2="340"
          y2="90"
          stroke="currentColor"
          strokeOpacity=".15"
          strokeDasharray="3,3"
        />
        {/* Ligne souscrite + label déporté à droite */}
        <line
          x1="36"
          y1="34"
          x2="340"
          y2="34"
          stroke="var(--sol-refuse-fg)"
          strokeOpacity=".55"
          strokeDasharray="3,3"
          strokeWidth="1"
        />
        <text
          x="338"
          y="30"
          textAnchor="end"
          fontFamily="var(--sol-font-mono)"
          fontSize="8.5"
          fill="var(--sol-refuse-fg)"
          fillOpacity=".85"
        >
          P. souscrite {subscribedKw != null ? `${subSplit.value} ${subSplit.unit}` : '—'}
        </text>
        {/* Phase 14.bis — Axe Y avec graduations (4 ticks). Source ligne souscrite
            comme référence (= y=34). 0 kW = y=90 (baseline). */}
        {(() => {
          const ySouscrite = 34;
          const yZero = 90;
          const ratio = (frac) => yZero - (yZero - ySouscrite) * frac;
          const subVal = subscribedKw != null ? Number(subSplit.value.replace(',', '.')) || 0 : 0;
          const fmt = (v) => {
            if (subSplit.unit === 'MW') return `${v.toFixed(2)}`;
            return `${Math.round(v)}`;
          };
          return (
            <g
              fontFamily="var(--sol-font-mono)"
              fontSize="8"
              fill="currentColor"
              fillOpacity=".5"
              textAnchor="end"
            >
              <text x="32" y={yZero + 3}>
                0
              </text>
              <text x="32" y={ratio(0.33) + 3}>
                {fmt(subVal * 0.33)}
              </text>
              <text x="32" y={ratio(0.66) + 3}>
                {fmt(subVal * 0.66)}
              </text>
              <text x="32" y={ySouscrite + 3}>
                {subSplit.value}
              </text>
              {/* Unité affichée en kicker au-dessus de l'axe */}
              <text x="32" y="14" fillOpacity=".7" fontSize="7.5">
                {subSplit.unit || 'kW'}
              </text>
            </g>
          );
        })()}
        {/* Phase 31 : 3 paths SVG calculés depuis keyPoints (data-driven si
            backend hourly_breakdown dispo, sinon fallback placeholder). On
            sépare HC matin (avant 7h), HP journée (7h-21h), HC soir (>=22h)
            pour conserver les 2 couleurs distinctes contractuelles. */}
        {(() => {
          // Helpers : segments par période + path d
          const toL = (pts) =>
            pts.length > 0
              ? `M${pts[0].x},${pts[0].y} ` +
                pts
                  .slice(1)
                  .map((p) => `L${p.x},${p.y}`)
                  .join(' ')
              : '';
          // Indices par période (24 entries data-driven, ou les 11 placeholder)
          const hcMorning = keyPoints.filter((p) => {
            const h =
              p.hourNum != null ? p.hourNum : parseInt((p.hour || '0').replace(' h', ''), 10);
            return !Number.isNaN(h) && h <= 7;
          });
          const hpDay = keyPoints.filter((p) => {
            const h =
              p.hourNum != null ? p.hourNum : parseInt((p.hour || '0').replace(' h', ''), 10);
            return !Number.isNaN(h) && h >= 7 && h <= 21;
          });
          const hcEvening = keyPoints.filter((p) => {
            const h =
              p.hourNum != null ? p.hourNum : parseInt((p.hour || '0').replace(' h', ''), 10);
            return !Number.isNaN(h) && h >= 21;
          });
          // Aire HP sous la courbe : ferme le path en bas (y=baseline+2 pour
          // descendre sous la grille).
          const hpAreaPts = hpDay;
          const hpAreaD =
            hpAreaPts.length > 0
              ? `${toL(hpAreaPts)} L${hpAreaPts[hpAreaPts.length - 1].x},${_CHARGE_J1_Y_BASELINE + 15} L${hpAreaPts[0].x},${_CHARGE_J1_Y_BASELINE + 15} Z`
              : '';
          return (
            <>
              <path d={hpAreaD} fill="url(#hp-fill-pilotage)" fillOpacity=".7" />
              <path d={toL(hcMorning)} fill="none" stroke="var(--sol-hch-fg)" strokeWidth="1.6" />
              <path d={toL(hpDay)} fill="none" stroke="var(--sol-hpe-fg)" strokeWidth="1.6" />
              <path d={toL(hcEvening)} fill="none" stroke="var(--sol-hch-fg)" strokeWidth="1.6" />
            </>
          );
        })()}
        {/* Axe X (heures) */}
        <g fontFamily="var(--sol-font-mono)" fontSize="9" fill="currentColor" fillOpacity=".55">
          <text x="36" y="125" textAnchor="start">
            0 h
          </text>
          <text x="114" y="125" textAnchor="middle">
            8 h
          </text>
          <text x="188" y="125" textAnchor="middle">
            12 h
          </text>
          <text x="262" y="125" textAnchor="middle">
            18 h
          </text>
          <text x="340" y="125" textAnchor="end">
            22 h
          </text>
        </g>
        {/* Phase 27.bis + 31 : cercles invisibles aux points clés pour
            tooltips natifs <title> au hover. En mode data-driven (24 points),
            on rend 1 cercle par heure ; en placeholder, 11 points clés. */}
        {keyPoints.map((p) => {
          // Phase 31 : si data-driven, kw vient du backend ; sinon calcul
          // depuis kwRatio × subscribed.
          const ptKw = isDataDriven ? p.kw : subscribedKw != null ? subscribedKw * p.kwRatio : null;
          const ptKwLabel =
            ptKw != null
              ? subSplit.unit === 'MW'
                ? `${(ptKw / 1000).toFixed(2).replace('.', ',')} MW`
                : `${Math.round(ptKw)} kW`
              : '—';
          const tooltipText = `${p.hour} (${p.period}) : ${ptKwLabel}${
            subscribedKw != null && ptKw != null
              ? ` · ${Math.round((ptKw / subscribedKw) * 100)} % de la souscrite`
              : ''
          }`;
          return (
            <circle
              key={`pt-${p.x}`}
              cx={p.x}
              cy={p.y}
              r="6"
              fill="transparent"
              style={{ cursor: 'help' }}
            >
              <title>{tooltipText}</title>
            </circle>
          );
        })}
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
  // Audit Phase 3.0 P2 (simplify 09/05) : ancien mapping inline shadow le
  // helper canonique `confidenceTone()` de solTones.js (consommé par KpiCard
  // et SOL_CONFIDENCE_TONES SoT). Refacto pour utiliser la SoT — élimine
  // la duplication 3-niveaux + rapproche d'un futur source-guard CI.
  const confidenceBadge = item.confidence_badge;
  const confTone = confidenceBadge ? confidenceTone(confidenceBadge) : null;
  const confidenceLabel = confTone?.label || null;
  const confTonePill = confTone ? { bg: confTone.bg, fg: confTone.fg } : null;
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
              {confidenceLabel && confTonePill && (
                <span
                  className="inline-flex items-center px-1 py-0 rounded font-mono uppercase tracking-[0.06em]"
                  style={{
                    fontSize: 9,
                    background: confTonePill.bg,
                    color: confTonePill.fg,
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
  // Audit Phase 3.0 P0 (CX 09/05) : ancien catch silencieux `setPriorities([])`
  // affichait "0 décision" comme si l'utilisateur était en règle alors que
  // l'API était en erreur — anti-pattern §6.5 doctrine ("backend réactif
  // qui mensonge"). On expose désormais l'erreur pour rendu ErrorState.
  const [prioritiesError, setPrioritiesError] = useState(null);
  const [searchParams] = useSearchParams();

  const fetchPriorities = useCallback(() => {
    let cancelled = false;
    setPrioritiesLoading(true);
    setPrioritiesError(null);
    getCockpitPriorities()
      .then((data) => {
        if (cancelled) return;
        setPriorities(data?.priorities || []);
        setPrioritiesRemaining(data?.remaining_count || 0);
      })
      .catch((err) => {
        if (cancelled) return;
        // P0 anti-silent : on garde priorities=null pour distinguer "pas encore
        // chargé" (skeleton) de "erreur" (ErrorState avec retry).
        setPrioritiesError(err?.message || 'Impossible de charger les priorités');
        setPriorities(null);
      })
      .finally(() => {
        if (!cancelled) setPrioritiesLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    return fetchPriorities();
    // P1 audit /simplify : recharge sur scope change (org switch).
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [org?.id]);

  // Phase 17.bis.D — drill-down depuis Vue exécutive (`?focus=action-{id}`
  // ou `?focus=decision-{rank}`). Audit Phase 17 nav P0 : la cible était
  // câblée côté Décision mais Pilotage ignorait le query param. Désormais :
  // scroll-to-anchor si l'élément #decision-{rank} ou #action-{id} existe.
  useEffect(() => {
    if (prioritiesLoading) return;
    const focus = searchParams.get('focus');
    if (!focus) return;
    // Anchors actuels : `decision-{rank}` (rendus par FileTraitementRow).
    // Format accepté : "action-{id}" ou "decision-{rank}" — fallback brut.
    const targetIds = [focus, focus.replace('action-', 'decision-')];
    let t2 = null;
    const tryScroll = () => {
      for (const id of targetIds) {
        const el = document.getElementById(id);
        if (el) {
          el.scrollIntoView({ behavior: 'smooth', block: 'center' });
          el.style.outline = '2px solid var(--sol-attention-fg)';
          t2 = setTimeout(() => {
            el.style.outline = '';
          }, 2400);
          return true;
        }
      }
      return false;
    };
    // Petit délai pour laisser le DOM se hydrater.
    const t = setTimeout(tryScroll, 200);
    return () => {
      clearTimeout(t);
      if (t2) clearTimeout(t2);
    };
  }, [searchParams, prioritiesLoading]);

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

  /**
   * Architecture BRIEFING (Sprint Grammaire v1 Phase 3.1 visual refonte 09/05) :
   *
   *   1. SITUATION       → SolKickerWithSwitch + H1 Fraunces + sous-ligne mono Term EMS
   *   2. NARRATIVE       → 60 mots chiffrés (priorités + exposition + sources)
   *   3. CONTEXTE        → boutons alertes + Centre d'action (raccourcis)
   *   4. DÉCISION        → Top 3 DecisionEvidenceCard ranked par impact € (CARDINAL)
   *                        Tonalité calme via toDecSeverityBriefing (critical → warning)
   *   5. PREUVE TECHNIQUE → KpiTriptyqueEnergetique + 2 visuels glanceables
   *   6. DRILL-DOWN      → File P1-P5 détaillée (vue exhaustive)
   *   7. PROVENANCE      → SolPageFooter SCM (Source · Confiance · Mis à jour)
   *
   * Phase 3.1 changement narratif : DÉCISIONS remontées AVANT la preuve
   * technique (KPI/visuels) — réponse à audit UI Phase 3d "page commence par
   * grille KPI" (anti-pattern §6.1) + vision "le produit murmure la décision
   * juste, pas l'alerte".
   *
   * Briques conservées (Lego intactes) : SolKickerWithSwitch, useCockpitFacts,
   * getCockpitPriorities, KpiTriptyqueEnergetique, ConsoSevenDaysBars,
   * CourbeChargeJMinus1, FileTraitement.
   *
   * Briques nouvelles (primitifs Sol grammar/) : DecisionEvidenceCard, Term,
   * SolPageFooter — primitifs Phase 1 industrialisés. decisionAdapters SoT
   * (toDecSeverityBriefing + buildEvidenceFallback + priorityLabel).
   *
   * Tonalité : calme par défaut (rouge réservé aux exceptions vraies).
   */
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
      {/* ──────────────────────────────────────────────────────────────────
          1. SITUATION + 2. NARRATIVE — header narratif BRIEFING
          ────────────────────────────────────────────────────────────────── */}
      <header className="flex justify-between items-start gap-3.5 flex-wrap">
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
            data-hero
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
            Données <Term acronyme="EMS" /> {lastUpdateRel}
            {dataQualityPct != null ? ` · qualité ${dataQualityPct} %` : ''}
            {' · semaine '}
            {weekIso}
          </div>
          {/* Narrative briefing 2-3 lignes 60 mots max — doctrine §5. */}
          {(priorities?.length > 0 || alertsTotal > 0) && (
            <p
              className="mt-2.5 max-w-[760px]"
              style={{
                fontSize: 13.5,
                lineHeight: 1.5,
                color: 'var(--sol-ink-700)',
                fontFamily: 'var(--sol-font-system)',
              }}
              data-testid="cockpit-jour-briefing-narrative"
            >
              {priorities?.length > 0 && (
                <>
                  {priorities.length === 1
                    ? '1 décision prioritaire'
                    : `${priorities.length} décisions prioritaires`}
                  {criticalCount > 0
                    ? criticalCount === 1
                      ? ' dont 1 critique'
                      : ` dont ${criticalCount} critiques`
                    : ''}{' '}
                  à arbitrer cette semaine.{' '}
                </>
              )}
              {facts?.exposure?.total?.value_eur > 0 && (
                <>
                  Exposition financière consolidée :{' '}
                  <strong style={{ color: 'var(--sol-ink-900)' }}>
                    {fmtEurShort(facts.exposure.total.value_eur)}
                  </strong>
                  .{' '}
                </>
              )}
              <span className="font-mono" style={{ fontSize: 11.5 }}>
                Sources : <Term acronyme="EMS" /> · <Term acronyme="CRE" /> ·{' '}
                <Term acronyme="ADEME" />.
              </span>
            </p>
          )}
        </div>
        {/* 3. CONTEXTE — raccourcis alertes + Centre d'action */}
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
      </header>

      {/* ──────────────────────────────────────────────────────────────────
          4. DÉCISION — Top 3 DecisionEvidenceCard CARDINAL BRIEFING
          Phase 3.1 (audit UI 09/05) : DEC remontées EN PREMIER après le
          header narratif. Réponse à l'anti-pattern §6.1 "page commence par
          grille KPI sans préambule" — désormais la page commence par les
          DÉCISIONS à arbitrer (cardinal pour energy manager 30s).
          Tonalité calme : `toDecSeverityBriefing()` mappe critical → warning
          (ambré) — le rouge est réservé aux exceptions vraies.
          (Doctrine §5.6 Loi L9 : 4-8 cellules evidence enrichies backend.)
          Audit Phase 3.0 P0 : ErrorState anti-silent-fail si l'API échoue.
          ────────────────────────────────────────────────────────────────── */}
      {prioritiesError && !prioritiesLoading && (
        <section className="mb-4" data-testid="cockpit-jour-top-decisions-error">
          <div
            className="rounded-md p-4 text-sm"
            style={{
              background: 'var(--sol-attention-bg)',
              border: '0.5px solid var(--sol-attention-line)',
              color: 'var(--sol-attention-fg)',
            }}
            role="alert"
          >
            <strong>Priorités indisponibles.</strong> {prioritiesError}.{' '}
            <button
              type="button"
              onClick={fetchPriorities}
              className="underline ml-1"
              style={{ color: 'var(--sol-attention-fg)' }}
            >
              Réessayer
            </button>
          </div>
        </section>
      )}
      {priorities && priorities.length > 0 && (
        <section className="mb-4" data-testid="cockpit-jour-top-decisions">
          <h2
            className="font-mono uppercase tracking-[0.07em] mb-2"
            style={{ fontSize: 10.5, color: 'var(--sol-ink-500)' }}
          >
            Top {Math.min(3, priorities.length)} décision
            {Math.min(3, priorities.length) > 1 ? 's' : ''} à arbitrer
          </h2>
          <div className="grid grid-cols-1 gap-3">
            {priorities.slice(0, 3).map((p) => (
              <DecisionEvidenceCard
                key={p.rank}
                rang={p.rank}
                category={(p.category_label || p.domain || 'ACTION').toUpperCase()}
                scope={p.scope_label || 'PORTEFEUILLE'}
                severity={toDecSeverityBriefing(p.urgency)}
                titre={<>{p.title}</>}
                lead={p.lead || ''}
                evidence={
                  p.evidence_cells ||
                  buildEvidenceFallback({
                    impactDisplay: p.impact_value_eur ? fmtEurShort(p.impact_value_eur) : null,
                    category: p.category_label,
                    priorityLabel: decPriorityLabel(p.urgency),
                    rang: p.rank,
                    domain: p.domain,
                  })
                }
                primaryCta={{ label: "Voir l'action", href: p.action_url }}
                methodologyRef={p.methodology_ref || '/methodologie/cockpit'}
              />
            ))}
          </div>
        </section>
      )}

      {/* ──────────────────────────────────────────────────────────────────
          5. PREUVE TECHNIQUE — Triptyque KPI temporel + 2 visuels glanceables
          Phase 3.1 (audit UI 09/05) : descendus APRÈS les DÉCISIONS car ils
          sont la PREUVE technique de la situation, pas le pitch initial.
          Le triptyque KPI (Conso J-1 / mois DJU / pic kW) reste cardinal
          pour l'energy manager qui veut le détail technique.
          ────────────────────────────────────────────────────────────────── */}
      {factsLoading && !facts ? (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-2.5 my-4">
          <KpiSkeleton variant="temporal" scaleLabel={SCALE_LABEL.medium} />
          <KpiSkeleton variant="temporal" scaleLabel={SCALE_LABEL.short} />
          <KpiSkeleton variant="temporal" scaleLabel={SCALE_LABEL.contract} />
        </div>
      ) : (
        <KpiTriptyqueEnergetique facts={facts} />
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-2.5 mb-4">
        <ConsoSevenDaysBars
          lastUpdate={lastUpdateRel}
          confidence={confidence}
          weeklyAnomaly={facts?.consumption?.weekly_anomaly}
          weeklyBreakdown={facts?.consumption?.weekly_breakdown}
        />
        <CourbeChargeJMinus1
          subscribedKw={facts?.power?.subscribed_kw}
          lastUpdate={lastUpdateRel}
          confidence={confidence}
          hourlyBreakdown={facts?.power?.hourly_breakdown}
        />
      </div>

      {/* ──────────────────────────────────────────────────────────────────
          7. DRILL-DOWN — File de traitement P1-P5 détaillée (preuve actionnable)
          ────────────────────────────────────────────────────────────────── */}
      <div className="mb-4">
        <FileTraitement
          priorities={priorities}
          loading={prioritiesLoading}
          remainingCount={prioritiesRemaining}
        />
      </div>

      {/* ──────────────────────────────────────────────────────────────────
          8. PROVENANCE — SolPageFooter SCM (Loi L6 doctrine §5)
          ────────────────────────────────────────────────────────────────── */}
      <SolPageFooter
        source={sources.join(' + ') || 'PROMEOS'}
        confidence={confidence || 'medium'}
        updatedAt={lastUpdate}
        methodologyUrl="/methodologie/cockpit"
      />
    </div>
  );
}
