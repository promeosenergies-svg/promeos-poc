/**
 * PROMEOS — WatchersSol presenters (Lot 2 Phase 7, Pattern B prélude cards)
 *
 * API consommée (parent WatchersPage.jsx) :
 *   listWatchers() → { watchers: [{ name, description }] }
 *   listRegEvents(source?, ?, status?) → { events: [{
 *     id, title, source_name, published_at, tags, status (new/
 *     reviewed/applied/dismissed), snippet, url, review_note,
 *     reviewed_at, reviewed_by
 *   }] }
 *   runWatcher(name) → { new_events, error? }
 *   reviewRegEvent(id, decision, notes) → void
 *
 * IMPORTANT — divergences spec user → API réelle :
 *   - `watcher_active_count` spec (implique pause) → API n'a pas de
 *     pause. Renommé `watcher_total_count`.
 *   - `watcher_coverage_pct` spec → API n'expose pas de coverage par
 *     site. Remap → `watcher_new_events_count` (events à traiter
 *     actionnable).
 *   - `triggers_30d` remappable via events.published_at.
 */
import { NBSP, formatFR } from '../cockpit/sol_presenters';
import { businessErrorFallback } from '../../i18n/business_errors';

export { NBSP, formatFR };

// ─────────────────────────────────────────────────────────────────────────────
// Labels + tones
// ─────────────────────────────────────────────────────────────────────────────

export const STATUS_LABELS = {
  new: 'Nouveau',
  reviewed: 'Révisé',
  applied: 'Appliqué',
  dismissed: 'Ignoré',
};

const STATUS_TONE = {
  new: 'attention',
  reviewed: 'afaire',
  applied: 'succes',
  dismissed: 'calme',
};

export function toneFromStatus(s) {
  return STATUS_TONE[s] || 'attention';
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
// KPIs + narratives
// ─────────────────────────────────────────────────────────────────────────────

export function buildWatchersKicker({ scopeLabel, watchersCount } = {}) {
  const scope = scopeLabel ? scopeLabel.toUpperCase() : 'TOUS LES SITES';
  const n = Number(watchersCount) || 0;
  return `WATCHERS · ${scope} · ${n}${NBSP}CONFIGURÉ${n > 1 ? 'S' : ''}`;
}

export function countEvents30d(events = []) {
  const now = Date.now();
  const thirtyDays = 30 * 24 * 3600 * 1000;
  return events.filter((e) => {
    if (!e?.published_at) return false;
    const t = new Date(e.published_at).getTime();
    return Number.isFinite(t) && now - t <= thirtyDays;
  }).length;
}

export function countNewEvents(events = []) {
  return events.filter((e) => !e?.status || e.status === 'new').length;
}

export function findTopSource(events = []) {
  const by = {};
  for (const e of events || []) {
    const k = e?.source_name;
    if (!k) continue;
    by[k] = (by[k] || 0) + 1;
  }
  const sorted = Object.entries(by).sort((a, b) => b[1] - a[1]);
  return sorted[0] || null;
}

export function buildWatchersNarrative({ watchers = [], events = [] } = {}) {
  const nbWatchers = watchers.length;
  const newCount = countNewEvents(events);
  const count30d = countEvents30d(events);

  if (nbWatchers === 0) {
    return 'Aucun watcher configuré. Créez votre premier watcher pour activer la veille réglementaire et marché.';
  }

  const parts = [`${nbWatchers}${NBSP}watcher${nbWatchers > 1 ? 's' : ''} configuré${nbWatchers > 1 ? 's' : ''}`];
  if (count30d > 0) {
    parts.push(`${count30d}${NBSP}événement${count30d > 1 ? 's' : ''} captés sur 30${NBSP}jours`);
  }
  if (newCount > 0) {
    parts.push(`${newCount}${NBSP}à réviser`);
  }
  const top = findTopSource(events);
  if (top) {
    parts.push(`source dominante : ${top[0]} (${top[1]}${NBSP}événements)`);
  }
  return parts.join(' · ') + '.';
}

export function buildWatchersSubNarrative({ events = [] } = {}) {
  const total = events.length;
  const applied = events.filter((e) => e.status === 'applied').length;
  const dismissed = events.filter((e) => e.status === 'dismissed').length;
  const parts = [];
  if (total > 0) {
    parts.push(`${total}${NBSP}événement${total > 1 ? 's' : ''} total`);
    if (applied > 0) parts.push(`${applied}${NBSP}appliqué${applied > 1 ? 's' : ''}`);
    if (dismissed > 0) parts.push(`${dismissed}${NBSP}ignoré${dismissed > 1 ? 's' : ''}`);
  }
  const head = parts.length > 0 ? `Historique : ${parts.join(' · ')}. ` : '';
  return (
    head +
    'Sources : Légifrance, CRE, RTE + agrégateurs marché. Stockage minimal (hash + snippet 500 chars, droits d\'auteur respectés).'
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// KPI interpretations
// ─────────────────────────────────────────────────────────────────────────────

export function interpretWatchersCount({ watchers = [] } = {}) {
  const n = watchers.length;
  if (n === 0) return 'Aucun watcher configuré — créer via bouton Nouveau.';
  if (n <= 3) return 'Couverture minimale — envisager d\'ajouter des sources complémentaires.';
  return 'Couverture veille active sur sources multiples.';
}

export function interpretNewEvents({ events = [] } = {}) {
  const n = countNewEvents(events);
  if (n === 0) return 'Aucun événement en attente — backlog à jour.';
  return `${n}${NBSP}événement${n > 1 ? 's' : ''} à réviser · cliquer sur la ligne pour ouvrir.`;
}

export function interpretEvents30d({ events = [] } = {}) {
  const n = countEvents30d(events);
  if (n === 0) return 'Aucun événement sur 30 jours — veille calme.';
  const top = findTopSource(events);
  if (top) return `Top source : ${top[0]} · ${top[1]}${NBSP}événement${top[1] > 1 ? 's' : ''}.`;
  return `${n}${NBSP}événement${n > 1 ? 's' : ''} captés.`;
}

// ─────────────────────────────────────────────────────────────────────────────
// Rows builder
// ─────────────────────────────────────────────────────────────────────────────

export function buildEventRows(events = []) {
  return (events || []).map((e) => ({
    id: `event-${e.id}`,
    cells: {
      published_at: e.published_at,
      title: e.title || 'Événement sans titre',
      source_name: e.source_name || '—',
      tags: e.tags || '',
      status: e.status || 'new',
      snippet: e.snippet || '',
      url: e.url || null,
      _raw: e,
    },
    tone: e.status === 'new' ? 'attention' : null,
  }));
}

// ─────────────────────────────────────────────────────────────────────────────
// Filter + sort
// ─────────────────────────────────────────────────────────────────────────────

export function filterRows(rows, { search, source, status } = {}) {
  let r = rows;
  if (source) r = r.filter((x) => x.cells.source_name === source);
  if (status) r = r.filter((x) => x.cells.status === status);
  if (search) {
    const q = search.toLowerCase();
    r = r.filter(
      (x) =>
        String(x.cells.title || '').toLowerCase().includes(q) ||
        String(x.cells.source_name || '').toLowerCase().includes(q) ||
        String(x.cells.tags || '').toLowerCase().includes(q)
    );
  }
  return r;
}

export function sortRows(rows, sortBy) {
  if (!sortBy?.column) return rows;
  const sorted = [...rows].sort((a, b) => {
    const va = a.cells[sortBy.column];
    const vb = b.cells[sortBy.column];
    if (sortBy.column === 'published_at') {
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

// ─────────────────────────────────────────────────────────────────────────────
// Empty state + filter config
// ─────────────────────────────────────────────────────────────────────────────

export function buildEmptyState({ hasFilters, hasAnyEvent } = {}) {
  if (hasFilters) {
    const fb = businessErrorFallback('watcher.filter_no_results');
    return { title: fb.title, message: fb.body };
  }
  if (!hasAnyEvent) {
    const fb = businessErrorFallback('watcher.no_watchers');
    return { title: fb.title, message: fb.body };
  }
  return null;
}

export function buildFilterConfig({ watchers = [], events = [] } = {}) {
  const sources = Array.from(
    new Set([
      ...(watchers || []).map((w) => w.name).filter(Boolean),
      ...(events || []).map((e) => e.source_name).filter(Boolean),
    ])
  );
  return [
    {
      id: 'source',
      label: 'Source',
      options: sources.slice(0, 10).map((s) => ({ value: s, label: s })),
    },
    {
      id: 'status',
      label: 'Statut',
      options: [
        { value: 'new', label: 'Nouveau' },
        { value: 'reviewed', label: 'Révisé' },
        { value: 'applied', label: 'Appliqué' },
        { value: 'dismissed', label: 'Ignoré' },
      ],
    },
  ];
}
