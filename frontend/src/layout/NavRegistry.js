/**
 * PROMEOS — Navigation Registry (Phase 6.1 - IA v4)
 * Jobs-to-be-done sections with progressive disclosure via ExpertMode.
 * Normal: Cockpit + Operations + Analyse core (~8 visible items)
 * Expert: + Diagnostic + Marche + Donnees & Admin
 */
import {
  LayoutDashboard, Building2, ShieldCheck, FileText,
  Zap, ListChecks, Activity, Import, Users, Receipt,
  BookOpen, ShoppingCart, Search, Link2, Eye, Bell, Lock,
  Target,
} from 'lucide-react';

export const ROUTE_MODULE_MAP = {
  '/': 'cockpit',
  '/cockpit': 'cockpit',
  '/notifications': 'cockpit',
  '/conformite': 'conformite',
  '/actions': 'actions',
  '/patrimoine': 'patrimoine',
  '/consommations': 'consommations',
  '/consommations/explorer': 'consommations',
  '/consommations/import': 'consommations',
  '/consommations/kb': 'consommations',
  '/diagnostic-conso': 'diagnostic',
  '/bill-intel': 'billing',
  '/achat-energie': 'purchase',
  '/achat-assistant': 'purchase',
  '/monitoring': 'monitoring',
  '/import': null,
  '/connectors': null,
  '/segmentation': null,
  '/watchers': null,
  '/kb': null,
  '/admin/users': null,
  '/admin/roles': null,
  '/admin/assignments': null,
  '/admin/audit': null,
};

export const NAV_SECTIONS = [
  {
    label: 'Cockpit',
    expertOnly: false,
    collapsible: false,
    order: 1,
    items: [
      { to: '/',        icon: LayoutDashboard, label: 'Dashboard', keywords: ['dashboard', 'accueil', 'home', 'tableau'] },
      { to: '/cockpit', icon: FileText,        label: 'Vue executive', keywords: ['synthese', 'executive', 'brief'] },
    ],
  },
  {
    label: 'Operations',
    expertOnly: false,
    collapsible: false,
    order: 2,
    items: [
      { to: '/actions',       icon: ListChecks,  label: "Plan d'actions", keywords: ['actions', 'plan', 'todo'] },
      { to: '/notifications', icon: Bell,         label: 'Alertes', badgeKey: 'alerts', keywords: ['alertes', 'notifications'] },
      { to: '/conformite',    icon: ShieldCheck,  label: 'Conformite', keywords: ['compliance', 'reglementation', 'decret'] },
    ],
  },
  {
    label: 'Analyse',
    expertOnly: false,
    collapsible: true,
    defaultCollapsed: false,
    order: 3,
    items: [
      { to: '/consommations',    icon: Zap,      label: 'Consommations', keywords: ['conso', 'energie', 'import', 'explorer', 'ems', 'timeseries'] },
      { to: '/monitoring',       icon: Activity, label: 'Performance', badgeKey: 'monitoring', keywords: ['monitoring', 'kpi', 'puissance'] },
      { to: '/diagnostic-conso', icon: Search,   label: 'Diagnostic', expertOnly: true, keywords: ['anomalies', 'diagnostic', 'analyse'] },
    ],
  },
  {
    label: 'Marche',
    expertOnly: true,
    collapsible: true,
    defaultCollapsed: true,
    order: 4,
    items: [
      { to: '/bill-intel',      icon: Receipt,      label: 'Facturation', keywords: ['factures', 'billing', 'invoices'] },
      { to: '/achat-energie',   icon: ShoppingCart,  label: "Strategie d'achat", keywords: ['achat', 'purchase', 'scenarios', 'strategie'] },
      { to: '/achat-assistant', icon: Target,        label: 'Assistant Achat', keywords: ['assistant', 'wizard', 'rfp', 'arenh', 'corridor'] },
    ],
  },
  {
    label: 'Donnees & Admin',
    expertOnly: true,
    collapsible: true,
    defaultCollapsed: true,
    order: 5,
    items: [
      { to: '/patrimoine',          icon: Building2,   label: 'Patrimoine', keywords: ['sites', 'batiments', 'immobilier'] },
      { to: '/import',              icon: Import,      label: 'Imports', keywords: ['import', 'csv', 'upload'] },
      { to: '/connectors',          icon: Link2,       label: 'Connexions', keywords: ['connecteurs', 'api', 'sync'] },
      { to: '/segmentation',        icon: Users,       label: 'Segmentation', keywords: ['segment', 'profil'] },
      { to: '/kb',                  icon: BookOpen,    label: 'Referentiels', keywords: ['kb', 'knowledge', 'base'] },
      { to: '/admin/users',         icon: Lock,        label: 'Utilisateurs', requireAdmin: true, keywords: ['users', 'comptes'] },
      { to: '/admin/roles',         icon: ShieldCheck, label: 'Roles', requireAdmin: true, keywords: ['roles', 'permissions'] },
      { to: '/admin/assignments',   icon: Users,       label: 'Assignments', requireAdmin: true, keywords: ['assignments', 'scopes'] },
      { to: '/admin/audit',         icon: FileText,    label: 'Audit Log', requireAdmin: true, keywords: ['audit', 'log', 'historique'] },
    ],
  },
];

// Flat list of all nav items (for CommandPalette search)
export const ALL_NAV_ITEMS = NAV_SECTIONS.flatMap((s) =>
  s.items.map((item) => ({ ...item, section: s.label }))
);
