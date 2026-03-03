/**
 * PROMEOS — Navigation Registry (Rail + Panel Architecture)
 * 5 modules stables, each with a tint color:
 * Cockpit / Operations / Analyse / Marche / Admin
 *
 * Normal mode: Cockpit + Operations + Analyse core (~7 visible items)
 * Expert mode: + Diagnostic + Marche + Admin (Donnees & IAM)
 */
import {
  LayoutDashboard, Building2, ShieldCheck, FileText,
  Zap, ListChecks, Activity, Import, Users, Receipt, CalendarRange,
  BookOpen, ShoppingCart, Search, Link2, Eye, Bell, Lock,
  Target, Database, ScanLine, ListPlus, AlertTriangle, BadgeEuro,
} from 'lucide-react';

/* ── Route → module mapping (for permission checks + auto-select) ──
 * Static routes (exact match) + dynamic patterns (:param segments).
 * Dynamic patterns are matched by matchRouteToModule() with "best match wins".
 */
export const ROUTE_MODULE_MAP = {
  '/': 'cockpit',
  '/cockpit': 'cockpit',
  '/notifications': 'cockpit',
  '/conformite': 'operations',
  '/conformite/tertiaire': 'operations',
  '/conformite/tertiaire/wizard': 'operations',
  '/conformite/tertiaire/anomalies': 'operations',
  '/conformite/tertiaire/efa/:id': 'operations',
  '/actions': 'operations',
  '/actions/new': 'operations',
  '/actions/:actionId': 'operations',
  '/anomalies': 'operations',
  '/consommations': 'analyse',
  '/consommations/explorer': 'analyse',
  '/consommations/import': 'analyse',
  '/consommations/kb': 'analyse',
  '/consommations/portfolio': 'analyse',
  '/diagnostic-conso': 'analyse',
  '/usages-horaires': 'analyse',
  '/monitoring': 'analyse',
  '/billing': 'marche',
  '/bill-intel': 'marche',
  '/achat-energie': 'marche',
  '/achat-assistant': 'marche',
  '/patrimoine': 'admin',
  '/payment-rules': 'admin',
  '/sites/:id': 'admin',
  '/import': 'admin',
  '/connectors': 'admin',
  '/segmentation': 'admin',
  '/watchers': 'admin',
  '/kb': 'admin',
  '/admin/users': 'admin',
  '/admin/roles': 'admin',
  '/admin/assignments': 'admin',
  '/admin/audit': 'admin',
  '/compliance': 'operations',
  '/compliance/pipeline': 'operations',
  '/compliance/findings': 'operations',
  '/compliance/obligations': 'operations',
  '/compliance/sites/:siteId': 'operations',
  '/activation': 'admin',
  '/status': 'admin',
};

/**
 * matchRouteToModule(pathname) — "best match wins" route resolver.
 *
 * Strategy:
 * 1. Exact match in ROUTE_MODULE_MAP (fastest path).
 * 2. Pattern match with dynamic segments (:param). More segments = more specific = higher priority.
 * 3. Prefix fallback (legacy compat).
 * 4. Default → 'cockpit'.
 *
 * Ignores querystring and hash. Pure function, fully testable.
 *
 * @param {string} pathname — e.g. '/sites/42', '/actions/123', '/conformite/tertiaire/efa/7'
 * @returns {{ moduleId: string, moduleLabel: string, pattern: string|null }}
 */
export function matchRouteToModule(pathname) {
  // Strip querystring/hash
  const clean = pathname.split('?')[0].split('#')[0];

  // 1. Exact match
  if (ROUTE_MODULE_MAP[clean]) {
    return _result(clean, ROUTE_MODULE_MAP[clean]);
  }

  // 2. Pattern match — score by number of matching segments (more = better)
  const segments = clean.split('/').filter(Boolean);
  let bestPattern = null;
  let bestScore = -1;

  for (const pattern of Object.keys(ROUTE_MODULE_MAP)) {
    if (!pattern.includes(':')) continue; // skip static routes (already checked)
    const patternSegs = pattern.split('/').filter(Boolean);
    if (patternSegs.length !== segments.length) continue;

    let match = true;
    let score = 0;
    for (let i = 0; i < patternSegs.length; i++) {
      if (patternSegs[i].startsWith(':')) {
        score += 1; // dynamic segment matches anything but scores less
      } else if (patternSegs[i] === segments[i]) {
        score += 2; // exact segment match scores more
      } else {
        match = false;
        break;
      }
    }
    if (match && score > bestScore) {
      bestScore = score;
      bestPattern = pattern;
    }
  }

  if (bestPattern) {
    return _result(bestPattern, ROUTE_MODULE_MAP[bestPattern]);
  }

  // 3. Prefix fallback (sorted longest first)
  const sorted = Object.keys(ROUTE_MODULE_MAP)
    .filter((r) => !r.includes(':'))
    .sort((a, b) => b.length - a.length);
  for (const route of sorted) {
    if (clean.startsWith(route + '/') || clean === route) {
      return _result(route, ROUTE_MODULE_MAP[route]);
    }
  }

  // 4. Default
  return _result(null, 'cockpit');
}

function _result(pattern, moduleId) {
  const mod = NAV_MODULES.find((m) => m.key === moduleId);
  return { moduleId, moduleLabel: mod?.label || moduleId, pattern };
}

/* ── Module definitions (Rail) ── */
export const NAV_MODULES = [
  { key: 'cockpit',    label: 'Cockpit',    icon: LayoutDashboard, tint: 'blue',    expertOnly: false, order: 1, desc: "Vue d'ensemble et alertes" },
  { key: 'operations', label: 'Opérations', icon: ListChecks,      tint: 'emerald', expertOnly: false, order: 2, desc: "Conformité et plans d'actions" },
  { key: 'analyse',    label: 'Analyse',    icon: Activity,        tint: 'indigo',  expertOnly: false, order: 3, desc: 'Consommations et performance' },
  { key: 'marche',     label: 'Marché',     icon: Receipt,         tint: 'amber',   expertOnly: true,  order: 4, desc: 'Factures et achats énergie' },
  { key: 'admin',      label: 'Admin',      icon: Database,        tint: 'slate',   expertOnly: true,  order: 5, desc: 'Données, connexions et IAM' },
];

/* ── Centralized Tint Palette (Color Life System) ──
 * One entry per tint color. Every surface class is a literal string
 * for Tailwind JIT scanning. Rule: 80% neutral / 15% tint / 5% accent.
 */
export const TINT_PALETTE = {
  blue: {
    headerBand:     'from-blue-50/60 to-transparent',
    panelHeader:    'from-blue-50/40 to-transparent',
    softBg:         'bg-blue-50/40',
    hoverBg:        'bg-blue-50/30',
    activeBg:       'bg-blue-50/60',
    activeText:     'text-blue-700',
    activeBorder:   'border-blue-500',
    railActiveBg:   'bg-blue-50/70',
    railActiveRing: 'ring-blue-300/50',
    railActiveText: 'text-blue-600',
    dot:            'bg-blue-400',
    icon:           'text-blue-500',
    pillBg:         'bg-blue-50',
    pillText:       'text-blue-700',
    pillRing:       'ring-blue-200/60',
  },
  emerald: {
    headerBand:     'from-emerald-50/50 to-transparent',
    panelHeader:    'from-emerald-50/30 to-transparent',
    softBg:         'bg-emerald-50/40',
    hoverBg:        'bg-emerald-50/30',
    activeBg:       'bg-emerald-50/60',
    activeText:     'text-emerald-700',
    activeBorder:   'border-emerald-500',
    railActiveBg:   'bg-emerald-50/70',
    railActiveRing: 'ring-emerald-300/50',
    railActiveText: 'text-emerald-600',
    dot:            'bg-emerald-400',
    icon:           'text-emerald-500',
    pillBg:         'bg-emerald-50',
    pillText:       'text-emerald-700',
    pillRing:       'ring-emerald-200/60',
  },
  indigo: {
    headerBand:     'from-indigo-50/50 to-transparent',
    panelHeader:    'from-indigo-50/30 to-transparent',
    softBg:         'bg-indigo-50/40',
    hoverBg:        'bg-indigo-50/30',
    activeBg:       'bg-indigo-50/60',
    activeText:     'text-indigo-700',
    activeBorder:   'border-indigo-500',
    railActiveBg:   'bg-indigo-50/70',
    railActiveRing: 'ring-indigo-300/50',
    railActiveText: 'text-indigo-600',
    dot:            'bg-indigo-400',
    icon:           'text-indigo-500',
    pillBg:         'bg-indigo-50',
    pillText:       'text-indigo-700',
    pillRing:       'ring-indigo-200/60',
  },
  amber: {
    headerBand:     'from-amber-50/50 to-transparent',
    panelHeader:    'from-amber-50/30 to-transparent',
    softBg:         'bg-amber-50/40',
    hoverBg:        'bg-amber-50/30',
    activeBg:       'bg-amber-50/60',
    activeText:     'text-amber-700',
    activeBorder:   'border-amber-500',
    railActiveBg:   'bg-amber-50/70',
    railActiveRing: 'ring-amber-300/50',
    railActiveText: 'text-amber-600',
    dot:            'bg-amber-400',
    icon:           'text-amber-500',
    pillBg:         'bg-amber-50',
    pillText:       'text-amber-700',
    pillRing:       'ring-amber-200/60',
  },
  slate: {
    headerBand:     'from-slate-100/50 to-transparent',
    panelHeader:    'from-slate-100/30 to-transparent',
    softBg:         'bg-slate-100/40',
    hoverBg:        'bg-slate-100/30',
    activeBg:       'bg-slate-100/60',
    activeText:     'text-slate-700',
    activeBorder:   'border-slate-500',
    railActiveBg:   'bg-slate-100/70',
    railActiveRing: 'ring-slate-300/50',
    railActiveText: 'text-slate-600',
    dot:            'bg-slate-400',
    icon:           'text-slate-500',
    pillBg:         'bg-slate-100',
    pillText:       'text-slate-700',
    pillRing:       'ring-slate-200/60',
  },
};

/* ── Module tint colors for header bands (derived from TINT_PALETTE) ── */
export const MODULE_TINTS = Object.fromEntries(
  NAV_MODULES.map((m) => [m.key, TINT_PALETTE[m.tint]?.headerBand || TINT_PALETTE.slate.headerBand])
);

/* ── Quick Actions (sidebar + CommandPalette) ── */
export const QUICK_ACTIONS = [
  { key: 'scan',   label: 'Scanner',        icon: ScanLine, to: '/conformite',      keywords: ['scan', 'evaluer'] },
  { key: 'import', label: 'Importer',       icon: Import,   to: '/patrimoine',       keywords: ['csv', 'upload'] },
  { key: 'action', label: 'Creer action',   icon: ListPlus, to: '/actions',          keywords: ['action', 'plan'] },
  { key: 'diag',   label: 'Lancer analyse', icon: Search,   to: '/diagnostic-conso', keywords: ['diagnostic', 'anomalies'] },
];

/* ── Section definitions (Panel content per module) ── */
export const NAV_SECTIONS = [
  {
    key: 'cockpit',
    module: 'cockpit',
    label: 'Piloter',
    expertOnly: false,
    order: 1,
    items: [
      { to: '/',              icon: LayoutDashboard, label: 'Tableau de bord', keywords: ['dashboard', 'accueil', 'home', 'tableau'] },
      { to: '/cockpit',       icon: FileText,        label: 'Vue exécutive', keywords: ['synthese', 'executive', 'brief'] },
      { to: '/notifications', icon: Bell,            label: 'Alertes', badgeKey: 'alerts', keywords: ['alertes', 'notifications'] },
    ],
  },
  {
    key: 'operations',
    module: 'operations',
    label: 'Exécuter',
    expertOnly: false,
    order: 2,
    items: [
      { to: '/conformite', icon: ShieldCheck, label: 'Conformité', keywords: ['compliance', 'reglementation', 'decret'] },
      { to: '/conformite/tertiaire', icon: Building2, label: 'Tertiaire / OPERAT', keywords: ['tertiaire', 'operat', 'efa', 'decret', 'declaration'] },
      { to: '/actions',    icon: ListChecks,  label: "Plan d'actions", keywords: ['actions', 'plan', 'todo'] },
      { to: '/anomalies',  icon: AlertTriangle, label: "Centre d'actions", keywords: ['anomalies', 'actions', 'centre', 'risque', 'priorite'] },
    ],
  },
  {
    key: 'analyse',
    module: 'analyse',
    label: 'Analyser',
    expertOnly: false,
    order: 3,
    items: [
      { to: '/consommations',    icon: Zap,       label: 'Consommations', keywords: ['conso', 'energie', 'import', 'explorer', 'ems', 'timeseries'] },
      { to: '/monitoring',       icon: Activity,  label: 'Performance', badgeKey: 'monitoring', keywords: ['monitoring', 'kpi', 'puissance'] },
      { to: '/diagnostic-conso', icon: Search,    label: 'Diagnostic', expertOnly: true, keywords: ['anomalies', 'diagnostic', 'analyse'] },
      { to: '/usages-horaires',  icon: Activity,  label: 'Usages & Horaires', expertOnly: true, keywords: ['usages', 'horaires', 'profil', 'heatmap', 'comportement'] },
    ],
  },
  {
    key: 'marche',
    module: 'marche',
    label: 'Marché & Factures',
    expertOnly: true,
    order: 4,
    items: [
      { to: '/bill-intel',      icon: Receipt,       label: 'Factures & anomalies', keywords: ['factures', 'billing', 'invoices', 'anomalies'] },
      { to: '/billing',         icon: CalendarRange,  label: 'Timeline & couverture', keywords: ['timeline', 'couverture', 'mois', 'manquant', 'periodes'], indent: true },
      { to: '/achat-energie',   icon: ShoppingCart,  label: 'Achats énergie', keywords: ['achat', 'purchase', 'scenarios', 'strategie'] },
      { to: '/achat-assistant', icon: Target,        label: 'Assistant Achat', keywords: ['assistant', 'wizard', 'rfp', 'arenh', 'corridor'] },
    ],
  },
  {
    key: 'donnees',
    module: 'admin',
    label: 'Donnees',
    expertOnly: true,
    order: 5,
    items: [
      { to: '/patrimoine',      icon: Building2,  label: 'Patrimoine', keywords: ['sites', 'batiments', 'immobilier'] },
      { to: '/payment-rules',  icon: BadgeEuro,  label: 'Paiement & Refacturation', keywords: ['paiement', 'payeur', 'facture', 'refacturation', 'cost center'] },
      { to: '/import',         icon: Import,     label: 'Imports', keywords: ['import', 'csv', 'upload'], hidden: true },
      { to: '/connectors',    icon: Link2,     label: 'Connexions', keywords: ['connecteurs', 'api', 'sync'] },
      { to: '/kb',            icon: BookOpen,  label: 'Mémobox', keywords: ['kb', 'knowledge', 'base', 'memobox', 'documents', 'preuves'] },
      { to: '/segmentation',  icon: Users,     label: 'Segmentation', keywords: ['segment', 'profil'] },
      { to: '/watchers',      icon: Eye,       label: 'Veille', keywords: ['veille', 'rss', 'reglementaire'] },
    ],
  },
  {
    key: 'iam',
    module: 'admin',
    label: 'Administration',
    expertOnly: true,
    order: 6,
    items: [
      { to: '/admin/users',       icon: Lock,        label: 'Utilisateurs', requireAdmin: true, expertOnly: true, keywords: ['users', 'comptes'] },
      { to: '/admin/roles',       icon: ShieldCheck, label: 'Rôles', requireAdmin: true, expertOnly: true, keywords: ['roles', 'permissions'] },
      { to: '/admin/assignments', icon: Users,       label: 'Affectations', requireAdmin: true, expertOnly: true, keywords: ['assignments', 'affectations', 'scopes'] },
      { to: '/admin/audit',       icon: FileText,    label: 'Journal d\'audit', requireAdmin: true, expertOnly: true, keywords: ['audit', 'log', 'historique'] },
    ],
  },
];

/* ── Helpers ── */

/** Get sections for a specific module */
export function getSectionsForModule(moduleKey) {
  return NAV_SECTIONS.filter((s) => s.module === moduleKey);
}

/** Resolve current module from pathname (delegates to matchRouteToModule) */
export function resolveModule(pathname) {
  return matchRouteToModule(pathname).moduleId;
}

// Flat list of all nav items (for CommandPalette search)
export const ALL_NAV_ITEMS = NAV_SECTIONS.flatMap((s) =>
  s.items.map((item) => ({ ...item, section: s.label, module: s.module }))
);

/* ── Section tints (section key → tint name from parent module) ── */
export const SECTION_TINTS = Object.fromEntries(
  NAV_SECTIONS.map((s) => [s.key, NAV_MODULES.find((m) => m.key === s.module)?.tint || 'slate'])
);

/* ── Sidebar item active-state classes per tint (derived from TINT_PALETTE) ── */
export const SIDEBAR_ITEM_TINTS = Object.fromEntries(
  Object.entries(TINT_PALETTE).map(([k, v]) => [k, {
    activeBg: v.activeBg,
    activeText: v.activeText,
    activeBorder: v.activeBorder,
    dot: v.dot,
  }])
);

/** Get full tint palette for a module key or pathname */
export function getModuleTint(keyOrPath) {
  // Direct module key
  const mod = NAV_MODULES.find((m) => m.key === keyOrPath);
  if (mod) return TINT_PALETTE[mod.tint] || TINT_PALETTE.slate;
  // Pathname → module → tint
  const moduleKey = resolveModule(keyOrPath);
  const resolved = NAV_MODULES.find((m) => m.key === moduleKey);
  return TINT_PALETTE[resolved?.tint || 'slate'] || TINT_PALETTE.slate;
}
