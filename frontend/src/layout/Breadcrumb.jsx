import { Link, useLocation } from 'react-router-dom';
import { ChevronRight } from 'lucide-react';
import { ALL_NAV_ITEMS, ROUTE_SECTION_MAP, NAV_MAIN_SECTIONS } from './NavRegistry';
import { useScope } from '../contexts/ScopeContext';

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
  sites: 'Site',
  compliance: 'Conformité',
  status: 'Statut',
  login: 'Connexion',
  explorer: 'Explorer',
  portfolio: 'Portefeuille',
  wizard: 'Assistant',
  tertiaire: 'Tertiaire / OPERAT',
  efa: 'EFA',
  new: 'Nouveau',
  // Aliases for redirect paths
  factures: 'Facturation',
  facturation: 'Facturation',
  'plan-action': "Plan d'actions",
  'plan-actions': "Plan d'actions",
  diagnostic: 'Diagnostic',
  achats: 'Achats énergie',
  purchase: 'Achats énergie',
  referentiels: 'Mémobox',
  kb: 'Mémobox',
  synthese: 'Vue exécutive',
  executive: 'Vue exécutive',
  dashboard: 'Tableau de bord',
  conso: 'Consommations',
  imports: 'Imports',
  connexions: 'Connexions',
  alertes: 'Alertes',
});

/**
 * DYNAMIC_CONTEXT — maps "parent segment" to label prefix for dynamic :id segments.
 * When a numeric/alphanumeric ID follows one of these parent segments,
 * the breadcrumb shows "Label #id" instead of the raw ID.
 *
 * e.g. /sites/42 → "Site #42", /actions/7 → "Action #7"
 */
const DYNAMIC_CONTEXT = {
  sites: 'Site',
  actions: 'Action',
  efa: 'EFA',
  compliance: 'Conformité',
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
  if (!segment) return '';
  if (isDynamicSegment(segment)) return `#${segment}`;
  return segment.charAt(0).toUpperCase() + segment.slice(1).replace(/-/g, ' ');
}

/**
 * Resolve section label from pathname for breadcrumb prefix.
 * Tries exact match first, then longest prefix match.
 */
function resolveSectionLabel(pathname) {
  // Exact match
  if (ROUTE_SECTION_MAP[pathname]) return ROUTE_SECTION_MAP[pathname];
  // Prefix match (longest first)
  const sorted = Object.keys(ROUTE_SECTION_MAP).sort((a, b) => b.length - a.length);
  for (const route of sorted) {
    if (pathname === route || pathname.startsWith(route + '/')) {
      return ROUTE_SECTION_MAP[route];
    }
  }
  // Fallback: check NAV_MAIN_SECTIONS for root section
  if (pathname === '/') return 'TABLEAU DE BORD';
  return null;
}

/** Get the first route of a section (for clickable breadcrumb) */
function getSectionRoute(sectionLabel) {
  const section = NAV_MAIN_SECTIONS.find((s) => s.label === sectionLabel);
  return section?.items[0]?.to || '/';
}

export default function Breadcrumb() {
  const { pathname } = useLocation();
  const { scopedSites } = useScope();
  const parts = pathname.split('/').filter(Boolean);

  // Build a lookup for dynamic site names
  const siteNameById =
    scopedSites?.reduce((acc, s) => {
      acc[String(s.id)] = s.nom;
      return acc;
    }, {}) || {};

  const crumbs = [{ label: 'PROMEOS', to: '/' }];

  // B.2: Add section crumb (Section > Page > Context)
  const sectionLabel = resolveSectionLabel(pathname);
  if (sectionLabel) {
    const sectionRoute = getSectionRoute(sectionLabel);
    // Only add section crumb if it's not the same as the page itself
    const pageLabel = parts.length > 0 ? resolveBreadcrumbLabel(parts[0], null) : null;
    if (pageLabel !== sectionLabel) {
      crumbs.push({ label: sectionLabel, to: sectionRoute });
    }
  }

  let path = '';
  for (let i = 0; i < parts.length; i++) {
    path += '/' + parts[i];
    const parent = i > 0 ? parts[i - 1] : null;
    // Resolve actual entity names for dynamic IDs (e.g. /sites/4 → "Siege HELIOS Paris")
    let label;
    if (parent === 'sites' && isDynamicSegment(parts[i]) && siteNameById[parts[i]]) {
      label = siteNameById[parts[i]];
    } else {
      label = resolveBreadcrumbLabel(parts[i], parent);
    }
    crumbs.push({ label, to: path });
  }

  return (
    <nav className="flex items-center gap-1 text-sm text-gray-500">
      {crumbs.map((c, i) => (
        <span key={c.to} className="flex items-center gap-1">
          {i > 0 && <ChevronRight size={14} className="text-gray-300" />}
          {i < crumbs.length - 1 ? (
            <Link
              to={c.to}
              className="hover:text-blue-600 hover:underline underline-offset-2 transition"
            >
              {c.label}
            </Link>
          ) : (
            <span className="text-gray-800 font-medium">{c.label}</span>
          )}
        </span>
      ))}
    </nav>
  );
}
