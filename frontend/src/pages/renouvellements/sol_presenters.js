/**
 * PROMEOS — RenouvellementsSol presenters (Lot 2 Phase 4, Pattern B pur)
 *
 * Helpers purs pour /renouvellements (radar échéances DAF).
 *
 * API consommée (parent ContractRadarPage.jsx) :
 *   getContractRadar({ days, site_id? }) → {
 *     contracts: [{
 *       contract_id, site_nom, portfolio_nom, supplier_name,
 *       end_date, days_to_end,
 *       urgency: 'red'|'orange'|'yellow'|'green'|'gray',
 *       contract_status: 'expired'|'expiring'|'active',
 *       indexation_label, readiness_score (0-100), payer_entity,
 *       energy_type
 *     }],
 *     stats: { expired, expiring, active },
 *     total
 *   }
 *
 * IMPORTANT — divergences spec user → API réelle (documentées) :
 *   - `bestImpactCumulativeEur` spec → **ABSENT** côté getContractRadar
 *     (nécessite getContractPurchaseScenarios par contrat, coûteux).
 *     KPI 2 remappé → score readiness moyen (indicateur de préparation
 *     à la renégociation, honnête et dispo gratuitement).
 *   - `totalScenariosCount` spec → **ABSENT** même raison. KPI 3
 *     remappé → nombre de contrats expirés (= dette urgence immédiate).
 */
import { NBSP, formatFR, formatFREur } from '../cockpit/sol_presenters';
import { businessErrorFallback } from '../../i18n/business_errors';

export { NBSP, formatFR, formatFREur };

// ─────────────────────────────────────────────────────────────────────────────
// Labels + tones
// ─────────────────────────────────────────────────────────────────────────────

export const URGENCY_LABELS = {
  red: 'Critique',
  orange: 'Urgent',
  yellow: 'Attention',
  green: 'OK',
  gray: 'Serein',
};

const URGENCY_TONE = {
  red: 'refuse',
  orange: 'attention',
  yellow: 'afaire',
  green: 'calme',
  gray: 'calme',
};

export const STATUS_LABELS = {
  expired: 'Expiré',
  expiring: 'Bientôt',
  active: 'Actif',
};

const STATUS_TONE = {
  expired: 'refuse',
  expiring: 'attention',
  active: 'calme',
};

export function toneFromUrgency(u) {
  return URGENCY_TONE[u] || 'afaire';
}

export function toneFromStatus(s) {
  return STATUS_TONE[s] || 'afaire';
}

// ─────────────────────────────────────────────────────────────────────────────
// Date helpers
// ─────────────────────────────────────────────────────────────────────────────

export function formatDateFR(dateStr) {
  if (!dateStr) return '—';
  const d = new Date(dateStr);
  if (isNaN(d.getTime())) return dateStr;
  return d.toLocaleDateString('fr-FR', { day: '2-digit', month: 'short', year: 'numeric' });
}

// ─────────────────────────────────────────────────────────────────────────────
// KPIs computations (honnêteté : pas de scenario data, on utilise readiness)
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Calcule 3 KPIs portefeuille depuis contracts[] de getContractRadar.
 *   - imminentCount90d  : contrats avec 0 < days_to_end <= 90
 *   - readinessAvg       : moyenne readiness_score (ignore null)
 *   - expiredCount       : contrats déjà expirés (action urgente)
 */
export function computeRenewalsKpis(contracts = []) {
  let imminent = 0;
  let expired = 0;
  let readinessSum = 0;
  let readinessCount = 0;
  let under30d = 0;
  let between30and90d = 0;

  for (const c of contracts || []) {
    const days = Number(c?.days_to_end);
    const r = Number(c?.readiness_score);
    if (Number.isFinite(days)) {
      if (days < 0) {
        expired += 1;
      } else if (days <= 90) {
        imminent += 1;
        if (days <= 30) under30d += 1;
        else between30and90d += 1;
      }
    }
    if (Number.isFinite(r)) {
      readinessSum += r;
      readinessCount += 1;
    }
  }

  return {
    imminentCount90d: imminent,
    expiredCount: expired,
    under30d,
    between30and90d,
    readinessAvg: readinessCount > 0 ? Math.round(readinessSum / readinessCount) : null,
    totalContracts: contracts.length,
  };
}

// ─────────────────────────────────────────────────────────────────────────────
// Kicker + narratives
// ─────────────────────────────────────────────────────────────────────────────

export function buildRenewalsKicker({ scopeLabel, imminentCount } = {}) {
  const scope = scopeLabel ? scopeLabel.toUpperCase() : 'PATRIMOINE';
  const n = Number(imminentCount) || 0;
  return `RENOUVELLEMENTS · ${scope} · ${n}${NBSP}IMMINENT${n > 1 ? 'S' : ''}`;
}

export function buildRenewalsNarrative({ contracts = [], kpis } = {}) {
  const k = kpis || computeRenewalsKpis(contracts);
  if (k.totalContracts === 0) {
    return "Aucun contrat dans la fenêtre de renégociation. Élargissez l'horizon pour voir les échéances à > 90 jours.";
  }
  const parts = [];
  if (k.imminentCount90d > 0) {
    parts.push(
      `${k.imminentCount90d}${NBSP}renouvellement${k.imminentCount90d > 1 ? 's' : ''} imminent${k.imminentCount90d > 1 ? 's' : ''} sous 90${NBSP}jours`
    );
  }
  if (k.expiredCount > 0) {
    parts.push(
      `${k.expiredCount}${NBSP}déjà expiré${k.expiredCount > 1 ? 's' : ''} · action immédiate requise`
    );
  }
  // Top priorité : contract avec urgency=red + days_to_end minimum
  const top = [...contracts]
    .filter((c) => Number.isFinite(c?.days_to_end) && c.days_to_end >= 0)
    .sort((a, b) => (a.days_to_end ?? Infinity) - (b.days_to_end ?? Infinity))[0];
  if (top) {
    const where = top.site_nom || top.supplier_name || 'un site';
    parts.push(
      `action prioritaire : ${where} · ${top.supplier_name || 'fournisseur'} · ${top.days_to_end}${NBSP}jours`
    );
  }
  return parts.join(' · ') + '.';
}

export function buildRenewalsSubNarrative({ kpis } = {}) {
  const bits = [];
  if (kpis?.under30d > 0) bits.push(`${kpis.under30d}${NBSP}<${NBSP}30${NBSP}j`);
  if (kpis?.between30and90d > 0) bits.push(`${kpis.between30and90d}${NBSP}entre 30-90${NBSP}j`);
  if (kpis?.expiredCount > 0) bits.push(`${kpis.expiredCount}${NBSP}expirés`);
  const left = bits.length > 0 ? `Distribution urgence : ${bits.join(' · ')}. ` : '';
  return `${left}Sources : radar contrats V99 + segmentation métier V100.`;
}

// ─────────────────────────────────────────────────────────────────────────────
// KPI interpretations
// ─────────────────────────────────────────────────────────────────────────────

export function interpretImminentCount({ kpis } = {}) {
  if (!kpis || kpis.imminentCount90d === 0) {
    return 'Aucun renouvellement sous 90 jours — portefeuille stable.';
  }
  const bits = [];
  if (kpis.under30d > 0) bits.push(`${kpis.under30d}${NBSP}<${NBSP}30${NBSP}j`);
  if (kpis.between30and90d > 0) bits.push(`${kpis.between30and90d}${NBSP}entre 30-90${NBSP}j`);
  return bits.length > 0
    ? `Répartition : ${bits.join(' · ')}.`
    : 'Fenêtre active de renégociation.';
}

export function interpretReadinessAvg({ kpis } = {}) {
  if (!kpis || kpis.readinessAvg == null) {
    return 'Score de préparation non disponible — complétez les données fournisseur.';
  }
  const r = kpis.readinessAvg;
  if (r >= 80) return `Données complètes · négociation activable immédiatement.`;
  if (r >= 50) return `Données partielles · compléter pour scénarios précis.`;
  return `Données insuffisantes · rassembler factures et CDC avant RFP.`;
}

export function interpretExpiredCount({ kpis } = {}) {
  if (!kpis || kpis.expiredCount === 0) {
    return 'Aucun contrat expiré — portefeuille sous contrôle.';
  }
  return `${kpis.expiredCount}${NBSP}contrat${kpis.expiredCount > 1 ? 's' : ''} à régulariser en priorité absolue.`;
}

// ─────────────────────────────────────────────────────────────────────────────
// Adapt contracts → rows SolExpertGridFull
// ─────────────────────────────────────────────────────────────────────────────

export function buildRenewalRows(contracts = []) {
  return (contracts || []).map((c) => {
    const tone =
      c.contract_status === 'expired'
        ? 'refuse'
        : c.urgency === 'red'
          ? 'refuse'
          : c.urgency === 'orange'
            ? 'attention'
            : null;
    return {
      id: `contract-${c.contract_id}`,
      cells: {
        site: c.site_nom || c.portfolio_nom || `#${c.contract_id}`,
        supplier: c.supplier_name || '—',
        end_date: c.end_date,
        days_to_end: Number.isFinite(Number(c.days_to_end)) ? Number(c.days_to_end) : null,
        urgency: c.urgency || 'gray',
        indexation: c.indexation_label || '—',
        readiness: Number.isFinite(Number(c.readiness_score)) ? Number(c.readiness_score) : null,
        status: c.contract_status || 'active',
        _raw: c,
      },
      tone,
    };
  });
}

// ─────────────────────────────────────────────────────────────────────────────
// Filter + sort + paginate
// ─────────────────────────────────────────────────────────────────────────────

export function filterRows(rows, { search, supplier, status, urgency } = {}) {
  let r = rows;
  if (supplier) r = r.filter((x) => x.cells.supplier === supplier);
  if (status) r = r.filter((x) => x.cells.status === status);
  if (urgency) {
    if (urgency === 'under30')
      r = r.filter(
        (x) => x.cells.days_to_end != null && x.cells.days_to_end >= 0 && x.cells.days_to_end <= 30
      );
    else if (urgency === 'between30_90')
      r = r.filter(
        (x) => x.cells.days_to_end != null && x.cells.days_to_end > 30 && x.cells.days_to_end <= 90
      );
    else if (urgency === 'over90')
      r = r.filter((x) => x.cells.days_to_end != null && x.cells.days_to_end > 90);
    else if (urgency === 'expired')
      r = r.filter(
        (x) =>
          x.cells.status === 'expired' || (x.cells.days_to_end != null && x.cells.days_to_end < 0)
      );
  }
  if (search) {
    const q = search.toLowerCase();
    r = r.filter(
      (x) =>
        String(x.cells.site || '')
          .toLowerCase()
          .includes(q) ||
        String(x.cells.supplier || '')
          .toLowerCase()
          .includes(q)
    );
  }
  return r;
}

export function sortRows(rows, sortBy) {
  if (!sortBy?.column) return rows;
  const sorted = [...rows].sort((a, b) => {
    const va = a.cells[sortBy.column];
    const vb = b.cells[sortBy.column];
    if (typeof va === 'number' && typeof vb === 'number') return va - vb;
    if (sortBy.column === 'end_date') {
      const da = va ? new Date(va).getTime() : 0;
      const db = vb ? new Date(vb).getTime() : 0;
      return da - db;
    }
    if (va == null) return 1;
    if (vb == null) return -1;
    return String(va).localeCompare(String(vb));
  });
  return sortBy.direction === 'desc' ? sorted.reverse() : sorted;
}

export function paginateRows(rows, page, pageSize) {
  const start = Math.max(0, (page - 1) * pageSize);
  return rows.slice(start, start + pageSize);
}

// ─────────────────────────────────────────────────────────────────────────────
// Empty state
// ─────────────────────────────────────────────────────────────────────────────

export function buildEmptyState({ hasFilters, hasAnyRenewal } = {}) {
  if (hasFilters) {
    const fb = businessErrorFallback('renewal.filter_no_results');
    return { title: fb.title, message: fb.body };
  }
  if (!hasAnyRenewal) {
    const fb = businessErrorFallback('renewal.no_renewals');
    return { title: fb.title, message: fb.body };
  }
  return null;
}

// ─────────────────────────────────────────────────────────────────────────────
// Filter config
// ─────────────────────────────────────────────────────────────────────────────

export function buildFilterConfig({ contracts = [] } = {}) {
  const suppliers = Array.from(
    new Set((contracts || []).map((c) => c.supplier_name).filter(Boolean))
  );
  return [
    {
      id: 'supplier',
      label: 'Fournisseur',
      options: suppliers.slice(0, 10).map((s) => ({ value: s, label: s })),
    },
    {
      id: 'urgency',
      label: 'Urgence',
      options: [
        { value: 'expired', label: 'Expirés' },
        { value: 'under30', label: '< 30 j' },
        { value: 'between30_90', label: '30-90 j' },
        { value: 'over90', label: '> 90 j' },
      ],
    },
    {
      id: 'status',
      label: 'Statut',
      options: [
        { value: 'expired', label: 'Expiré' },
        { value: 'expiring', label: 'Bientôt' },
        { value: 'active', label: 'Actif' },
      ],
    },
  ];
}
