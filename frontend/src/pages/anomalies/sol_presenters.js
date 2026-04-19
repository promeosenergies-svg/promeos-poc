/**
 * PROMEOS — AnomaliesSol presenters (Lot 2 Phase 2, Pattern B pur)
 *
 * Helpers purs pour AnomaliesSol (/anomalies onglet Anomalies).
 *
 * Shape anomaly consommée (parent AnomaliesPage.jsx) :
 *   {
 *     id, code, title_fr, detail_fr, fix_hint_fr,
 *     site_id, site_nom,
 *     severity: 'CRITICAL'|'HIGH'|'MEDIUM'|'LOW',
 *     business_impact: { estimated_risk_eur },
 *     regulatory_impact: { framework: 'DECRET_TERTIAIRE'|'FACTURATION'|'BACS' },
 *     priority_score,
 *     _isBilling?: boolean
 *   }
 */
import { NBSP, formatFR, formatFREur } from '../cockpit/sol_presenters';
import { businessErrorFallback } from '../../i18n/business_errors';

export { NBSP, formatFR, formatFREur };

// ─────────────────────────────────────────────────────────────────────────────
// Labels + tones
// ─────────────────────────────────────────────────────────────────────────────

export const SEVERITY_LABELS = {
  CRITICAL: 'Critique',
  HIGH: 'Élevé',
  MEDIUM: 'Moyen',
  LOW: 'Faible',
};

const SEVERITY_TONE = {
  CRITICAL: 'refuse',
  HIGH: 'attention',
  MEDIUM: 'afaire',
  LOW: 'calme',
};

export const FRAMEWORK_LABELS = {
  DECRET_TERTIAIRE: 'Décret Tertiaire',
  FACTURATION: 'Facturation',
  BACS: 'BACS',
};

export function toneFromSeverity(sev) {
  return SEVERITY_TONE[sev] || 'afaire';
}

// ─────────────────────────────────────────────────────────────────────────────
// Kicker + narratives
// ─────────────────────────────────────────────────────────────────────────────

export function buildAnomaliesKicker({ scopeLabel, activeCount } = {}) {
  const scope = scopeLabel ? scopeLabel.toUpperCase() : 'PATRIMOINE';
  const n = Number(activeCount) || 0;
  return `ANOMALIES · ${scope} · ${n}${NBSP}DÉTECTÉE${n > 1 ? 'S' : ''}`;
}

export function buildAnomaliesNarrative({ anomalies = [], summary } = {}) {
  const total = Number(summary?.total) || anomalies.length;
  if (total === 0) {
    return 'Aucune anomalie active sur votre patrimoine. Sol continue à surveiller en continu.';
  }

  const critiques = Number(summary?.critiques) || 0;
  const risque = Number(summary?.risque) || 0;

  // Top driver par impact €
  const top = [...anomalies]
    .filter((a) => Number(a?.business_impact?.estimated_risk_eur) > 0)
    .sort(
      (a, b) =>
        (Number(b.business_impact?.estimated_risk_eur) || 0) -
        (Number(a.business_impact?.estimated_risk_eur) || 0)
    )[0];

  const parts = [
    `${total}${NBSP}anomalie${total > 1 ? 's' : ''} active${total > 1 ? 's' : ''} sur votre patrimoine`,
  ];
  if (critiques > 0) {
    parts.push(`${critiques}${NBSP}critique${critiques > 1 ? 's' : ''}`);
  }
  if (risque > 0) {
    parts.push(`récupération potentielle ${formatFREur(risque, 0)}`);
  }
  if (top) {
    const where = top.site_nom || `site #${top.site_id}`;
    const title = top.title_fr || 'anomalie prioritaire';
    parts.push(`action prioritaire : ${where} · ${title}`);
  }
  return parts.join(' · ') + '.';
}

export function buildAnomaliesSubNarrative({ anomalies = [] } = {}) {
  const bySev = { CRITICAL: 0, HIGH: 0, MEDIUM: 0, LOW: 0 };
  for (const a of anomalies) {
    const s = a?.severity;
    if (bySev[s] != null) bySev[s] += 1;
  }
  const bits = [];
  if (bySev.CRITICAL > 0) bits.push(`${bySev.CRITICAL}${NBSP}critique${bySev.CRITICAL > 1 ? 's' : ''}`);
  if (bySev.HIGH > 0) bits.push(`${bySev.HIGH}${NBSP}élevée${bySev.HIGH > 1 ? 's' : ''}`);
  if (bySev.MEDIUM > 0) bits.push(`${bySev.MEDIUM}${NBSP}moyenne${bySev.MEDIUM > 1 ? 's' : ''}`);
  if (bySev.LOW > 0) bits.push(`${bySev.LOW}${NBSP}faible${bySev.LOW > 1 ? 's' : ''}`);
  if (bits.length === 0) {
    return 'Sources : moteur patrimoine + shadow billing + règles BACS.';
  }
  return `Répartition sévérité : ${bits.join(' · ')}. Sources : moteur patrimoine + shadow billing + règles BACS.`;
}

// ─────────────────────────────────────────────────────────────────────────────
// KPI interpretations
// ─────────────────────────────────────────────────────────────────────────────

export function interpretActiveCount({ anomalies = [] } = {}) {
  const sub = buildAnomaliesSubNarrative({ anomalies });
  return sub.split('Sources')[0].replace(/\.\s*$/, '').trim() || 'Aucune anomalie active.';
}

export function interpretTotalImpact({ summary } = {}) {
  const risque = Number(summary?.risque) || 0;
  if (risque <= 0) return 'Aucun impact financier identifié à ce jour.';
  return 'Estimation basée sur prix moyen pondéré + baseline DJU ADEME.';
}

export function interpretFilteredContext({ filtersActive, totalAll, totalFiltered }) {
  if (!filtersActive) return null;
  return `${totalFiltered} affichée${totalFiltered > 1 ? 's' : ''} sur ${totalAll} au total — filtres actifs.`;
}

// ─────────────────────────────────────────────────────────────────────────────
// Grid columns adapter
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Convertit une liste d'anomalies en rows pour SolExpertGridFull.
 * Format rows : { id, cells: { site, detected_at, framework, severity,
 *                               title, impact_eur, status }, tone }
 */
export function adaptAnomaliesToRows(anomalies = [], statuses = {}) {
  return (anomalies || []).map((a) => {
    const key = `${a._isBilling ? 'billing' : 'patrimoine'}:${a.code || a.id}:${a.site_id}`;
    const status = statuses[key]?.status || 'open';
    const sev = a.severity || 'MEDIUM';
    return {
      id: key,
      cells: {
        site: a.site_nom || `Site #${a.site_id ?? '—'}`,
        framework: FRAMEWORK_LABELS[a?.regulatory_impact?.framework] || '—',
        severity: SEVERITY_LABELS[sev] || sev,
        title: a.title_fr || 'Anomalie sans titre',
        impact_eur: Number(a.business_impact?.estimated_risk_eur) || 0,
        status,
        _raw: a,
      },
      tone: sev === 'CRITICAL' ? 'refuse' : null,
    };
  });
}

// ─────────────────────────────────────────────────────────────────────────────
// Sort + paginate (client-side, vu qu'API ne supporte pas pagination)
// ─────────────────────────────────────────────────────────────────────────────

export function sortAnomaliesRows(rows, sortBy) {
  if (!sortBy?.column) return rows;
  const sorted = [...rows].sort((a, b) => {
    const va = a.cells[sortBy.column];
    const vb = b.cells[sortBy.column];
    if (typeof va === 'number' && typeof vb === 'number') return va - vb;
    return String(va || '').localeCompare(String(vb || ''));
  });
  return sortBy.direction === 'desc' ? sorted.reverse() : sorted;
}

export function paginateRows(rows, page, pageSize) {
  const start = Math.max(0, (page - 1) * pageSize);
  return rows.slice(start, start + pageSize);
}

// ─────────────────────────────────────────────────────────────────────────────
// Empty state context-aware
// ─────────────────────────────────────────────────────────────────────────────

export function buildEmptyState({ hasFilters, hasAnyAnomaly } = {}) {
  if (hasFilters) {
    const fb = businessErrorFallback('anomaly.filter_no_results');
    return { title: fb.title, message: fb.body };
  }
  if (!hasAnyAnomaly) {
    const fb = businessErrorFallback('anomaly.no_anomalies');
    return { title: fb.title, message: fb.body };
  }
  return null;
}

// ─────────────────────────────────────────────────────────────────────────────
// Filters builder pour SolExpertToolbar
// ─────────────────────────────────────────────────────────────────────────────

export function buildFilterConfig({ scopedSites = [] } = {}) {
  return [
    {
      id: 'fw',
      label: 'Framework',
      options: [
        { value: 'DECRET_TERTIAIRE', label: 'Décret Tertiaire' },
        { value: 'FACTURATION', label: 'Facturation' },
        { value: 'BACS', label: 'BACS' },
      ],
    },
    {
      id: 'sev',
      label: 'Sévérité',
      options: [
        { value: 'CRITICAL', label: 'Critique' },
        { value: 'HIGH', label: 'Élevé' },
        { value: 'MEDIUM', label: 'Moyen' },
        { value: 'LOW', label: 'Faible' },
      ],
    },
    {
      id: 'site',
      label: 'Site',
      options: scopedSites.slice(0, 20).map((s) => ({
        value: String(s.id),
        label: s.nom,
      })),
    },
  ];
}
