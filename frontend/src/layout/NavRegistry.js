/**
 * PROMEOS — Navigation Registry (Rail + Panel Architecture)
 * 5 modules stables, each with a tint color:
 * Cockpit / Operations / Analyse / Marche / Admin
 *
 * Normal mode: Cockpit + Operations + Analyse core (~7 visible items)
 * Expert mode: + Diagnostic + Marche + Admin (Donnees & IAM)
 */
import {
  LayoutDashboard,
  Building2,
  ShieldCheck,
  FileText,
  Zap,
  ListChecks,
  Activity,
  Import,
  Users,
  Receipt,
  CalendarRange,
  BookOpen,
  ShoppingCart,
  Search,
  Link2,
  Eye,
  Lock,
  Target,
  Database,
  ScanLine,
  AlertTriangle,
  Sparkles,
  Rocket,
  Settings,
  Bell,
  Clipboard,
  Download,
  HelpCircle,
  ToggleRight,
  MapPin,
  TrendingUp,
  Calculator,
  Upload,
  BarChart3,
} from 'lucide-react';

/* ── Route → module mapping (for permission checks + auto-select) ──
 * Static routes (exact match) + dynamic patterns (:param segments).
 * Dynamic patterns are matched by matchRouteToModule() with "best match wins".
 */
export const ROUTE_MODULE_MAP = {
  '/': 'pilotage',
  '/cockpit': 'pilotage',
  '/notifications': 'pilotage',
  '/actions': 'pilotage',
  '/actions/new': 'pilotage',
  '/actions/:actionId': 'pilotage',
  '/anomalies': 'pilotage',
  '/onboarding': 'pilotage',
  '/patrimoine': 'patrimoine',
  '/sites/:id': 'patrimoine',
  '/conformite': 'patrimoine',
  '/conformite/tertiaire': 'patrimoine',
  '/conformite/tertiaire/wizard': 'patrimoine',
  '/conformite/tertiaire/anomalies': 'patrimoine',
  '/conformite/tertiaire/efa/:id': 'patrimoine',
  '/compliance': 'patrimoine',
  '/compliance/pipeline': 'patrimoine',
  '/compliance/findings': 'patrimoine',
  '/compliance/obligations': 'patrimoine',
  '/compliance/sites/:siteId': 'patrimoine',
  '/consommations': 'energie',
  '/consommations/explorer': 'energie',
  '/consommations/import': 'energie',
  '/consommations/kb': 'energie',
  '/consommations/portfolio': 'energie',
  '/diagnostic-conso': 'energie',
  '/usages-horaires': 'energie',
  '/monitoring': 'energie',
  '/billing': 'energie',
  '/bill-intel': 'energie',
  '/payment-rules': 'energie',
  '/portfolio-reconciliation': 'energie',
  '/achat-energie': 'achat',
  '/achat-assistant': 'achat',
  '/renouvellements': 'achat',
  '/contracts-radar': 'achat',
  '/market': 'achat',
  '/import': 'admin',
  '/connectors': 'admin',
  '/segmentation': 'admin',
  '/watchers': 'admin',
  '/kb': 'admin',
  '/admin/users': 'admin',
  '/admin/roles': 'admin',
  '/admin/assignments': 'admin',
  '/admin/audit': 'admin',
  '/activation': 'admin',
  '/status': 'admin',
  '/energy-copilot': 'pilotage',
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

/* ── Module definitions (Rail — 5 sections) ── */
export const NAV_MODULES = [
  {
    key: 'pilotage',
    label: 'Pilotage',
    icon: LayoutDashboard,
    tint: 'blue',
    expertOnly: false,
    order: 1,
    desc: 'Vue exécutive et actions',
  },
  {
    key: 'patrimoine',
    label: 'Patrimoine',
    icon: Building2,
    tint: 'emerald',
    expertOnly: false,
    order: 2,
    desc: 'Sites, bâtiments et conformité',
  },
  {
    key: 'energie',
    label: 'Énergie',
    icon: Zap,
    tint: 'indigo',
    expertOnly: false,
    order: 3,
    desc: 'Consommations, performance et facturation',
  },
  {
    key: 'achat',
    label: 'Achat',
    icon: ShoppingCart,
    tint: 'amber',
    expertOnly: false,
    order: 4,
    desc: "Stratégies d'achat énergie",
  },
  {
    key: 'admin',
    label: 'Administration',
    icon: Settings,
    tint: 'slate',
    expertOnly: true,
    order: 5,
    desc: 'Import, utilisateurs et système',
  },
];

/* ── Centralized Tint Palette (Color Life System) ──
 * One entry per tint color. Every surface class is a literal string
 * for Tailwind JIT scanning. Rule: 80% neutral / 15% tint / 5% accent.
 */
export const TINT_PALETTE = {
  blue: {
    headerBand: 'from-blue-50/60 to-transparent',
    panelHeader: 'from-blue-50/40 to-transparent',
    softBg: 'bg-blue-50/40',
    hoverBg: 'bg-blue-50/30',
    activeBg: 'bg-blue-50/60',
    activeText: 'text-blue-700',
    activeBorder: 'border-blue-500',
    railActiveBg: 'bg-blue-50/70',
    railActiveRing: 'ring-blue-300/50',
    railActiveText: 'text-blue-600',
    dot: 'bg-blue-400',
    icon: 'text-blue-500',
    pillBg: 'bg-blue-50',
    pillText: 'text-blue-700',
    pillRing: 'ring-blue-200/60',
  },
  emerald: {
    headerBand: 'from-emerald-50/50 to-transparent',
    panelHeader: 'from-emerald-50/30 to-transparent',
    softBg: 'bg-emerald-50/40',
    hoverBg: 'bg-emerald-50/30',
    activeBg: 'bg-emerald-50/60',
    activeText: 'text-emerald-700',
    activeBorder: 'border-emerald-500',
    railActiveBg: 'bg-emerald-50/70',
    railActiveRing: 'ring-emerald-300/50',
    railActiveText: 'text-emerald-600',
    dot: 'bg-emerald-400',
    icon: 'text-emerald-500',
    pillBg: 'bg-emerald-50',
    pillText: 'text-emerald-700',
    pillRing: 'ring-emerald-200/60',
  },
  indigo: {
    headerBand: 'from-indigo-50/50 to-transparent',
    panelHeader: 'from-indigo-50/30 to-transparent',
    softBg: 'bg-indigo-50/40',
    hoverBg: 'bg-indigo-50/30',
    activeBg: 'bg-indigo-50/60',
    activeText: 'text-indigo-700',
    activeBorder: 'border-indigo-500',
    railActiveBg: 'bg-indigo-50/70',
    railActiveRing: 'ring-indigo-300/50',
    railActiveText: 'text-indigo-600',
    dot: 'bg-indigo-400',
    icon: 'text-indigo-500',
    pillBg: 'bg-indigo-50',
    pillText: 'text-indigo-700',
    pillRing: 'ring-indigo-200/60',
  },
  amber: {
    headerBand: 'from-amber-50/50 to-transparent',
    panelHeader: 'from-amber-50/30 to-transparent',
    softBg: 'bg-amber-50/40',
    hoverBg: 'bg-amber-50/30',
    activeBg: 'bg-amber-50/60',
    activeText: 'text-amber-700',
    activeBorder: 'border-amber-500',
    railActiveBg: 'bg-amber-50/70',
    railActiveRing: 'ring-amber-300/50',
    railActiveText: 'text-amber-600',
    dot: 'bg-amber-400',
    icon: 'text-amber-500',
    pillBg: 'bg-amber-50',
    pillText: 'text-amber-700',
    pillRing: 'ring-amber-200/60',
  },
  slate: {
    headerBand: 'from-slate-100/50 to-transparent',
    panelHeader: 'from-slate-100/30 to-transparent',
    softBg: 'bg-slate-100/40',
    hoverBg: 'bg-slate-100/30',
    activeBg: 'bg-slate-100/60',
    activeText: 'text-slate-700',
    activeBorder: 'border-slate-500',
    railActiveBg: 'bg-slate-100/70',
    railActiveRing: 'ring-slate-300/50',
    railActiveText: 'text-slate-600',
    dot: 'bg-slate-400',
    icon: 'text-slate-500',
    pillBg: 'bg-slate-100',
    pillText: 'text-slate-700',
    pillRing: 'ring-slate-200/60',
  },
};

/* ── Module tint colors for header bands (derived from TINT_PALETTE) ── */
export const MODULE_TINTS = Object.fromEntries(
  NAV_MODULES.map((m) => [m.key, TINT_PALETTE[m.tint]?.headerBand || TINT_PALETTE.slate.headerBand])
);

/* ── Quick Actions (sidebar + CommandPalette) ── */
export const QUICK_ACTIONS = [
  {
    key: 'scan',
    label: 'Scanner',
    icon: ScanLine,
    to: '/conformite',
    keywords: ['scan', 'evaluer'],
  },
  {
    key: 'import',
    label: 'Importer',
    icon: Import,
    to: '/import',
    keywords: ['csv', 'upload'],
  },
  {
    key: 'centre',
    label: "Centre d'actions",
    icon: AlertTriangle,
    to: '/anomalies',
    keywords: ['anomalies', 'actions', 'inbox', 'plan'],
  },
  {
    key: 'diag',
    label: 'Lancer analyse',
    icon: Search,
    to: '/diagnostic-conso',
    keywords: ['diagnostic', 'anomalies'],
  },
  {
    key: 'dq',
    label: 'Qualité données',
    icon: Database,
    to: '/conformite?tab=donnees',
    keywords: ['qualite', 'donnees', 'data', 'quality', 'couverture'],
  },
  {
    key: 'copilot',
    label: 'Actions Copilot',
    icon: Sparkles,
    to: '/anomalies?tab=actions&source=copilot',
    keywords: ['copilot', 'ia', 'intelligence', 'recommandations'],
  },
  {
    key: 'achats',
    label: 'Achats',
    longLabel: "Achats d'énergie & scénarios",
    icon: ShoppingCart,
    to: '/achat-energie',
    keywords: ['achat', 'purchase', 'marche', 'contrat'],
  },
  {
    key: 'onboarding',
    label: 'Onboarding',
    icon: Rocket,
    to: '/onboarding',
    keywords: ['onboarding', 'demarrage', 'setup', 'configuration'],
  },
  {
    key: 'operat',
    label: 'Export OPERAT',
    icon: Building2,
    to: '/conformite/tertiaire',
    keywords: ['operat', 'export', 'tertiaire', 'décret'],
  },
  {
    key: 'preuves',
    label: 'Preuves manquantes',
    icon: FileText,
    to: '/conformite?tab=preuves',
    keywords: ['preuves', 'manquantes', 'justificatifs', 'upload'],
  },
  {
    key: 'factures',
    label: 'Anomalies',
    longLabel: 'Anomalies de facturation',
    icon: Receipt,
    to: '/bill-intel',
    keywords: ['facture', 'anomalie', 'surfacturation', 'billing', 'anomalies'],
  },
  {
    key: 'corriger',
    label: 'Corriger données',
    icon: Database,
    to: '/conformite?tab=donnees',
    keywords: ['corriger', 'données', 'manquantes', 'qualité'],
  },
  {
    key: 'audit',
    label: "Journal d'audit",
    icon: FileText,
    to: '/admin/audit',
    keywords: ['audit', 'log', 'historique', 'journal'],
  },
  {
    key: 'creer-action',
    label: 'Créer une action',
    icon: Target,
    to: '/actions/new',
    keywords: ['créer', 'action', 'nouvelle', 'tâche'],
  },
];

/* ── Section definitions (Panel content per module) ── */
export const NAV_SECTIONS = [
  {
    key: 'pilotage',
    module: 'pilotage',
    label: 'Pilotage',
    expertOnly: false,
    order: 1,
    items: [
      { to: '/cockpit', icon: BarChart3, label: 'Cockpit', keywords: ['cockpit', 'executive', 'synthese', 'dashboard'] },
      { to: '/actions', icon: AlertTriangle, label: "Centre d'actions", badgeKey: 'alerts', keywords: ['anomalies', 'actions', 'inbox', 'plan', 'todo'] },
      { to: '/notifications', icon: Bell, label: 'Notifications', badgeKey: 'notif_count', keywords: ['alertes', 'notifications'] },
    ],
  },
  {
    key: 'patrimoine',
    module: 'patrimoine',
    label: 'Patrimoine',
    expertOnly: false,
    order: 2,
    items: [
      { to: '/patrimoine', icon: MapPin, label: 'Sites & Bâtiments', keywords: ['sites', 'batiments', 'immobilier', 'patrimoine'] },
      { to: '/conformite', icon: ShieldCheck, label: 'Conformité', keywords: ['compliance', 'reglementation', 'decret', 'tertiaire', 'operat'] },
    ],
  },
  {
    key: 'energie',
    module: 'energie',
    label: 'Énergie',
    expertOnly: false,
    order: 3,
    items: [
      { to: '/consommations', icon: Activity, label: 'Consommations', keywords: ['conso', 'energie', 'explorer', 'diagnostic', 'usages'] },
      { to: '/monitoring', icon: TrendingUp, label: 'Performance', badgeKey: 'monitoring', keywords: ['monitoring', 'kpi', 'puissance', 'performance'] },
      { to: '/billing', icon: Receipt, label: 'Facturation', keywords: ['factures', 'billing', 'anomalies', 'surfacturation', 'historique'] },
    ],
  },
  {
    key: 'achat',
    module: 'achat',
    label: 'Achat',
    expertOnly: false,
    order: 4,
    items: [
      { to: '/achat-energie', icon: Calculator, label: "Stratégies d'achat", keywords: ['achat', 'purchase', 'scenarios', 'strategie', 'assistant', 'renouvellements'] },
    ],
  },
  {
    key: 'admin-data',
    module: 'admin',
    label: 'Données',
    expertOnly: true,
    order: 5,
    items: [
      { to: '/import', icon: Upload, label: 'Import données', keywords: ['import', 'csv', 'upload'] },
      { to: '/admin/users', icon: Users, label: 'Utilisateurs', requireAdmin: true, keywords: ['users', 'comptes'] },
      { to: '/watchers', icon: Eye, label: 'Veille réglementaire', keywords: ['veille', 'rss', 'reglementaire'] },
      { to: '/status', icon: Settings, label: 'Système', keywords: ['status', 'health', 'connecteurs', 'kb', 'segmentation'] },
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
  Object.entries(TINT_PALETTE).map(([k, v]) => [
    k,
    {
      activeBg: v.activeBg,
      activeText: v.activeText,
      activeBorder: v.activeBorder,
      dot: v.dot,
    },
  ])
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

/* ══════════════════════════════════════════════════════════════════
 * B.2 — 5 Sections principales (sidebar collapsible)
 * Regroupement métier des pages en 5 sections visibles.
 * Admin/IAM dans un menu secondaire (engrenage).
 * ══════════════════════════════════════════════════════════════════ */

export const NAV_MAIN_SECTIONS = [
  {
    key: 'pilotage',
    label: 'Pilotage',
    icon: LayoutDashboard,
    tint: 'blue',
    order: 1,
    items: [
      { to: '/cockpit', icon: BarChart3, label: 'Cockpit', keywords: ['cockpit', 'executive', 'synthese', 'dashboard', 'accueil'] },
      { to: '/actions', icon: AlertTriangle, label: "Centre d'actions", badgeKey: 'alerts', keywords: ['anomalies', 'actions', 'inbox', 'plan', 'todo'] },
      { to: '/notifications', icon: Bell, label: 'Notifications', badgeKey: 'notif_count', keywords: ['alertes', 'notifications'] },
    ],
  },
  {
    key: 'patrimoine',
    label: 'Patrimoine',
    icon: Building2,
    tint: 'emerald',
    order: 2,
    items: [
      { to: '/patrimoine', icon: MapPin, label: 'Sites & Bâtiments', keywords: ['sites', 'batiments', 'immobilier', 'patrimoine'] },
      { to: '/conformite', icon: ShieldCheck, label: 'Conformité', keywords: ['compliance', 'reglementation', 'decret', 'tertiaire', 'operat', 'obligations'] },
    ],
  },
  {
    key: 'energie',
    label: 'Énergie',
    icon: Zap,
    tint: 'indigo',
    order: 3,
    items: [
      { to: '/consommations', icon: Activity, label: 'Consommations', keywords: ['conso', 'energie', 'explorer', 'diagnostic', 'usages', 'horaires'] },
      { to: '/monitoring', icon: TrendingUp, label: 'Performance', badgeKey: 'monitoring', keywords: ['monitoring', 'kpi', 'puissance', 'performance', 'heatmap'] },
      { to: '/billing', icon: Receipt, label: 'Facturation', keywords: ['factures', 'billing', 'anomalies', 'surfacturation', 'historique', 'audit', 'import'] },
    ],
  },
  {
    key: 'achat',
    label: 'Achat',
    icon: ShoppingCart,
    tint: 'amber',
    order: 4,
    items: [
      { to: '/achat-energie', icon: Calculator, label: "Stratégies d'achat", keywords: ['achat', 'purchase', 'scenarios', 'strategie', 'assistant', 'renouvellements', 'contrats'] },
    ],
  },
];

/** Items du menu secondaire (engrenage) — Administration */
export const NAV_ADMIN_ITEMS = [
  { to: '/import', icon: Upload, label: 'Import données', keywords: ['import', 'csv', 'upload'] },
  { to: '/admin/users', icon: Users, label: 'Utilisateurs', requireAdmin: true, keywords: ['users', 'comptes'] },
  { to: '/watchers', icon: Eye, label: 'Veille réglementaire', keywords: ['veille', 'rss', 'reglementaire'] },
  { to: '/status', icon: Settings, label: 'Système', keywords: ['status', 'health', 'connecteurs', 'segmentation', 'kb'] },
];

/** Icon for the admin secondary menu */
export const NAV_ADMIN_ICON = Settings;

/** Route → section label map (for breadcrumb) */
export const ROUTE_SECTION_MAP = Object.fromEntries(
  NAV_MAIN_SECTIONS.flatMap((section) =>
    section.items.map((item) => [item.to, section.label])
  )
);

/** Pages retirées du menu mais trouvables via CommandPalette (Ctrl+K) */
export const HIDDEN_PAGES = [
  { to: '/kb', icon: BookOpen, label: 'Mémobox / Base de connaissances', keywords: ['kb', 'knowledge', 'memobox', 'documents'], section: 'Autres', hidden: true },
  { to: '/segmentation', icon: Users, label: 'Segmentation', keywords: ['segment', 'profil'], section: 'Autres', hidden: true },
  { to: '/connectors', icon: Link2, label: 'Connecteurs', keywords: ['connecteurs', 'api', 'sync'], section: 'Autres', hidden: true },
  { to: '/achat-assistant', icon: Target, label: "Assistant d'achat", keywords: ['assistant', 'wizard', 'rfp', 'corridor', 'achat'], section: 'Achat', hidden: true },
  { to: '/diagnostic-conso', icon: Search, label: 'Diagnostic consommation', keywords: ['diagnostic', 'anomalies', 'analyse'], section: 'Énergie', hidden: true },
  { to: '/usages-horaires', icon: Activity, label: 'Usages & Horaires', keywords: ['usages', 'horaires', 'profil', 'heatmap', 'comportement'], section: 'Énergie', hidden: true },
  { to: '/bill-intel', icon: Receipt, label: 'Anomalies factures', keywords: ['factures', 'billing', 'surfacturation', 'anomalies'], section: 'Énergie', hidden: true },
  { to: '/renouvellements', icon: CalendarRange, label: 'Renouvellements contrats', keywords: ['renouvellements', 'contrats', 'echeances', 'radar'], section: 'Achat', hidden: true },
  { to: '/conformite/tertiaire', icon: Building2, label: 'Tertiaire / OPERAT', keywords: ['tertiaire', 'operat', 'efa', 'décret'], section: 'Patrimoine', hidden: true },
  { to: '/energy-copilot', icon: Sparkles, label: 'Copilot énergie', keywords: ['copilot', 'ia', 'recommandations'], section: 'Pilotage', hidden: true },
  { to: '/compliance/pipeline', icon: ListChecks, label: 'Pipeline conformité', keywords: ['pipeline', 'findings'], section: 'Patrimoine', hidden: true },
  { to: '/', icon: LayoutDashboard, label: 'Tableau de bord', keywords: ['dashboard', 'accueil', 'home'], section: 'Pilotage', hidden: true },
  { to: '/anomalies', icon: AlertTriangle, label: "Centre d'actions (anomalies)", keywords: ['anomalies', 'inbox'], section: 'Pilotage', hidden: true },
];

/** Flat list of all main section items + hidden pages (for CommandPalette) */
export const ALL_MAIN_ITEMS = [
  ...NAV_MAIN_SECTIONS.flatMap((s) =>
    s.items.map((item) => ({ ...item, section: s.label, sectionKey: s.key }))
  ),
  ...HIDDEN_PAGES,
];

/** 10 actions rapides pour CommandPalette avec raccourcis visuels */
export const COMMAND_SHORTCUTS = [
  { key: 'creer-action', label: 'Créer une action', icon: Target, to: '/actions/new', shortcut: 'Ctrl+Shift+A', keywords: ['créer', 'action', 'nouvelle'] },
  { key: 'importer', label: 'Importer des données', icon: Import, to: '/import', shortcut: 'Ctrl+Shift+I', keywords: ['import', 'csv', 'upload', 'données'] },
  { key: 'alertes', label: 'Voir les alertes', icon: AlertTriangle, to: '/anomalies', shortcut: 'Ctrl+Shift+L', keywords: ['alertes', 'anomalies', 'actions'] },
  { key: 'cockpit', label: 'Aller au cockpit', icon: LayoutDashboard, to: '/cockpit', shortcut: 'Ctrl+Shift+C', keywords: ['cockpit', 'executive', 'synthese'] },
  { key: 'changer-site', label: 'Changer de site', icon: Building2, to: '/patrimoine', shortcut: 'Ctrl+Shift+S', keywords: ['site', 'patrimoine', 'changer'] },
  { key: 'exporter', label: 'Exporter CSV', icon: Download, to: '/consommations/export', shortcut: 'Ctrl+Shift+E', keywords: ['export', 'csv', 'télécharger'] },
  { key: 'conformite', label: 'Voir la conformité', icon: ShieldCheck, to: '/conformite', shortcut: 'Ctrl+Shift+F', keywords: ['conformité', 'compliance', 'décret'] },
  { key: 'factures', label: 'Voir les factures', icon: Receipt, to: '/bill-intel', shortcut: 'Ctrl+Shift+B', keywords: ['factures', 'billing', 'anomalies'] },
  { key: 'expert', label: 'Mode expert', icon: ToggleRight, to: '#expert-toggle', shortcut: 'Ctrl+Shift+X', keywords: ['expert', 'mode', 'pro', 'avancé'] },
  { key: 'aide', label: 'Aide', icon: HelpCircle, to: '/onboarding', shortcut: 'F1', keywords: ['aide', 'help', 'documentation', 'onboarding'] },
];
