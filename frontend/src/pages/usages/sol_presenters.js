/**
 * PROMEOS — UsagesSol presenters (Lot 2 Phase 5, Pattern A hybride)
 *
 * Helpers purs pour l'injection Sol en haut de /usages.
 *
 * API consommée (parent UsagesDashboardPage.jsx) :
 *   getScopedUsagesDashboard() → {
 *     summary: { total_kwh, total_eur, total_surface_m2,
 *                elec_share_pct?, gaz_share_pct? },
 *     top_ues: [{ label, kwh, pct_of_total, ipe_kwh_m2,
 *                 data_source, is_significant, trend? }],
 *     baselines: [{ label, kwh_baseline, kwh_current,
 *                   ecart_kwh, ecart_pct, trend }],
 *     readiness: { score (0-100), level, details, recommendations },
 *     sites_count
 *   }
 *
 * IMPORTANT — divergences spec user → API réelle :
 *   - `efficiency_potential_mwh` spec → ABSENT côté getScopedUsagesDashboard.
 *     KPI 3 remappé → Score readiness (qualité segmentation données
 *     usages). Honnête vs inventer un chiffre d'économies fantôme.
 */
import { NBSP, formatFR, formatFREur } from '../cockpit/sol_presenters';
import { businessErrorFallback } from '../../i18n/business_errors';

export { NBSP, formatFR, formatFREur };

// ─────────────────────────────────────────────────────────────────────────────
// Kicker + narratives
// ─────────────────────────────────────────────────────────────────────────────

export function buildUsagesKicker({ scopeLabel, nbUsages } = {}) {
  const scope = scopeLabel ? scopeLabel.toUpperCase() : 'PATRIMOINE';
  const n = Number(nbUsages) || 0;
  return `USAGES · ${scope} · ${n}${NBSP}SEGMENTÉ${n > 1 ? 'S' : ''}`;
}

export function buildUsagesNarrative({ dashboard } = {}) {
  if (!dashboard) {
    return 'Segmentation des usages énergétiques en cours de calcul — données de comptage requises sur plus de 30 jours.';
  }
  const top = Array.isArray(dashboard.top_ues) && dashboard.top_ues.length > 0
    ? dashboard.top_ues[0]
    : null;
  const totalKwh = Number(dashboard.summary?.total_kwh) || 0;
  const totalMwh = Math.round(totalKwh / 1000);

  const parts = [];
  if (top) {
    const pct = Number(top.pct_of_total) || 0;
    parts.push(
      `${top.label} représente ${Math.round(pct)}${NBSP}% de votre consommation patrimoine`
    );
  }
  if (totalMwh > 0) {
    parts.push(`${formatFR(totalMwh, 0)}${NBSP}MWh cumulés sur 12${NBSP}mois`);
  }
  const totalEur = Number(dashboard.summary?.total_eur) || 0;
  if (totalEur > 0) {
    parts.push(`coût ${formatFREur(Math.round(totalEur), 0)}/an`);
  }
  // Baseline écart le plus marquant
  const worstBaseline = (dashboard.baselines || [])
    .filter((b) => Math.abs(Number(b.ecart_pct) || 0) >= 10)
    .sort((a, b) => Math.abs(Number(b.ecart_pct) || 0) - Math.abs(Number(a.ecart_pct) || 0))[0];
  if (worstBaseline) {
    const ecart = Math.round(Number(worstBaseline.ecart_pct) || 0);
    if (ecart > 0) {
      parts.push(`${worstBaseline.label} +${ecart}${NBSP}% vs baseline`);
    } else {
      parts.push(`${worstBaseline.label} ${ecart}${NBSP}% vs baseline`);
    }
  }
  if (parts.length === 0) {
    return 'Données d\'usages en cours d\'agrégation — segmentation complète disponible sous 7 jours.';
  }
  return parts.join(' · ') + '.';
}

export function buildUsagesSubNarrative({ dashboard } = {}) {
  const readiness = Number(dashboard?.readiness?.score);
  const level = dashboard?.readiness?.level;
  const parts = ['Sources : compteurs temps réel + benchmarks archétype ADEME OID 2024'];
  if (Number.isFinite(readiness)) {
    parts.push(`fiabilité données ${readiness}${NBSP}/${NBSP}100${level ? ` · ${level}` : ''}`);
  }
  return parts.join(' · ') + '.';
}

// ─────────────────────────────────────────────────────────────────────────────
// KPI interpretations
// ─────────────────────────────────────────────────────────────────────────────

export function interpretUsageDominant({ dashboard } = {}) {
  const top = dashboard?.top_ues?.[0];
  if (!top) return 'Aucun usage dominant identifié — segmentation en attente.';
  const kwh = Number(top.kwh) || 0;
  const mwh = kwh > 0 ? Math.round(kwh / 1000) : null;
  const ipe = Number(top.ipe_kwh_m2);
  const bits = [];
  if (mwh != null) bits.push(`${formatFR(mwh, 0)}${NBSP}MWh/an`);
  if (Number.isFinite(ipe) && ipe > 0) bits.push(`IPE ${formatFR(ipe, 0)}${NBSP}kWh/m²`);
  if (top.data_source) bits.push(`source : ${top.data_source}`);
  return bits.length > 0 ? bits.join(' · ') + '.' : 'Usage principal identifié.';
}

export function interpretUsageTotal({ dashboard } = {}) {
  const totalKwh = Number(dashboard?.summary?.total_kwh) || 0;
  if (totalKwh <= 0) return 'Consommation totale indisponible — import compteurs requis.';
  const totalEur = Number(dashboard?.summary?.total_eur) || 0;
  if (totalEur > 0) {
    return `Coût annuel ${formatFREur(Math.round(totalEur), 0)} sur 12${NBSP}mois glissants.`;
  }
  return '12 mois glissants · toutes énergies confondues.';
}

export function interpretReadinessScore({ dashboard } = {}) {
  const score = Number(dashboard?.readiness?.score);
  if (!Number.isFinite(score)) {
    return 'Score qualité indisponible — segmentation en cours.';
  }
  if (score >= 80) return 'Segmentation complète · leviers d\'efficacité activables immédiatement.';
  if (score >= 50) return 'Segmentation partielle · compléter les compteurs manquants.';
  return 'Données insuffisantes · prioriser import compteurs sous-comptage.';
}

// ─────────────────────────────────────────────────────────────────────────────
// Adapter top_ues → SolBarChart catégoriel
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Convertit top_ues[] → data SolBarChart catégoriel (xAxisType='category').
 * Shape retournée : [{ name, current (MWh), previous (MWh baseline) }]
 */
export function adaptUsagesToBar(dashboard, { limit = 5 } = {}) {
  const topUes = Array.isArray(dashboard?.top_ues) ? dashboard.top_ues : [];
  const baselines = Array.isArray(dashboard?.baselines) ? dashboard.baselines : [];
  const baselineByLabel = new Map();
  for (const b of baselines) {
    if (b?.label) baselineByLabel.set(b.label, Number(b.kwh_baseline) || 0);
  }
  return topUes
    .filter((u) => Number(u.kwh) > 0)
    .slice(0, limit)
    .map((u) => {
      const kwh = Number(u.kwh) || 0;
      const baselineKwh = baselineByLabel.get(u.label) || 0;
      return {
        name: shortLabel(u.label),
        current: Math.round(kwh / 1000),
        previous: baselineKwh > 0 ? Math.round(baselineKwh / 1000) : 0,
      };
    });
}

function shortLabel(label) {
  if (!label) return 'Usage';
  return label.length > 20 ? label.slice(0, 18) + '…' : label;
}

// ─────────────────────────────────────────────────────────────────────────────
// Week-cards (variety guard D1 : 1 attention + 1 afaire + 1 succes)
// ─────────────────────────────────────────────────────────────────────────────

export function buildUsagesWeekCards({ dashboard, onOpenDetail } = {}) {
  const cards = [];
  const baselines = Array.isArray(dashboard?.baselines) ? dashboard.baselines : [];
  const topUes = Array.isArray(dashboard?.top_ues) ? dashboard.top_ues : [];

  // Card 1 'attention' : baseline avec écart positif max (consommation en hausse)
  const drift = baselines
    .filter((b) => Number(b.ecart_pct) > 10)
    .sort((a, b) => Number(b.ecart_pct) - Number(a.ecart_pct))[0];
  if (drift) {
    cards.push({
      id: `drift-${drift.label}`,
      tagKind: 'attention',
      tagLabel: 'À regarder',
      title: `${drift.label} en dérive`,
      body: `+${Math.round(Number(drift.ecart_pct))}${NBSP}% vs baseline · écart ${formatFR(
        Math.round((Number(drift.ecart_kwh) || 0) / 1000),
        0
      )}${NBSP}MWh sur 12${NBSP}mois.`,
      footerLeft: `tendance ${drift.trend || 'haussière'}`,
      footerRight: '⌘K',
      onClick: () => onOpenDetail?.(drift),
    });
  } else {
    cards.push(businessErrorFallback('usage.no_usages', cards.length));
  }

  // Card 2 'afaire' : top usage non significatif = donnée à compléter
  const nonSignificant = topUes.find((u) => !u.is_significant && Number(u.kwh) > 0);
  if (nonSignificant) {
    cards.push({
      id: `data-${nonSignificant.label}`,
      tagKind: 'afaire',
      tagLabel: 'À faire',
      title: `${nonSignificant.label} à qualifier`,
      body: "Données de comptage insuffisantes pour valider cet usage. Ajoutez un sous-compteur dédié pour activer le suivi efficacité.",
      footerLeft: `source actuelle : ${nonSignificant.data_source || 'estimée'}`,
      footerRight: 'Sol peut guider',
      onClick: () => onOpenDetail?.(nonSignificant),
    });
  } else {
    const fb = businessErrorFallback('usage.segmentation_pending', cards.length);
    cards.push({ ...fb, tagKind: 'afaire', tagLabel: 'À faire' });
  }

  // Card 3 'succes' : baseline avec écart négatif (consommation en baisse) OU monitoring actif
  const improved = baselines
    .filter((b) => Number(b.ecart_pct) < -5)
    .sort((a, b) => Number(a.ecart_pct) - Number(b.ecart_pct))[0];
  if (improved) {
    cards.push({
      id: `improved-${improved.label}`,
      tagKind: 'succes',
      tagLabel: 'Bonne nouvelle',
      title: `${improved.label} en baisse`,
      body: `${Math.round(Number(improved.ecart_pct))}${NBSP}% vs baseline · économie ${formatFR(
        Math.round(Math.abs(Number(improved.ecart_kwh) || 0) / 1000),
        0
      )}${NBSP}MWh sur 12${NBSP}mois.`,
      footerLeft: 'efficacité mesurée',
      footerRight: '✓ Clean',
    });
  } else {
    cards.push({
      id: 'monitoring-active',
      tagKind: 'succes',
      tagLabel: 'Bonne nouvelle',
      title: 'Suivi usages actif',
      body: "Sol analyse vos courbes de charge chaque nuit et vous alertera dès qu'une dérive usage dépasse 10 %.",
      footerLeft: 'baseline + ML',
      footerRight: '—',
    });
  }

  return cards.slice(0, 3);
}

// ─────────────────────────────────────────────────────────────────────────────
// Normalize
// ─────────────────────────────────────────────────────────────────────────────

export function normalizeUsagesSummary(raw) {
  if (!raw) return null;
  return {
    summary: raw.summary || {},
    top_ues: Array.isArray(raw.top_ues) ? raw.top_ues : [],
    baselines: Array.isArray(raw.baselines) ? raw.baselines : [],
    readiness: raw.readiness || {},
    sites_count: Number(raw.sites_count) || 0,
  };
}
