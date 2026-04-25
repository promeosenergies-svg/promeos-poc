/**
 * PROMEOS — CompliancePipelineSol presenters (Lot 6 Phase 5, Pattern B)
 *
 * Helpers purs pour le hero + grid `/compliance/pipeline`. Pure
 * functions, zéro import React, zéro calcul métier. Tous les
 * agrégats, buckets deadline, filtre untrusted, enum gate_status
 * viennent du backend via `GET /api/compliance/portfolio/summary`.
 *
 * API consommée :
 *   getPortfolioComplianceSummary({ site_id? }) → {
 *     org_id, total_sites,
 *     kpis: { data_blocked, data_warning, data_ready },
 *     top_blockers: [...],
 *     deadlines: { d30, d90, d180, beyond },
 *     untrusted_sites: [{ site_id, site_nom, trust_score, anomaly_count, reasons }],
 *     sites: [{ site_id, site_nom, gate_status, completeness_pct,
 *               reg_risk, compliance_score, financial_opportunity_eur,
 *               applicability: { tertiaire_operat, bacs, aper } }]
 *   }
 *
 * Chaque helper accepte null|undefined → empty-state propre (pas de
 * throw). Unit tests Vitest couvrent null + 0 + frameworks manquants
 * + applicability vide. Voir pré-flight :
 * docs/audit/api_compliance_pipeline_phase5.md
 */
import { NBSP, formatFR } from '../cockpit/sol_presenters';
import { businessErrorFallback } from '../../i18n/business_errors';

export { NBSP, formatFR };

// ─────────────────────────────────────────────────────────────────────────────
// 1. hasSummary — empty-state guard
// ─────────────────────────────────────────────────────────────────────────────

export function hasSummary(summary) {
  return Boolean(
    summary &&
    typeof summary === 'object' &&
    'total_sites' in summary &&
    summary.total_sites !== null &&
    summary.total_sites !== undefined
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// 2. formatSitesReady — KPI 1 "Sites prêts" (data_ready / total_sites)
// ─────────────────────────────────────────────────────────────────────────────

export function formatSitesReady(summary) {
  if (!hasSummary(summary)) {
    return { value: null, total: null, label: '—', tone: 'calme' };
  }
  const total = Number(summary.total_sites) || 0;
  const ready = Number(summary.kpis?.data_ready) || 0;
  if (total === 0) {
    return { value: 0, total: 0, label: '0 / 0', tone: 'calme' };
  }
  const ratio = ready / total;
  const tone = ratio === 1 ? 'succes' : ratio >= 0.5 ? 'attention' : 'refuse';
  return { value: ready, total, label: `${ready} / ${total}`, tone };
}

// ─────────────────────────────────────────────────────────────────────────────
// 3. formatDeadlinesD30 — KPI 2 "Échéances < 30 j" (buckets backend)
// ─────────────────────────────────────────────────────────────────────────────

export function formatDeadlinesD30(summary) {
  if (!hasSummary(summary)) {
    return { value: null, d90: null, label: '—', tone: 'calme' };
  }
  const d30 = Array.isArray(summary.deadlines?.d30) ? summary.deadlines.d30.length : 0;
  const d90 = Array.isArray(summary.deadlines?.d90) ? summary.deadlines.d90.length : 0;
  const tone = d30 > 0 ? 'refuse' : d90 > 0 ? 'attention' : 'calme';
  return { value: d30, d90, label: String(d30), tone };
}

// ─────────────────────────────────────────────────────────────────────────────
// 4. formatUntrustedSites — KPI 3 "Sites non fiables" (array pré-filtré)
// ─────────────────────────────────────────────────────────────────────────────

export function formatUntrustedSites(summary) {
  if (!hasSummary(summary)) {
    return { value: null, total: null, label: '—', tone: 'calme' };
  }
  const total = Number(summary.total_sites) || 0;
  const untrusted = Array.isArray(summary.untrusted_sites) ? summary.untrusted_sites.length : 0;
  if (total === 0) {
    return { value: 0, total: 0, label: '0 / 0', tone: 'calme' };
  }
  const ratio = untrusted / total;
  const tone = ratio >= 0.5 ? 'refuse' : untrusted > 0 ? 'attention' : 'succes';
  return { value: untrusted, total, label: `${untrusted} / ${total}`, tone };
}

// ─────────────────────────────────────────────────────────────────────────────
// 5-7. interpret* — tooltips adaptatifs par KPI
// ─────────────────────────────────────────────────────────────────────────────

export function interpretSitesReady(summary) {
  if (!hasSummary(summary)) return 'Portefeuille conformité indisponible.';
  const k = formatSitesReady(summary);
  if (k.total === 0) return 'Aucun site dans le portefeuille.';
  if (k.tone === 'succes') return `Tous les ${k.total} sites sont prêts (gate data OK).`;
  if (k.tone === 'attention')
    return `${k.value} sites prêts sur ${k.total} — compléter les blocages data.`;
  return `Seuls ${k.value} sites prêts sur ${k.total} — priorité débloquer la data.`;
}

export function interpretDeadlinesD30(summary) {
  if (!hasSummary(summary)) return 'Échéances indisponibles.';
  const k = formatDeadlinesD30(summary);
  if (k.tone === 'calme') {
    if (k.d90 > 0) {
      return `Aucune échéance < 30 j, ${k.d90} à venir dans les 90 jours.`;
    }
    return 'Aucune échéance imminente — horizon confortable.';
  }
  if (k.tone === 'attention') return `${k.d90} échéance(s) dans 30–90 j — fenêtre préparation.`;
  return `${k.value} échéance(s) imminente(s) — action sous 30 jours.`;
}

export function interpretUntrustedSites(summary) {
  if (!hasSummary(summary)) return 'Fiabilité sites indisponible.';
  const k = formatUntrustedSites(summary);
  if (k.total === 0) return 'Aucun site dans le portefeuille.';
  if (k.tone === 'succes') return `Tous les ${k.total} sites sont fiables (trust score OK).`;
  if (k.tone === 'attention') return `${k.value} site(s) à fiabiliser — anomalies data à corriger.`;
  return `${k.value} sites non fiables sur ${k.total} — audit data prioritaire.`;
}

// ─────────────────────────────────────────────────────────────────────────────
// 8. buildKickerText — kicker hero compact
// ─────────────────────────────────────────────────────────────────────────────

export function buildKickerText(summary) {
  if (!hasSummary(summary)) return 'CONFORMITÉ · PIPELINE PORTEFEUILLE';
  const total = Number(summary.total_sites) || 0;
  const suffix = total > 1 ? 'S' : '';
  return `CONFORMITÉ · PIPELINE · ${total} SITE${suffix}`;
}

// ─────────────────────────────────────────────────────────────────────────────
// 9. buildNarrative — 1 phrase ≤ 130 car avec ratio prêts + d30 + untrusted
// ─────────────────────────────────────────────────────────────────────────────

export function buildNarrative(summary) {
  if (!hasSummary(summary)) {
    return 'Pipeline conformité portefeuille DT × BACS × APER indisponible.';
  }
  const total = Number(summary.total_sites) || 0;
  if (total === 0) {
    return 'Aucun site dans le portefeuille — ajoutez votre premier site.';
  }
  const ready = Number(summary.kpis?.data_ready) || 0;
  const d30 = Array.isArray(summary.deadlines?.d30) ? summary.deadlines.d30.length : 0;
  const untrusted = Array.isArray(summary.untrusted_sites) ? summary.untrusted_sites.length : 0;
  const parts = [`${ready}/${total} prêts`];
  if (d30 > 0) parts.push(`${d30} échéance${d30 > 1 ? 's' : ''} < 30${NBSP}j`);
  if (untrusted > 0) parts.push(`${untrusted} à fiabiliser`);
  return `Portefeuille conformité${NBSP}: ${parts.join(' · ')}.`;
}

// ─────────────────────────────────────────────────────────────────────────────
// 10. buildSubNarrative — contexte métier sans endpoints
// ─────────────────────────────────────────────────────────────────────────────

export function buildSubNarrative(summary) {
  if (!hasSummary(summary)) return '';
  const blocked = Number(summary.kpis?.data_blocked) || 0;
  const warning = Number(summary.kpis?.data_warning) || 0;
  if (blocked > 0) {
    return `${blocked} site${blocked > 1 ? 's' : ''} bloqué${blocked > 1 ? 's' : ''} sur la gate data — priorité déblocage avant scoring conformité.`;
  }
  if (warning > 0) {
    return `${warning} site${warning > 1 ? 's' : ''} en warning gate data — compléter les champs obligatoires.`;
  }
  return 'Pipeline stable — poursuivez la trajectoire Décret Tertiaire 2030 et les attestations BACS / APER.';
}

// ─────────────────────────────────────────────────────────────────────────────
// 11. buildEmptyState — fallback businessError si summary absent
// ─────────────────────────────────────────────────────────────────────────────

export function buildEmptyState({ summary } = {}) {
  if (hasSummary(summary)) return null;
  const fb = businessErrorFallback('pipeline.no_sites');
  return { title: fb.title, message: fb.body };
}

// ─────────────────────────────────────────────────────────────────────────────
// 12. resolveTooltipExplain — router par code KPI
// ─────────────────────────────────────────────────────────────────────────────

export function resolveTooltipExplain(code, summary) {
  switch (code) {
    case 'pipeline_sites_ready':
      return interpretSitesReady(summary);
    case 'pipeline_deadlines_d30':
      return interpretDeadlinesD30(summary);
    case 'pipeline_untrusted_sites':
      return interpretUntrustedSites(summary);
    default:
      return '';
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// 12 bis. buildKpiAriaLabel — aria-label via helper (pas hardcoded JSX)
// ─────────────────────────────────────────────────────────────────────────────

export function buildKpiAriaLabel(code, summary) {
  switch (code) {
    case 'pipeline_sites_ready': {
      const k = formatSitesReady(summary);
      if (k.value == null) return 'Sites prêts : donnée indisponible';
      return `Sites prêts : ${k.value} sur ${k.total}, ${interpretSitesReady(summary)}`;
    }
    case 'pipeline_deadlines_d30': {
      const k = formatDeadlinesD30(summary);
      if (k.value == null) return 'Échéances imminentes : donnée indisponible';
      return `Échéances sous 30 jours : ${k.value}, ${interpretDeadlinesD30(summary)}`;
    }
    case 'pipeline_untrusted_sites': {
      const k = formatUntrustedSites(summary);
      if (k.value == null) return 'Sites non fiables : donnée indisponible';
      return `Sites non fiables : ${k.value} sur ${k.total}, ${interpretUntrustedSites(summary)}`;
    }
    default:
      return '';
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// 12 ter. buildFilterConfig — toolbar filters déclaratifs (pas inline JSX)
// ─────────────────────────────────────────────────────────────────────────────

export function buildFilterConfig(summary) {
  const gateValues = new Set();
  if (hasSummary(summary) && Array.isArray(summary.sites)) {
    for (const s of summary.sites) {
      if (s.gate_status) gateValues.add(s.gate_status);
    }
  }
  const gateOptions = [
    { value: '', label: 'Tous gates' },
    ...['OK', 'WARNING', 'BLOCKED']
      .filter((g) => gateValues.has(g))
      .map((g) => ({ value: g, label: g })),
  ];
  return [
    {
      id: 'gate_status',
      label: 'Gate data',
      options: gateOptions,
    },
    {
      id: 'framework',
      label: 'Framework',
      options: [
        { value: '', label: 'Tous frameworks' },
        { value: 'dt', label: 'Décret Tertiaire' },
        { value: 'bacs', label: 'BACS' },
        { value: 'aper', label: 'APER' },
      ],
    },
    {
      id: 'untrustedOnly',
      label: 'Fiabilité',
      options: [
        { value: '', label: 'Tous' },
        { value: 'untrusted', label: 'Sites à fiabiliser' },
      ],
    },
  ];
}

// ─────────────────────────────────────────────────────────────────────────────
// 13. pipelineRows — transforme sites[] en rows pour SolExpertGridFull
// ─────────────────────────────────────────────────────────────────────────────

export function pipelineRows(summary) {
  if (!hasSummary(summary)) return [];
  const sites = Array.isArray(summary.sites) ? summary.sites : [];
  return sites.map((s) => ({
    id: s.site_id,
    cells: {
      site_nom: s.site_nom ?? '—',
      gate_status: s.gate_status ?? 'UNKNOWN',
      completeness_pct: Number(s.completeness_pct) || 0,
      compliance_score: Number(s.compliance_score) || 0,
      reg_risk: Number(s.reg_risk) || 0,
      financial_opportunity_eur: Number(s.financial_opportunity_eur) || 0,
      applicable_dt: Boolean(s.applicability?.tertiaire_operat),
      applicable_bacs: Boolean(s.applicability?.bacs),
      applicable_aper: Boolean(s.applicability?.aper),
    },
  }));
}

// ─────────────────────────────────────────────────────────────────────────────
// 14. filterRows — search + gate_status + applicability + untrusted
// ─────────────────────────────────────────────────────────────────────────────

// ─────────────────────────────────────────────────────────────────────────────
// 15. sortRows — tri client-side sur enum / numérique / string
// ─────────────────────────────────────────────────────────────────────────────

const GATE_SORT_ORDER = { BLOCKED: 0, WARNING: 1, OK: 2, UNKNOWN: 3 };

export function sortRows(rows, sortBy) {
  if (!Array.isArray(rows)) return [];
  if (!sortBy || !sortBy.column) return [...rows];
  const { column, direction } = sortBy;
  const factor = direction === 'asc' ? 1 : -1;
  return [...rows].sort((a, b) => {
    const ca = a.cells || a;
    const cb = b.cells || b;
    let va = ca[column];
    let vb = cb[column];
    if (column === 'gate_status') {
      va = GATE_SORT_ORDER[va] ?? 99;
      vb = GATE_SORT_ORDER[vb] ?? 99;
    }
    if (typeof va === 'boolean') va = va ? 1 : 0;
    if (typeof vb === 'boolean') vb = vb ? 1 : 0;
    if (va == null) return 1;
    if (vb == null) return -1;
    if (typeof va === 'string' && typeof vb === 'string') {
      return va.localeCompare(vb, 'fr') * factor;
    }
    return (va - vb) * factor;
  });
}

// ─────────────────────────────────────────────────────────────────────────────
// 16. paginateRows — découpe page (aucun return null, composant décide seul)
// ─────────────────────────────────────────────────────────────────────────────

export function paginateRows(rows, page = 1, pageSize = 20) {
  if (!Array.isArray(rows)) return [];
  const safePage = Math.max(1, Number(page) || 1);
  const safeSize = Math.max(1, Number(pageSize) || 20);
  const start = (safePage - 1) * safeSize;
  return rows.slice(start, start + safeSize);
}

// ─────────────────────────────────────────────────────────────────────────────
// 14. filterRows — search + gate_status + applicability + untrusted
// ─────────────────────────────────────────────────────────────────────────────

export function filterRows(rows, filters = {}) {
  if (!Array.isArray(rows)) return [];
  const q = (filters.search ?? '').trim().toLowerCase();
  const gate = filters.gate_status ?? 'all';
  const framework = filters.framework ?? 'all';
  const untrustedIds = filters.untrustedIds instanceof Set ? filters.untrustedIds : null;
  const untrustedOnly = Boolean(filters.untrustedOnly);

  return rows.filter((r) => {
    const c = r.cells || r;
    if (q && !(c.site_nom || '').toLowerCase().includes(q)) return false;
    if (gate !== 'all' && c.gate_status !== gate) return false;
    if (framework === 'dt' && !c.applicable_dt) return false;
    if (framework === 'bacs' && !c.applicable_bacs) return false;
    if (framework === 'aper' && !c.applicable_aper) return false;
    if (untrustedOnly && untrustedIds && !untrustedIds.has(r.id)) return false;
    return true;
  });
}
