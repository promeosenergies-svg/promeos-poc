/**
 * PROMEOS — ContratsSol presenters (Lot 2 Phase 3, Pattern B pur)
 *
 * Helpers purs pour ContratsSol (/contrats).
 *
 * API consommée (parent Contrats.jsx) :
 *   listCadres() → [{
 *     id, supplier_name, contract_ref, status ('active'|'expiring'|
 *     'expired'|'draft'), energy_type ('elec'|'gaz'), site_name,
 *     pricing_model ('fixe'|'indexe_*'|'hybride'|...), end_date,
 *     volume_mwh?, eur_mwh?,
 *     annexes: [{ id, annexe_ref, site_name, status, pricing_model,
 *                 end_date, volume_mwh?, eur_mwh? }]
 *   }]
 *   getCadreKpis() → {...} shape variable
 *
 * Les 3 KPIs Sol sont calculés localement depuis `cadres` (robustesse
 * face à la variabilité getCadreKpis shape).
 */
import { NBSP, formatFR, formatFREur } from '../cockpit/sol_presenters';
import { businessErrorFallback } from '../../i18n/business_errors';

export { NBSP, formatFR, formatFREur };

// ─────────────────────────────────────────────────────────────────────────────
// Labels + tones
// ─────────────────────────────────────────────────────────────────────────────

export const STATUS_LABELS = {
  active: 'Actif',
  expiring: 'Expire bientôt',
  expired: 'Expiré',
  draft: 'Brouillon',
};

const STATUS_TONE = {
  active: 'calme',
  expiring: 'attention',
  expired: 'refuse',
  draft: 'afaire',
};

export const PRICING_LABELS = {
  fixe: 'Fixe',
  fixe_hors_acheminement: 'Fixe hors acheminement',
  indexe_trve: 'Indexé TRVE',
  indexe_peg: 'Indexé PEG',
  indexe_spot: 'Indexé spot',
  indexe: 'Indexé',
  hybride: 'Hybride',
};

export const ENERGY_LABELS = {
  elec: 'Élec',
  electricity: 'Élec',
  gaz: 'Gaz',
  gas: 'Gaz',
};

export function toneFromStatus(status) {
  return STATUS_TONE[status] || 'afaire';
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

export function daysUntil(dateStr) {
  if (!dateStr) return null;
  const d = new Date(dateStr);
  if (isNaN(d.getTime())) return null;
  return Math.ceil((d.getTime() - Date.now()) / (1000 * 60 * 60 * 24));
}

// ─────────────────────────────────────────────────────────────────────────────
// Rows builder (cadres + annexes indentées)
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Convertit cadres (+ annexes) → rows pour SolExpertGridFull.
 * Préserve la hiérarchie cadre/annexe via indentation visuelle dans
 * le site_name (prefix "↳ " pour annexes).
 */
export function buildContractRows(cadres = []) {
  const rows = [];
  for (const c of cadres || []) {
    rows.push({
      id: `cadre-${c.id}`,
      cells: {
        site: c.site_name || c.supplier_name || 'Cadre',
        supplier: c.supplier_name || '—',
        energy: ENERGY_LABELS[c.energy_type] || c.energy_type || '—',
        pricing: PRICING_LABELS[c.pricing_model] || c.pricing_model || '—',
        end_date: c.end_date,
        status: c.status || 'draft',
        volume_mwh: Number(c.volume_mwh) || 0,
        price_eur_mwh: Number(c.eur_mwh) || null,
        _type: 'cadre',
        _raw: c,
      },
      tone: c.status === 'expired' ? 'refuse' : c.status === 'expiring' ? 'attention' : null,
    });
    for (const a of c.annexes || []) {
      rows.push({
        // Préfixe cadreId pour éviter collisions annexe-id entre cadres
        id: `annexe-${c.id}-${a.id}`,
        cells: {
          site: `${NBSP}${NBSP}↳ ${a.site_name || a.annexe_ref || 'Annexe'}`,
          supplier: c.supplier_name || '—',
          energy: ENERGY_LABELS[a.energy_type || c.energy_type] || '—',
          pricing: PRICING_LABELS[a.pricing_model || c.pricing_model] || '—',
          end_date: a.end_date || c.end_date,
          status: a.status || c.status || 'draft',
          volume_mwh: Number(a.volume_mwh) || 0,
          price_eur_mwh: Number(a.eur_mwh) || null,
          _type: 'annexe',
          _cadreId: c.id,
          _raw: a,
        },
        tone: null,
      });
    }
  }
  return rows;
}

// ─────────────────────────────────────────────────────────────────────────────
// KPIs computations
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Calcule les 3 KPIs portefeuille depuis les cadres (+ annexes).
 * Retourne { activeCount, totalVolumeMwh, weightedPriceEurMwh, byType }.
 */
export function computePortfolioKpis(cadres = []) {
  let activeCount = 0;
  let totalVolume = 0;
  let weightedSum = 0;
  const byType = {};
  const allContracts = [];

  for (const c of cadres || []) {
    allContracts.push(c);
    for (const a of c.annexes || []) allContracts.push({ ...a, _parentPricing: c.pricing_model });
  }

  for (const k of allContracts) {
    if (k.status === 'active') activeCount += 1;
    const vol = Number(k.volume_mwh) || 0;
    const price = Number(k.eur_mwh) || 0;
    totalVolume += vol;
    if (price > 0 && vol > 0) weightedSum += price * vol;
    const type = k.pricing_model || k._parentPricing || 'inconnu';
    byType[type] = (byType[type] || 0) + 1;
  }

  return {
    activeCount,
    totalVolumeMwh: Math.round(totalVolume),
    // Retourne null si aucun contrat n'a de prix fixe renseigné
    // (Σ prix × volume = 0), pour éviter un "0 €/MWh" trompeur
    // quand le portefeuille est 100 % indexé.
    weightedPriceEurMwh:
      totalVolume > 0 && weightedSum > 0 ? Math.round((weightedSum / totalVolume) * 10) / 10 : null,
    byType,
    totalContracts: allContracts.length,
  };
}

// ─────────────────────────────────────────────────────────────────────────────
// Kicker + narratives
// ─────────────────────────────────────────────────────────────────────────────

export function buildContractsKicker({ scopeLabel, activeCount } = {}) {
  const scope = scopeLabel ? scopeLabel.toUpperCase() : 'PATRIMOINE';
  const n = Number(activeCount) || 0;
  return `CONTRATS · ${scope} · ${n}${NBSP}ACTIF${n > 1 ? 'S' : ''}`;
}

export function buildContractsNarrative({ cadres = [], kpis } = {}) {
  const k = kpis || computePortfolioKpis(cadres);
  const totalContracts = k.totalContracts;

  if (totalContracts === 0) {
    return "Aucun contrat enregistré pour l'instant. Importez vos contrats en cours depuis CSV ou PDF pour activer le radar de renouvellement.";
  }

  // Top expirant proche
  const all = [];
  for (const c of cadres || []) {
    all.push(c);
    for (const a of c.annexes || []) all.push({ ...a, supplier_name: c.supplier_name });
  }
  const topExpiring = all
    .filter((x) => x.status === 'expiring' || x.status === 'active')
    .map((x) => ({ ...x, _days: daysUntil(x.end_date) }))
    .filter((x) => x._days != null && x._days > 0 && x._days <= 180)
    .sort((a, b) => a._days - b._days)[0];

  const parts = [
    `${k.activeCount}${NBSP}contrat${k.activeCount > 1 ? 's' : ''} actif${k.activeCount > 1 ? 's' : ''} sur ${totalContracts} total`,
  ];
  if (k.totalVolumeMwh > 0) {
    parts.push(`volume ${formatFR(k.totalVolumeMwh, 0)}${NBSP}MWh sur 12${NBSP}mois`);
  }
  if (k.weightedPriceEurMwh != null) {
    parts.push(`prix pondéré ${formatFR(k.weightedPriceEurMwh, 1)}${NBSP}€/MWh`);
  } else if (k.totalVolumeMwh > 0) {
    parts.push('portefeuille 100% indexé · prix fixe à compléter');
  }
  if (topExpiring) {
    const where = topExpiring.site_name || topExpiring.supplier_name || 'un contrat';
    parts.push(`échéance proche : ${where} · ${topExpiring._days}${NBSP}jours`);
  }
  return parts.join(' · ') + '.';
}

export function buildContractsSubNarrative({ cadres = [], kpis } = {}) {
  const k = kpis || computePortfolioKpis(cadres);
  // Répartition fournisseurs (top 3)
  const bySupplier = {};
  for (const c of cadres || []) {
    const s = c.supplier_name || 'Inconnu';
    bySupplier[s] = (bySupplier[s] || 0) + 1;
  }
  const top3 = Object.entries(bySupplier)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 3);
  const total = (cadres || []).length;
  const parts = [];
  if (top3.length > 0 && total > 0) {
    const mix = top3.map(([s, n]) => `${s} ${Math.round((n / total) * 100)}${NBSP}%`).join(' · ');
    parts.push(`Mix fournisseurs : ${mix}`);
  }
  parts.push('Sources : référentiel contrats PROMEOS + import CSV/PDF');
  return parts.join('. ') + '.';
}

// ─────────────────────────────────────────────────────────────────────────────
// KPI interpretations
// ─────────────────────────────────────────────────────────────────────────────

export function interpretActiveContracts({ kpis } = {}) {
  if (!kpis || kpis.totalContracts === 0) {
    return 'Importez vos contrats pour activer les KPIs portefeuille.';
  }
  const bits = [];
  for (const [type, n] of Object.entries(kpis.byType || {})) {
    if (n > 0 && type !== 'inconnu') {
      const label = PRICING_LABELS[type] || type;
      bits.push(`${n}${NBSP}${label.toLowerCase()}`);
    }
  }
  if (bits.length === 0) return `${kpis.totalContracts}${NBSP}contrats enregistrés.`;
  return `Répartition : ${bits.slice(0, 3).join(' · ')}.`;
}

export function interpretTotalVolume({ kpis, nbSites } = {}) {
  if (!kpis || kpis.totalVolumeMwh <= 0) {
    return 'Volume indisponible — vérifiez la complétude des contrats.';
  }
  if (nbSites && nbSites > 0) {
    const avg = Math.round(kpis.totalVolumeMwh / nbSites);
    return `Réparti sur ${nbSites}${NBSP}site${nbSites > 1 ? 's' : ''} · moyenne ${formatFR(avg, 0)}${NBSP}MWh/site.`;
  }
  return `Volume cumulé 12 mois sur le portefeuille.`;
}

export function interpretWeightedPrice({ kpis } = {}) {
  if (!kpis || kpis.weightedPriceEurMwh == null) {
    return "Prix pondéré indisponible — certains contrats n'ont pas de prix renseigné.";
  }
  const p = kpis.weightedPriceEurMwh;
  // Heuristique marché : < 60 = bien · 60-100 = marché · > 100 = au-dessus
  if (p < 60) return `Prix compétitif vs marché spot 2024-2025 (~80${NBSP}€/MWh).`;
  if (p > 100) return `Au-dessus du marché spot moyen · levier renégociation activable.`;
  return `Cohérent avec le marché spot moyen 2024-2025.`;
}

// ─────────────────────────────────────────────────────────────────────────────
// Empty state context-aware
// ─────────────────────────────────────────────────────────────────────────────

export function buildEmptyState({ hasFilters, hasAnyContract } = {}) {
  if (hasFilters) {
    const fb = businessErrorFallback('contract.filter_no_results');
    return { title: fb.title, message: fb.body };
  }
  if (!hasAnyContract) {
    const fb = businessErrorFallback('contract.no_contracts');
    return {
      title: fb.title,
      message: fb.body,
      ctaLabel: fb.ctaLabel,
      ctaHref: fb.ctaHref,
    };
  }
  return null;
}

// ─────────────────────────────────────────────────────────────────────────────
// Filter config pour SolExpertToolbar
// ─────────────────────────────────────────────────────────────────────────────

export function buildFilterConfig({ cadres = [] } = {}) {
  const suppliers = Array.from(new Set((cadres || []).map((c) => c.supplier_name).filter(Boolean)));
  return [
    {
      id: 'supplier',
      label: 'Fournisseur',
      options: suppliers.slice(0, 10).map((s) => ({ value: s, label: s })),
    },
    {
      id: 'chip',
      label: 'Type',
      options: [
        { value: 'cadre', label: 'Cadres seuls' },
        { value: 'annexes', label: 'Annexes seules' },
      ],
    },
    {
      id: 'status',
      label: 'Statut',
      options: [
        { value: 'active', label: 'Actifs' },
        { value: 'expiring', label: 'Expirent bientôt' },
        { value: 'expired', label: 'Expirés' },
        { value: 'draft', label: 'Brouillons' },
      ],
    },
  ];
}

// ─────────────────────────────────────────────────────────────────────────────
// Filter + sort + paginate
// ─────────────────────────────────────────────────────────────────────────────

export function filterRows(rows, { search, supplier, chip, status } = {}) {
  let r = rows;
  if (chip === 'cadre') r = r.filter((x) => x.cells._type === 'cadre');
  if (chip === 'annexes') r = r.filter((x) => x.cells._type === 'annexe');
  if (supplier) r = r.filter((x) => x.cells.supplier === supplier);
  if (status) r = r.filter((x) => x.cells.status === status);
  if (search) {
    const q = search.toLowerCase();
    r = r.filter((x) => {
      const cells = x.cells;
      return (
        String(cells.site || '')
          .toLowerCase()
          .includes(q) ||
        String(cells.supplier || '')
          .toLowerCase()
          .includes(q)
      );
    });
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
    return String(va || '').localeCompare(String(vb || ''));
  });
  return sortBy.direction === 'desc' ? sorted.reverse() : sorted;
}

export function paginateRows(rows, page, pageSize) {
  const start = Math.max(0, (page - 1) * pageSize);
  return rows.slice(start, start + pageSize);
}
