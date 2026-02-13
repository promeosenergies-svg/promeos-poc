/**
 * PROMEOS — Navigation Registry
 * Single source of truth for all navigation items.
 * Used by Sidebar, CommandPalette, and Breadcrumb.
 */
import {
  LayoutDashboard, Building2, ShieldCheck, FileText,
  Zap, ListChecks, Activity, Import, Users, Receipt,
  BookOpen, ShoppingCart, Search, Link2, Eye, Bell, Lock,
} from 'lucide-react';

export const ROUTE_MODULE_MAP = {
  '/': 'cockpit',
  '/cockpit': 'cockpit',
  '/notifications': 'cockpit',
  '/conformite': 'conformite',
  '/actions': 'actions',
  '/patrimoine': 'patrimoine',
  '/consommations': 'consommations',
  '/diagnostic-conso': 'diagnostic',
  '/bill-intel': 'billing',
  '/achat-energie': 'purchase',
  '/monitoring': 'monitoring',
  '/import': null,
  '/connectors': null,
  '/segmentation': null,
  '/watchers': null,
  '/kb': null,
  '/admin/users': null,
};

export const NAV_SECTIONS = [
  {
    label: 'Pilotage',
    items: [
      { to: '/',              icon: LayoutDashboard, label: 'Tableau de bord', keywords: ['dashboard', 'accueil', 'home'] },
      { to: '/cockpit',       icon: FileText,        label: 'Vue executive', keywords: ['synthese', 'executive', 'brief'] },
      { to: '/notifications', icon: Bell,            label: 'Alertes', badgeKey: 'alerts', keywords: ['alertes', 'notifications'] },
    ],
  },
  {
    label: 'Execution',
    items: [
      { to: '/conformite', icon: ShieldCheck, label: 'Conformite', keywords: ['compliance', 'reglementation', 'decret'] },
      { to: '/actions',    icon: ListChecks,  label: "Plan d'actions", keywords: ['actions', 'plan', 'todo'] },
    ],
  },
  {
    label: 'Analyse',
    items: [
      { to: '/patrimoine',       icon: Building2,     label: 'Patrimoine', keywords: ['sites', 'batiments', 'immobilier'] },
      { to: '/consommations',    icon: Zap,           label: 'Consommations', keywords: ['conso', 'energie', 'import'] },
      { to: '/diagnostic-conso', icon: Search,        label: 'Diagnostic', keywords: ['anomalies', 'diagnostic', 'analyse'] },
      { to: '/bill-intel',       icon: Receipt,       label: 'Facturation', keywords: ['factures', 'billing', 'invoices'] },
      { to: '/achat-energie',    icon: ShoppingCart,   label: 'Achats energie', keywords: ['achat', 'purchase', 'scenarios'] },
      { to: '/monitoring',       icon: Activity,      label: 'Performance', badgeKey: 'monitoring', keywords: ['monitoring', 'kpi', 'puissance'] },
    ],
  },
  {
    label: 'Administration',
    items: [
      { to: '/import',       icon: Import,   label: 'Imports', keywords: ['import', 'csv', 'upload'] },
      { to: '/connectors',   icon: Link2,    label: 'Connexions', keywords: ['connecteurs', 'api', 'sync'] },
      { to: '/segmentation', icon: Users,    label: 'Segmentation', keywords: ['segment', 'profil'] },
      { to: '/watchers',     icon: Eye,      label: 'Veille', keywords: ['veille', 'rss', 'reglementaire'] },
      { to: '/kb',           icon: BookOpen, label: 'Referentiels', keywords: ['kb', 'knowledge', 'base'] },
    ],
  },
  {
    label: 'IAM',
    items: [
      { to: '/admin/users',       icon: Lock,       label: 'Utilisateurs', requireAdmin: true, keywords: ['users', 'comptes'] },
      { to: '/admin/roles',       icon: ShieldCheck, label: 'Roles', requireAdmin: true, keywords: ['roles', 'permissions'] },
      { to: '/admin/assignments', icon: Users,      label: 'Assignments', requireAdmin: true, keywords: ['assignments', 'scopes'] },
      { to: '/admin/audit',       icon: FileText,   label: 'Audit Log', requireAdmin: true, keywords: ['audit', 'log', 'historique'] },
    ],
  },
];

// Flat list of all nav items (for CommandPalette search)
export const ALL_NAV_ITEMS = NAV_SECTIONS.flatMap((s) =>
  s.items.map((item) => ({ ...item, section: s.label }))
);
