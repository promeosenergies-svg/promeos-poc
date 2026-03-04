import { Link, useLocation } from 'react-router-dom';
import { ChevronRight } from 'lucide-react';
import { ALL_NAV_ITEMS } from './NavRegistry';

// Auto-derive labels from NavRegistry (single source of truth)
const LABELS = Object.fromEntries(
  ALL_NAV_ITEMS.map((item) => {
    const segment = item.to.split('/').filter(Boolean).pop();
    return segment ? [segment, item.label] : null;
  }).filter(Boolean)
);

// Segment-level overrides not covered by NavRegistry
Object.assign(LABELS, {
  '': 'Tableau de bord',
  'sites': 'Site',
  'compliance': 'Conformité',
  'status': 'Statut',
  'login': 'Connexion',
  'explorer': 'Explorer',
  'portfolio': 'Portefeuille',
  'wizard': 'Assistant',
  'tertiaire': 'Tertiaire / OPERAT',
  'efa': 'EFA',
  'new': 'Nouveau',
  // Aliases for redirect paths
  'factures': 'Facturation',
  'facturation': 'Facturation',
  'plan-action': "Plan d'actions",
  'plan-actions': "Plan d'actions",
  'diagnostic': 'Diagnostic',
  'achats': 'Achats énergie',
  'purchase': 'Achats énergie',
  'referentiels': 'Mémobox',
  'synthese': 'Vue exécutive',
  'executive': 'Vue exécutive',
  'dashboard': 'Tableau de bord',
  'conso': 'Consommations',
  'imports': 'Imports',
  'connexions': 'Connexions',
  'alertes': 'Alertes',
});

/**
 * DYNAMIC_CONTEXT — maps "parent segment" to label prefix for dynamic :id segments.
 * When a numeric/alphanumeric ID follows one of these parent segments,
 * the breadcrumb shows "Label #id" instead of the raw ID.
 *
 * e.g. /sites/42 → "Site #42", /actions/7 → "Action #7"
 */
const DYNAMIC_CONTEXT = {
  'sites':      'Site',
  'actions':    'Action',
  'efa':        'EFA',
  'compliance': 'Conformité',
};

/** Check if a segment looks like a dynamic ID (numeric or UUID-like) */
function isDynamicSegment(segment) {
  return /^\d+$/.test(segment) || /^[0-9a-f]{8,}$/i.test(segment);
}

/**
 * Resolve label for a breadcrumb segment.
 * - Static segments → LABELS lookup
 * - Dynamic IDs → parent-aware contextual label ("Site #42")
 * - Never returns raw English or empty string
 */
export function resolveBreadcrumbLabel(segment, parentSegment) {
  // Known label
  if (LABELS[segment]) return LABELS[segment];
  // Dynamic ID with parent context
  if (isDynamicSegment(segment) && parentSegment) {
    const ctx = DYNAMIC_CONTEXT[parentSegment];
    if (ctx) return `${ctx} #${segment}`;
  }
  // Fallback: capitalize segment, replace hyphens
  if (isDynamicSegment(segment)) return `#${segment}`;
  return segment.charAt(0).toUpperCase() + segment.slice(1).replace(/-/g, ' ');
}

export default function Breadcrumb() {
  const { pathname } = useLocation();
  const parts = pathname.split('/').filter(Boolean);

  const crumbs = [{ label: 'PROMEOS', to: '/' }];
  let path = '';
  for (let i = 0; i < parts.length; i++) {
    path += '/' + parts[i];
    const parent = i > 0 ? parts[i - 1] : null;
    crumbs.push({ label: resolveBreadcrumbLabel(parts[i], parent), to: path });
  }

  return (
    <nav className="flex items-center gap-1 text-sm text-gray-500">
      {crumbs.map((c, i) => (
        <span key={c.to} className="flex items-center gap-1">
          {i > 0 && <ChevronRight size={14} className="text-gray-300" />}
          {i < crumbs.length - 1 ? (
            <Link to={c.to} className="hover:text-blue-600 hover:underline underline-offset-2 transition">{c.label}</Link>
          ) : (
            <span className="text-gray-800 font-medium">{c.label}</span>
          )}
        </span>
      ))}
    </nav>
  );
}
