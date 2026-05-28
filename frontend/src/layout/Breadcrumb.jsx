import { useMemo } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { ChevronRight } from 'lucide-react';
import { ALL_NAV_ITEMS, ROUTE_SECTION_MAP, NAV_MAIN_SECTIONS, getModuleTint } from './NavRegistry';
import { useScope } from '../contexts/ScopeContext';

// Auto-derive labels from NavRegistry (single source of truth)
const LABELS = Object.fromEntries(
  ALL_NAV_ITEMS.map((item) => {
    const basePath = item.to.split('?')[0].split('#')[0];
    const segment = basePath.split('/').filter(Boolean).pop();
    return segment ? [segment, item.label] : null;
  }).filter(Boolean)
);

// Segment-level overrides not covered by NavRegistry
// Phase 1.A — P0.2 : labels legacy redirect ("synthese", "executive",
// "dashboard") résolus en libellés canoniques Sol §11.3 ("Synthèse
// stratégique" / "Briefing du jour") pour cohérence breadcrumb avec
// le panel rail. Root path `/` (redirige `/cockpit/strategique` via
// Phase 13.D) → "Synthèse stratégique".
Object.assign(LABELS, {
  '': 'Synthèse stratégique',
  sites: 'Site',
  conformite: 'Conformité',
  compliance: 'Conformité',
  status: 'Statut',
  login: 'Connexion',
  explorer: 'Explorer',
  // Énergie P0b visual credibility (2026-05-27, brief C2) — alignement
  // rail (« Portefeuille » dans ConsommationsPage tabs) / breadcrumb /
  // H1 ConsumptionPortfolioPage (« Portefeuille Consommation »). Avant,
  // le breadcrumb affichait « Regroupement » pour /consommations/portfolio
  // → désynchronisation avec le rail et le titre de page.
  portfolio: 'Portefeuille',
  wizard: 'Assistant',
  // S2 hotfix (2026-05-28) — le libellé « Tertiaire / OPERAT » contenait
  // un slash qui, à cause du wrapping CSS, apparaissait coupé en deux
  // lignes (« Tertiaire » puis « / OPERAT ») et donnait l'illusion d'une
  // sous-route « /OPERAT » qui n'existe pas. Libellé unifié en référence
  // canonique réglementaire (Décret n°2019-771).
  tertiaire: 'Décret Tertiaire',
  efa: 'EFA',
  new: 'Nouveau',
  // Aliases for redirect paths
  // Phase 1.D — P0.1 : `bill-intel` retiré des overrides — le segment est
  // désormais auto-dérivé depuis NAV_SECTIONS.facturation.items (label
  // "Vue d'ensemble"). Avec la section "Facturation" ajoutée en amont
  // par resolveSectionLabel, le breadcrumb devient
  // "Facturation > Vue d'ensemble" (au lieu du doublon Facturation/Facturation).
  factures: 'Facturation',
  facturation: 'Facturation',
  'plan-action': "Plan d'actions",
  'plan-actions': "Plan d'actions",
  diagnostic: 'Diagnostic',
  achats: 'Achats énergie',
  purchase: 'Achats énergie',
  referentiels: 'Mémobox',
  kb: 'Mémobox',
  synthese: 'Synthèse stratégique',
  executive: 'Synthèse stratégique',
  dashboard: 'Briefing du jour',
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
 * Resolve section label from pathname.
 * Only uses exact match from ROUTE_SECTION_MAP — no prefix matching
 * to avoid false positives with nested routes.
 */
function resolveSectionLabel(pathname) {
  return ROUTE_SECTION_MAP[pathname] || null;
}

/** Get the first route of a section (for clickable breadcrumb) */
function getSectionRoute(sectionLabel) {
  const section = NAV_MAIN_SECTIONS.find((s) => s.label === sectionLabel);
  return section?.items[0]?.to || '/';
}

export default function Breadcrumb() {
  const { pathname } = useLocation();
  const { scopedSites } = useScope();
  const tint = getModuleTint(pathname);
  const parts = pathname.split('/').filter(Boolean);

  const siteNameById = useMemo(
    () =>
      scopedSites?.reduce((acc, s) => {
        acc[String(s.id)] = s.nom;
        return acc;
      }, {}) || {},
    [scopedSites]
  );

  const crumbs = [{ label: 'PROMEOS', to: '/' }];

  // Root path → simple breadcrumb
  // Phase 1.A — P0.2 : `/` redirige sur `/cockpit/strategique` (Phase 13.D),
  // donc le crumb root affiche le libellé canonique Sol §11.3. La SoT
  // est le LABELS map ci-dessus (segment '' → "Synthèse stratégique") —
  // on le réutilise au lieu de hardcoder le libellé.
  if (parts.length === 0) {
    crumbs.push({ label: LABELS[''], to: '/' });
    return <BreadcrumbNav crumbs={crumbs} tintText={tint?.activeText} />;
  }

  // Add section crumb if the page belongs to a known section
  const sectionLabel = resolveSectionLabel(pathname);
  if (sectionLabel) {
    const sectionRoute = getSectionRoute(sectionLabel);
    const pageLabel = resolveBreadcrumbLabel(parts[0], null);
    // Only add if section label differs from the page label
    if (pageLabel !== sectionLabel) {
      crumbs.push({ label: sectionLabel, to: sectionRoute });
    }
  }

  // Build crumbs from URL segments
  let path = '';
  for (let i = 0; i < parts.length; i++) {
    path += '/' + parts[i];
    const parent = i > 0 ? parts[i - 1] : null;
    let label;
    if (parent === 'sites' && isDynamicSegment(parts[i]) && siteNameById[parts[i]]) {
      label = siteNameById[parts[i]];
    } else {
      label = resolveBreadcrumbLabel(parts[i], parent);
    }
    crumbs.push({ label, to: path });
  }

  // Deduplicate: remove any crumb whose label already appeared earlier
  const seen = new Set();
  const deduped = crumbs.filter((c) => {
    const key = c.label.toLowerCase();
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });

  return <BreadcrumbNav crumbs={deduped} tintText={tint?.activeText} />;
}

function BreadcrumbNav({ crumbs, tintText }) {
  return (
    <nav
      key={crumbs.map((c) => c.to).join('/')}
      className="flex items-center gap-1 text-sm text-gray-500 animate-[fadeIn_0.2s_ease-out]"
    >
      {crumbs.map((c, i) => (
        <span key={`${c.to}-${i}`} className="flex items-center gap-1">
          {i > 0 && <ChevronRight size={14} className="text-gray-300" />}
          {i < crumbs.length - 1 ? (
            <Link
              to={c.to}
              className="hover:text-blue-600 hover:underline underline-offset-2 transition"
            >
              {c.label}
            </Link>
          ) : (
            <span className={`font-medium ${tintText || 'text-gray-800'}`}>{c.label}</span>
          )}
        </span>
      ))}
    </nav>
  );
}
