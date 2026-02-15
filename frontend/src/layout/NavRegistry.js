/**
 * PROMEOS — Navigation Registry (World-Class IA)
 * 5 sections stables oriente jobs-to-be-done:
 * Piloter / Executer / Analyser / Marche & Factures / Donnees & Admin
 *
 * Normal mode: ~8 items (Piloter + Executer + Analyser core)
 * Expert mode: + Diagnostic + Marche + Donnees & Admin
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
    key: 'piloter',
    label: 'Piloter',
    expertOnly: false,
    collapsible: false,
    order: 1,
    items: [
      { to: '/',              icon: LayoutDashboard, label: 'Tableau de bord', keywords: ['dashboard', 'accueil', 'home', 'tableau'] },
      { to: '/cockpit',       icon: FileText,        label: 'Vue executive', keywords: ['synthese', 'executive', 'brief'] },
      { to: '/notifications', icon: Bell,            label: 'Alertes', badgeKey: 'alerts', keywords: ['alertes', 'notifications'] },
    ],
  },
  {
    key: 'executer',
    label: 'Executer',
    expertOnly: false,
    collapsible: false,
    order: 2,
    items: [
      { to: '/conformite', icon: ShieldCheck, label: 'Conformite', keywords: ['compliance', 'reglementation', 'decret'] },
      { to: '/actions',    icon: ListChecks,  label: "Plan d'actions", keywords: ['actions', 'plan', 'todo'] },
    ],
  },
  {
    key: 'analyser',
    label: 'Analyser',
    expertOnly: false,
    collapsible: true,
    defaultCollapsed: false,
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
    label: 'Marche & Factures',
    expertOnly: true,
    collapsible: true,
    defaultCollapsed: true,
    order: 4,
    items: [
      { to: '/bill-intel',      icon: Receipt,      label: 'Facturation', keywords: ['factures', 'billing', 'invoices'] },
      { to: '/achat-energie',   icon: ShoppingCart,  label: 'Achats energie', keywords: ['achat', 'purchase', 'scenarios', 'strategie'] },
      { to: '/achat-assistant', icon: Target,        label: 'Assistant Achat', keywords: ['assistant', 'wizard', 'rfp', 'arenh', 'corridor'] },
    ],
  },
  {
    key: 'admin',
    label: 'Donnees & Admin',
    expertOnly: true,
    collapsible: true,
    defaultCollapsed: true,
    order: 5,
    items: [
      { to: '/import',              icon: Import,      label: 'Imports', keywords: ['import', 'csv', 'upload'] },
      { to: '/connectors',          icon: Link2,       label: 'Connexions', keywords: ['connecteurs', 'api', 'sync'] },
      { to: '/kb',                  icon: BookOpen,    label: 'Knowledge Base', keywords: ['kb', 'knowledge', 'base'] },
      { to: '/segmentation',        icon: Users,       label: 'Segmentation', keywords: ['segment', 'profil'] },
      { to: '/watchers',            icon: Eye,         label: 'Veille', keywords: ['veille', 'rss', 'reglementaire'] },
      { to: '/admin/users',         icon: Lock,        label: 'Utilisateurs', requireAdmin: true, expertOnly: true, keywords: ['users', 'comptes'] },
      { to: '/admin/roles',         icon: ShieldCheck, label: 'Roles', requireAdmin: true, expertOnly: true, keywords: ['roles', 'permissions'] },
      { to: '/admin/assignments',   icon: Users,       label: 'Assignments', requireAdmin: true, expertOnly: true, keywords: ['assignments', 'scopes'] },
      { to: '/admin/audit',         icon: FileText,    label: 'Audit Log', requireAdmin: true, expertOnly: true, keywords: ['audit', 'log', 'historique'] },
    ],
  },
];

// Flat list of all nav items (for CommandPalette search)
export const ALL_NAV_ITEMS = NAV_SECTIONS.flatMap((s) =>
  s.items.map((item) => ({ ...item, section: s.label }))
);
