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
  Zap, ListChecks, Activity, Import, Users, Receipt,
  BookOpen, ShoppingCart, Search, Link2, Eye, Bell, Lock,
  Target, Database, ScanLine, ListPlus,
} from 'lucide-react';

/* ── Route → module mapping (for permission checks + auto-select) ── */
export const ROUTE_MODULE_MAP = {
  '/': 'cockpit',
  '/cockpit': 'cockpit',
  '/notifications': 'cockpit',
  '/conformite': 'operations',
  '/actions': 'operations',
  '/consommations': 'analyse',
  '/consommations/explorer': 'analyse',
  '/consommations/import': 'analyse',
  '/consommations/kb': 'analyse',
  '/diagnostic-conso': 'analyse',
  '/monitoring': 'analyse',
  '/bill-intel': 'marche',
  '/achat-energie': 'marche',
  '/achat-assistant': 'marche',
  '/patrimoine': 'admin',
  '/import': 'admin',
  '/connectors': 'admin',
  '/segmentation': 'admin',
  '/watchers': 'admin',
  '/kb': 'admin',
  '/admin/users': 'admin',
  '/admin/roles': 'admin',
  '/admin/assignments': 'admin',
  '/admin/audit': 'admin',
};

/* ── Module definitions (Rail) ── */
export const NAV_MODULES = [
  { key: 'cockpit',    label: 'Cockpit',    icon: LayoutDashboard, tint: 'blue',    expertOnly: false, order: 1, desc: "Vue d'ensemble et alertes" },
  { key: 'operations', label: 'Operations', icon: ListChecks,      tint: 'emerald', expertOnly: false, order: 2, desc: "Conformite et plans d'actions" },
  { key: 'analyse',    label: 'Analyse',    icon: Activity,        tint: 'indigo',  expertOnly: false, order: 3, desc: 'Consommations et performance' },
  { key: 'marche',     label: 'Marche',     icon: Receipt,         tint: 'violet',  expertOnly: true,  order: 4, desc: 'Factures et achats energie' },
  { key: 'admin',      label: 'Admin',      icon: Database,        tint: 'slate',   expertOnly: true,  order: 5, desc: 'Donnees, connexions et IAM' },
];

/* ── Module tint colors for header bands ── */
export const MODULE_TINTS = {
  cockpit:    'from-blue-50/60 to-transparent',
  operations: 'from-emerald-50/35 to-transparent',
  analyse:    'from-indigo-50/50 to-transparent',
  marche:     'from-violet-50/40 to-transparent',
  admin:      'from-slate-100/50 to-transparent',
};

/* ── Quick Actions (sidebar + CommandPalette) ── */
export const QUICK_ACTIONS = [
  { key: 'scan',   label: 'Scanner',        icon: ScanLine, to: '/conformite',      keywords: ['scan', 'evaluer'] },
  { key: 'import', label: 'Importer',       icon: Import,   to: '/import',           keywords: ['csv', 'upload'] },
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
      { to: '/cockpit',       icon: FileText,        label: 'Vue executive', keywords: ['synthese', 'executive', 'brief'] },
      { to: '/notifications', icon: Bell,            label: 'Alertes', badgeKey: 'alerts', keywords: ['alertes', 'notifications'] },
    ],
  },
  {
    key: 'operations',
    module: 'operations',
    label: 'Executer',
    expertOnly: false,
    order: 2,
    items: [
      { to: '/conformite', icon: ShieldCheck, label: 'Conformite', keywords: ['compliance', 'reglementation', 'decret'] },
      { to: '/actions',    icon: ListChecks,  label: "Plan d'actions", keywords: ['actions', 'plan', 'todo'] },
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
    ],
  },
  {
    key: 'marche',
    module: 'marche',
    label: 'Marche & Factures',
    expertOnly: true,
    order: 4,
    items: [
      { to: '/bill-intel',      icon: Receipt,      label: 'Facturation', keywords: ['factures', 'billing', 'invoices'] },
      { to: '/achat-energie',   icon: ShoppingCart,  label: 'Achats energie', keywords: ['achat', 'purchase', 'scenarios', 'strategie'] },
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
      { to: '/patrimoine',    icon: Building2, label: 'Patrimoine', keywords: ['sites', 'batiments', 'immobilier'] },
      { to: '/import',        icon: Import,    label: 'Imports', keywords: ['import', 'csv', 'upload'] },
      { to: '/connectors',    icon: Link2,     label: 'Connexions', keywords: ['connecteurs', 'api', 'sync'] },
      { to: '/kb',            icon: BookOpen,  label: 'Knowledge Base', keywords: ['kb', 'knowledge', 'base'] },
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
      { to: '/admin/roles',       icon: ShieldCheck, label: 'Roles', requireAdmin: true, expertOnly: true, keywords: ['roles', 'permissions'] },
      { to: '/admin/assignments', icon: Users,       label: 'Assignments', requireAdmin: true, expertOnly: true, keywords: ['assignments', 'scopes'] },
      { to: '/admin/audit',       icon: FileText,    label: 'Audit Log', requireAdmin: true, expertOnly: true, keywords: ['audit', 'log', 'historique'] },
    ],
  },
];

/* ── Helpers ── */

/** Get sections for a specific module */
export function getSectionsForModule(moduleKey) {
  return NAV_SECTIONS.filter((s) => s.module === moduleKey);
}

/** Resolve current module from pathname */
export function resolveModule(pathname) {
  // Exact match first
  if (ROUTE_MODULE_MAP[pathname]) return ROUTE_MODULE_MAP[pathname];
  // Prefix match (e.g. /consommations/explorer → analyse)
  const sorted = Object.keys(ROUTE_MODULE_MAP).sort((a, b) => b.length - a.length);
  for (const route of sorted) {
    if (pathname.startsWith(route + '/') || pathname === route) {
      return ROUTE_MODULE_MAP[route];
    }
  }
  return 'cockpit';
}

// Flat list of all nav items (for CommandPalette search)
export const ALL_NAV_ITEMS = NAV_SECTIONS.flatMap((s) =>
  s.items.map((item) => ({ ...item, section: s.label, module: s.module }))
);

/* ── Section tints (section key → tint name from parent module) ── */
export const SECTION_TINTS = Object.fromEntries(
  NAV_SECTIONS.map((s) => [s.key, NAV_MODULES.find((m) => m.key === s.module)?.tint || 'slate'])
);

/* ── Sidebar item active-state classes per tint ── */
export const SIDEBAR_ITEM_TINTS = {
  blue:    { activeBg: 'bg-blue-50/60',    activeText: 'text-blue-600',    activeBorder: 'border-blue-600',    dot: 'bg-blue-400' },
  emerald: { activeBg: 'bg-emerald-50/60', activeText: 'text-emerald-600', activeBorder: 'border-emerald-600', dot: 'bg-emerald-400' },
  indigo:  { activeBg: 'bg-indigo-50/60',  activeText: 'text-indigo-600',  activeBorder: 'border-indigo-600',  dot: 'bg-indigo-400' },
  violet:  { activeBg: 'bg-violet-50/60',  activeText: 'text-violet-600',  activeBorder: 'border-violet-600',  dot: 'bg-violet-400' },
  slate:   { activeBg: 'bg-slate-100/60',  activeText: 'text-slate-700',   activeBorder: 'border-slate-600',   dot: 'bg-slate-400' },
};
