/**
 * PROMEOS — KBExplorerSol presenters (Lot 6 Phase 2, Pattern B pur)
 *
 * API consommée (parent KBExplorerPage.jsx) :
 *   searchKBItems({q, domain?, type?, limit}) → { results: [{
 *     id, title, domain, type, confidence, status, content_md,
 *     summary, tags, logic, sources, priority, updated_at
 *   }] }
 *   getKBFullStats() → { total_items, by_status, by_domain }
 *   getKBDocs({domain?, status?}) → { docs: [{
 *     doc_id, title, source_type, nb_chunks, content_hash,
 *     domain, status, updated_at
 *   }] }
 */
import { NBSP, formatFR } from '../cockpit/sol_presenters';
import { businessErrorFallback } from '../../i18n/business_errors';

export { NBSP, formatFR };

// ─────────────────────────────────────────────────────────────────────────────
// Labels + tones
// ─────────────────────────────────────────────────────────────────────────────

export const DOMAIN_LABELS = {
  reglementaire: 'Réglementaire',
  usages: 'Usages',
  acc: 'ACC',
  facturation: 'Facturation',
  flex: 'Flex',
};

export const TYPE_LABELS = {
  rule: 'Règle',
  knowledge: 'Connaissance',
  checklist: 'Checklist',
  calc: 'Calcul',
};

export const STATUS_LABELS = {
  draft: 'Brouillon',
  review: 'En revue',
  validated: 'Validé',
  decisional: 'Décisionnel',
};

const STATUS_TONE = {
  draft: 'afaire',
  review: 'attention',
  validated: 'succes',
  decisional: 'calme',
};

const CONFIDENCE_TONE = {
  high: 'succes',
  medium: 'attention',
  low: 'afaire',
};

export function toneFromStatus(s) {
  return STATUS_TONE[s] || 'afaire';
}

export function toneFromConfidence(c) {
  return CONFIDENCE_TONE[c] || 'afaire';
}

// ─────────────────────────────────────────────────────────────────────────────
// Date helper
// ─────────────────────────────────────────────────────────────────────────────

export function formatDateFR(dateStr) {
  if (!dateStr) return '—';
  const d = new Date(dateStr);
  if (isNaN(d.getTime())) return dateStr;
  return d.toLocaleDateString('fr-FR', { day: '2-digit', month: 'short', year: 'numeric' });
}

// ─────────────────────────────────────────────────────────────────────────────
// KPIs computation
// ─────────────────────────────────────────────────────────────────────────────

export function computeKpis(stats) {
  if (!stats) {
    return { total: null, validated: null, domainsCovered: null };
  }
  const total = Number(stats.total_items) || 0;
  const validated = Number(stats.by_status?.validated) || 0;
  const domainsCovered = stats.by_domain
    ? Object.keys(stats.by_domain).filter((k) => Number(stats.by_domain[k]) > 0).length
    : 0;
  return {
    total,
    validated,
    validatedRatio: total > 0 ? Math.round((validated / total) * 100) : null,
    domainsCovered,
  };
}

// ─────────────────────────────────────────────────────────────────────────────
// Kicker + narratives
// ─────────────────────────────────────────────────────────────────────────────

export function buildKbKicker({ activeTab, stats } = {}) {
  const kpis = computeKpis(stats);
  const total = kpis.total;
  const mode = activeTab === 'docs' ? 'DOCUMENTS' : 'ITEMS';
  if (total == null) return `BASE CONNAISSANCE · ${mode}`;
  return `BASE CONNAISSANCE · ${mode} · ${total}${NBSP}INDEXÉ${total > 1 ? 'S' : ''}`;
}

export function buildKbNarrative({ stats, activeTab } = {}) {
  if (!stats) {
    return 'Chargement des statistiques du moteur de connaissance en cours.';
  }
  const kpis = computeKpis(stats);
  if (kpis.total === 0) {
    return "Base de connaissance vide — aucun article indexé pour le moment. Uploadez votre premier document via l'onglet Documents.";
  }
  const parts = [];
  parts.push(
    `${kpis.total}${NBSP}article${kpis.total > 1 ? 's' : ''} indexé${kpis.total > 1 ? 's' : ''}`
  );
  if (kpis.validated > 0) {
    parts.push(
      `${kpis.validated}${NBSP}validé${kpis.validated > 1 ? 's' : ''} (${kpis.validatedRatio}${NBSP}%)`
    );
  }
  parts.push(
    `${kpis.domainsCovered}${NBSP}domaine${kpis.domainsCovered > 1 ? 's' : ''} couvert${kpis.domainsCovered > 1 ? 's' : ''}`
  );
  if (activeTab === 'docs') {
    parts.push('mode Documents — PDF/CSV sources');
  } else {
    parts.push('mode Items — fiches structurées (règles, connaissances, checklists, calculs)');
  }
  return parts.join(' · ') + '.';
}

export function buildKbSubNarrative({ stats } = {}) {
  if (!stats) {
    return 'Moteur : SQLite FTS5 · sources : Légifrance, ADEME, CRE, RTE + uploads internes.';
  }
  const by = stats.by_domain || {};
  const top = Object.entries(by)
    .filter(([, n]) => Number(n) > 0)
    .sort((a, b) => Number(b[1]) - Number(a[1]))
    .slice(0, 3)
    .map(([k, n]) => `${DOMAIN_LABELS[k] || k}${NBSP}${n}`);
  const mix = top.length > 0 ? `Mix domaines : ${top.join(' · ')}. ` : '';
  return mix + 'Moteur FTS5 · sources internes + externes agrégées.';
}

// ─────────────────────────────────────────────────────────────────────────────
// KPI interpretations
// ─────────────────────────────────────────────────────────────────────────────

export function interpretTotalItems({ stats } = {}) {
  const kpis = computeKpis(stats);
  if (kpis.total == null)
    return 'Statistiques indisponibles — base de connaissance en initialisation.';
  if (kpis.total === 0) return 'Base vide — uploadez votre premier document.';
  return `${kpis.domainsCovered}${NBSP}domaine${kpis.domainsCovered > 1 ? 's' : ''} couvert${kpis.domainsCovered > 1 ? 's' : ''} · base active.`;
}

export function interpretValidatedRatio({ stats } = {}) {
  const kpis = computeKpis(stats);
  if (kpis.validatedRatio == null) return 'Aucun article encore validé.';
  if (kpis.validatedRatio >= 80) return 'Base de haute fiabilité · usage décisionnel activable.';
  if (kpis.validatedRatio >= 50)
    return 'Base partiellement validée · revue recommandée sur les brouillons.';
  return 'Nombreux brouillons en attente · prioriser la revue éditoriale.';
}

export function interpretDomainsCovered({ stats } = {}) {
  const kpis = computeKpis(stats);
  if (!kpis.domainsCovered) return 'Aucun domaine couvert — base à amorcer.';
  const total = 5; // 5 domaines Sol définis
  if (kpis.domainsCovered === total) return 'Couverture complète des 5 domaines Sol.';
  return `${kpis.domainsCovered}${NBSP}sur${NBSP}${total} domaines couverts · étendre pour compléter.`;
}

// ─────────────────────────────────────────────────────────────────────────────
// Rows builders (items et docs)
// ─────────────────────────────────────────────────────────────────────────────

export function buildItemRows(items = []) {
  return (items || []).map((it) => ({
    id: `item-${it.id}`,
    cells: {
      title: it.title || 'Article sans titre',
      domain: it.domain,
      type: it.type,
      confidence: it.confidence || 'medium',
      status: it.status || 'draft',
      updated_at: it.updated_at,
      _raw: it,
    },
    tone: null,
  }));
}

export function buildDocRows(docs = []) {
  return (docs || []).map((d) => ({
    id: `doc-${d.doc_id}`,
    cells: {
      title: d.title || 'Document sans titre',
      source_type: d.source_type || 'pdf',
      domain: d.domain,
      nb_chunks: Number(d.nb_chunks) || 0,
      status: d.status || 'draft',
      updated_at: d.updated_at,
      _raw: d,
    },
    tone: null,
  }));
}

// ─────────────────────────────────────────────────────────────────────────────
// Filter + sort + paginate (client-side)
// ─────────────────────────────────────────────────────────────────────────────

export function filterRows(rows, { search, domain, type, status } = {}) {
  let r = rows;
  if (domain) r = r.filter((x) => x.cells.domain === domain);
  if (type) r = r.filter((x) => x.cells.type === type);
  if (status) r = r.filter((x) => x.cells.status === status);
  if (search) {
    const q = search.toLowerCase();
    r = r.filter(
      (x) =>
        String(x.cells.title || '')
          .toLowerCase()
          .includes(q) ||
        String(x.cells._raw?.summary || '')
          .toLowerCase()
          .includes(q) ||
        String(x.cells._raw?.tags || '')
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
    if (sortBy.column === 'updated_at') {
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

export function buildEmptyState({ hasFilters, hasAny } = {}) {
  if (hasFilters) {
    const fb = businessErrorFallback('kb.filter_no_results');
    return { title: fb.title, message: fb.body };
  }
  if (!hasAny) {
    const fb = businessErrorFallback('kb.no_results');
    return { title: fb.title, message: fb.body };
  }
  return null;
}

// ─────────────────────────────────────────────────────────────────────────────
// Filter config (mode-dependent)
// ─────────────────────────────────────────────────────────────────────────────

export function buildFilterConfig({ activeTab, stats } = {}) {
  const byDomain = stats?.by_domain || {};
  const domainOptions = Object.keys(DOMAIN_LABELS)
    .filter((k) => Number(byDomain[k] ?? 0) > 0 || !stats)
    .map((k) => ({ value: k, label: DOMAIN_LABELS[k] }));

  const base = [
    {
      id: 'domain',
      label: 'Domaine',
      options: domainOptions,
    },
  ];

  if (activeTab === 'docs') {
    base.push({
      id: 'status',
      label: 'Statut',
      options: [
        { value: 'draft', label: 'Brouillon' },
        { value: 'review', label: 'En revue' },
        { value: 'validated', label: 'Validé' },
        { value: 'decisional', label: 'Décisionnel' },
      ],
    });
  } else {
    base.push({
      id: 'type',
      label: 'Type',
      options: [
        { value: 'rule', label: 'Règle' },
        { value: 'knowledge', label: 'Connaissance' },
        { value: 'checklist', label: 'Checklist' },
        { value: 'calc', label: 'Calcul' },
      ],
    });
  }
  return base;
}
