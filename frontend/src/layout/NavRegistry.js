/**
 * PROMEOS — Navigation Registry (Rail + Panel IA)
 * 5 modules stables, each with a rail icon + tint color:
 * Cockpit / Operations / Analyse / Marche / Donnees
 *
 * Normal mode: Cockpit + Operations + Analyse core (~8 visible items)
 * Expert mode: + Diagnostic + Marche + Donnees & Admin
 */
import {
  LayoutDashboard, Building2, ShieldCheck, FileText,
  Zap, ListChecks, Activity, Import, Users, Receipt,
  BookOpen, ShoppingCart, Search, Link2, Eye, Bell, Lock,
  Target, Database,
} from 'lucide-react';

/* ── Route → module mapping (for permission checks + auto-select) ── */
export const ROUTE_MODULE_MAP = {
  '/': 'cockpit',
  '/cockpit': 'cockpit',
  '/notifications': 'cockpit',
  '/conformite': 'operations',
  '/actions': 'operations',
  '/patrimoine': 'analyse',
  '/consommations': 'analyse',
  '/consommations/explorer': 'analyse',
  '/consommations/import': 'analyse',
  '/consommations/kb': 'analyse',
  '/diagnostic-conso': 'analyse',
  '/monitoring': 'analyse',
  '/bill-intel': 'marche',
  '/achat-energie': 'marche',
  '/achat-assistant': 'marche',
  '/import': 'donnees',
  '/connectors': 'donnees',
  '/segmentation': 'donnees',
  '/watchers': 'donnees',
  '/kb': 'donnees',
  '/admin/users': 'donnees',
  '/admin/roles': 'donnees',
  '/admin/assignments': 'donnees',
  '/admin/audit': 'donnees',
};

/* ── Module definitions (Rail) ── */
export const NAV_MODULES = [
  { key: 'cockpit',    label: 'Cockpit',    icon: LayoutDashboard, tint: 'blue',    expertOnly: false, order: 1 },
  { key: 'operations', label: 'Operations', icon: ListChecks,      tint: 'emerald', expertOnly: false, order: 2 },
  { key: 'analyse',    label: 'Analyse',    icon: Activity,        tint: 'indigo',  expertOnly: false, order: 3 },
  { key: 'marche',     label: 'Marche',     icon: Receipt,         tint: 'violet',  expertOnly: true,  order: 4 },
  { key: 'donnees',    label: 'Donnees',    icon: Database,        tint: 'slate',   expertOnly: true,  order: 5 },
];

/* ── Module tint colors for header bands ── */
export const MODULE_TINTS = {
  cockpit:    'from-blue-50/60 to-transparent',
  operations: 'from-emerald-50/35 to-transparent',
  analyse:    'from-indigo-50/50 to-transparent',
  marche:     'from-violet-50/40 to-transparent',
  donnees:    'from-slate-100/50 to-transparent',
};

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
      { to: '/patrimoine',       icon: Building2, label: 'Patrimoine', keywords: ['sites', 'batiments', 'immobilier'] },
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
    module: 'donnees',
    label: 'Donnees',
    expertOnly: true,
    order: 5,
    items: [
      { to: '/import',       icon: Import,   label: 'Imports', keywords: ['import', 'csv', 'upload'] },
      { to: '/connectors',   icon: Link2,    label: 'Connexions', keywords: ['connecteurs', 'api', 'sync'] },
      { to: '/kb',           icon: BookOpen, label: 'Knowledge Base', keywords: ['kb', 'knowledge', 'base'] },
      { to: '/segmentation', icon: Users,    label: 'Segmentation', keywords: ['segment', 'profil'] },
      { to: '/watchers',     icon: Eye,      label: 'Veille', keywords: ['veille', 'rss', 'reglementaire'] },
    ],
  },
  {
    key: 'admin',
    module: 'donnees',
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
