/**
 * PROMEOS — Navigation Registry V7 (Rail + Panel Architecture)
 *
 * 6 modules total, 5 visibles en mode normal (rail stable) :
 *   1. Cockpit    (Accueil — bleu)
 *   2. Conformité (vert émeraude) — MODULE AUTONOME
 *   3. Énergie    (indigo)
 *   4. Patrimoine (ambre)
 *   5. Achat      (violet)
 *   6. Admin      (slate — expertOnly)
 *
 * `expertOnly` au niveau ITEM uniquement (sauf admin).
 * Normal : 13 items visibles. Expert : 17 items (+4 : audit-sme, diagnostics, facturation, simulateur).
 *
 * Changelog V7 (2026-04-10) :
 *  - Conformité promue en module autonome
 *  - Facturation migrée de Énergie vers Patrimoine (expertOnly)
 *  - Achat visible en mode normal (plus expertOnly)
 *  - Usages visible en mode normal (sorti de HIDDEN_PAGES)
 *  - Vocabulaire : Cockpit→Accueil, BACS→Pilotage bâtiment, APER→Solarisation (APER),
 *    Performance→Performance énergétique, Usages→Répartition par usage,
 *    Stratégies d'achat→Scénarios d'achat, Assistant→Simulateur d'achat
 *  - Actions & Suivi + Notifications retirés (déplacés dans Centre d'actions header)
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
  Target,
  Database,
  ScanLine,
  AlertTriangle,
  Sparkles,
  Rocket,
  Settings,
  Download,
  HelpCircle,
  ToggleRight,
  MapPin,
  TrendingUp,
  Calculator,
  Upload,
  BarChart3,
  Sun,
  Cpu,
  Building,
  SearchCheck,
  PieChart,
} from 'lucide-react';

/* ── Route → module mapping ── */
export const ROUTE_MODULE_MAP = {
  // Cockpit (ex-pilotage)
  '/': 'cockpit',
  '/cockpit': 'cockpit',
  '/onboarding': 'cockpit',
  '/onboarding/sirene': 'patrimoine',
  // Backward compat (redirigés vers Centre d'actions via AppShell)
  '/notifications': 'cockpit',
  '/actions': 'cockpit',
  '/actions/new': 'cockpit',
  '/actions/:actionId': 'cockpit',
  '/anomalies': 'cockpit',
  '/action-center': 'cockpit',

  // Conformité (module autonome)
  '/conformite': 'conformite',
  '/conformite/dt': 'conformite',
  '/conformite/bacs': 'conformite',
  '/conformite/aper': 'conformite',
  '/conformite/audit-sme': 'conformite',
  '/conformite/tertiaire': 'conformite',
  '/conformite/tertiaire/wizard': 'conformite',
  '/conformite/tertiaire/anomalies': 'conformite',
  '/conformite/tertiaire/efa/:id': 'conformite',
  '/compliance': 'conformite',
  '/compliance/pipeline': 'conformite',
  '/compliance/sites/:siteId': 'conformite',
  '/regops/:id': 'conformite',

  // Énergie
  '/consommations': 'energie',
  '/consommations/explorer': 'energie',
  '/consommations/import': 'energie',
  '/consommations/portfolio': 'energie',
  '/diagnostic-conso': 'energie',
  '/usages': 'energie',
  '/usages-horaires': 'energie',
  '/monitoring': 'energie',

  // Patrimoine (Facturation migrée ici)
  '/patrimoine': 'patrimoine',
  '/patrimoine/nouveau': 'patrimoine',
  '/sites/:id': 'patrimoine',
  '/contrats': 'patrimoine',
  '/billing': 'patrimoine',
  '/bill-intel': 'patrimoine',
  '/payment-rules': 'patrimoine',
  '/portfolio-reconciliation': 'patrimoine',

  // Achat
  '/achat-energie': 'achat',
  '/renouvellements': 'achat',

  // Admin
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
};

/**
 * matchRouteToModule — "best match wins" route resolver.
 */
export function matchRouteToModule(pathname) {
  const clean = pathname.split('?')[0].split('#')[0];

  // 1. Exact match
  if (ROUTE_MODULE_MAP[clean]) {
    return _result(clean, ROUTE_MODULE_MAP[clean]);
  }

  // 2. Pattern match with dynamic segments
  const segments = clean.split('/').filter(Boolean);
  let bestPattern = null;
  let bestScore = -1;

  for (const pattern of Object.keys(ROUTE_MODULE_MAP)) {
    if (!pattern.includes(':')) continue;
    const patternSegs = pattern.split('/').filter(Boolean);
    if (patternSegs.length !== segments.length) continue;

    let match = true;
    let score = 0;
    for (let i = 0; i < patternSegs.length; i++) {
      if (patternSegs[i].startsWith(':')) {
        score += 1;
      } else if (patternSegs[i] === segments[i]) {
        score += 2;
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

  // 3. Prefix fallback
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

/* ── Module definitions (6 modules, 5 visibles en normal) ── */
export const NAV_MODULES = [
  {
    key: 'cockpit',
    label: 'Accueil',
    icon: LayoutDashboard,
    tint: 'blue',
    expertOnly: false,
    order: 1,
    desc: 'Synthèse & décisions',
  },
  {
    key: 'conformite',
    label: 'Conformité',
    icon: ShieldCheck,
    tint: 'emerald',
    expertOnly: false,
    order: 2,
    desc: 'Obligations réglementaires',
  },
  {
    key: 'energie',
    label: 'Énergie',
    icon: Zap,
    tint: 'indigo',
    expertOnly: false,
    order: 3,
    desc: 'Consommations & performance',
  },
  {
    key: 'patrimoine',
    label: 'Patrimoine',
    icon: Building2,
    tint: 'amber',
    expertOnly: false,
    order: 4,
    desc: 'Sites, contrats & factures',
  },
  {
    key: 'achat',
    label: 'Achat',
    icon: ShoppingCart,
    tint: 'violet',
    expertOnly: false,
    order: 5,
    desc: 'Échéances & arbitrage énergie',
  },
  {
    key: 'admin',
    label: 'Administration',
    icon: Settings,
    tint: 'slate',
    expertOnly: true,
    order: 6,
    desc: 'Import, utilisateurs et système',
  },
];

/* ── Centralized Tint Palette (Color Life System) ── */
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
  violet: {
    headerBand: 'from-violet-50/50 to-transparent',
    panelHeader: 'from-violet-50/30 to-transparent',
    softBg: 'bg-violet-50/40',
    hoverBg: 'bg-violet-50/30',
    activeBg: 'bg-violet-50/60',
    activeText: 'text-violet-700',
    activeBorder: 'border-violet-500',
    railActiveBg: 'bg-violet-50/70',
    railActiveRing: 'ring-violet-300/50',
    railActiveText: 'text-violet-600',
    dot: 'bg-violet-400',
    icon: 'text-violet-500',
    pillBg: 'bg-violet-50',
    pillText: 'text-violet-700',
    pillRing: 'ring-violet-200/60',
  },
  yellow: {
    headerBand: 'from-yellow-50/50 to-transparent',
    panelHeader: 'from-yellow-50/30 to-transparent',
    softBg: 'bg-yellow-50/40',
    hoverBg: 'bg-yellow-50/30',
    activeBg: 'bg-yellow-50/60',
    activeText: 'text-yellow-700',
    activeBorder: 'border-yellow-500',
    railActiveBg: 'bg-yellow-50/70',
    railActiveRing: 'ring-yellow-300/50',
    railActiveText: 'text-yellow-600',
    dot: 'bg-yellow-400',
    icon: 'text-yellow-500',
    pillBg: 'bg-yellow-50',
    pillText: 'text-yellow-700',
    pillRing: 'ring-yellow-200/60',
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

/* ── Module tint colors for header bands ── */
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
  { key: 'import', label: 'Importer', icon: Import, to: '/import', keywords: ['csv', 'upload'] },
  {
    key: 'centre',
    label: 'Détection automatique',
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
    longLabel: "Scénarios d'achat & échéances",
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
    key: 'sirene',
    label: 'Créer depuis Sirene',
    longLabel: 'Créer un patrimoine depuis SIREN',
    icon: Building2,
    to: '/onboarding/sirene',
    keywords: [
      'sirene',
      'siren',
      'siret',
      'nouvelle entreprise',
      'nouveau client',
      'insee',
      'patrimoine',
      'auto-complete',
      'autocomplete',
      'creer organisation',
      'onboarding sirene',
    ],
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

/* ── Section definitions (Panel content per module) ──
 *  NAV_SECTIONS: une section par module (pas de sections imbriquées).
 *  `expertOnly` au niveau ITEM uniquement.
 */
export const NAV_SECTIONS = [
  // === COCKPIT / ACCUEIL (blue) ===
  {
    key: 'cockpit',
    module: 'cockpit',
    label: 'Accueil',
    expertOnly: false,
    order: 1,
    items: [
      {
        to: '/',
        icon: LayoutDashboard,
        label: 'Tableau de bord',
        desc: 'KPIs J-1, alertes, trajectoire mensuelle',
        keywords: ['dashboard', 'accueil', 'home', 'tableau'],
      },
      {
        to: '/cockpit',
        icon: BarChart3,
        label: 'Vue exécutive',
        desc: 'Synthèse portefeuille pour la direction',
        keywords: ['cockpit', 'executive', 'synthese', 'strategique'],
      },
    ],
  },

  // === CONFORMITÉ (emerald) — module autonome ===
  {
    key: 'conformite',
    module: 'conformite',
    label: 'Conformité',
    expertOnly: false,
    order: 2,
    items: [
      {
        to: '/conformite',
        icon: ShieldCheck,
        label: 'Conformité',
        desc: 'DT, BACS, Audit SMÉ — score & obligations',
        keywords: [
          'compliance',
          'reglementation',
          'obligations',
          'score',
          'decret',
          'tertiaire',
          'operat',
          'efa',
          'bacs',
          'gtb',
          'gtc',
          'automatisation',
          'audit',
          'sme',
          'energetique',
        ],
      },
      {
        to: '/conformite/aper',
        icon: Sun,
        label: 'Solarisation (APER)',
        desc: 'Obligations ENR parkings & toitures',
        keywords: ['aper', 'solaire', 'parking', 'toiture', 'photovoltaique', 'pvgis'],
      },
    ],
  },

  // === ÉNERGIE (indigo) ===
  {
    key: 'energie',
    module: 'energie',
    label: 'Énergie',
    expertOnly: false,
    order: 3,
    items: [
      {
        to: '/consommations',
        icon: Activity,
        label: 'Consommations',
        desc: 'Explorer les courbes de charge par site',
        keywords: ['conso', 'energie', 'explorer', 'horaires'],
      },
      {
        to: '/monitoring',
        icon: TrendingUp,
        label: 'Performance énergétique',
        desc: 'KPIs puissance, heatmap, tendances',
        badgeKey: 'monitoring',
        keywords: ['monitoring', 'kpi', 'puissance', 'performance', 'heatmap'],
      },
      {
        to: '/usages',
        icon: PieChart,
        label: 'Répartition par usage',
        desc: 'Ventilation CVC, éclairage, process',
        keywords: ['usages', 'energetiques', 'plan comptage', 'readiness', 'ues', 'baseline'],
      },
      {
        to: '/diagnostic-conso',
        icon: SearchCheck,
        label: 'Diagnostics',
        desc: 'Détection anomalies & gisements',
        keywords: ['diagnostic', 'anomalies', 'analyse'],
      },
    ],
  },

  // === PATRIMOINE (amber) ===
  {
    key: 'patrimoine',
    module: 'patrimoine',
    label: 'Patrimoine',
    expertOnly: false,
    order: 4,
    items: [
      {
        to: '/patrimoine',
        icon: MapPin,
        label: 'Sites & bâtiments',
        desc: 'Registre des sites, surfaces, compteurs',
        hint: 'Cliquez sur un site pour voir sa fiche',
        keywords: ['sites', 'batiments', 'immobilier', 'patrimoine', 'registre'],
      },
      {
        to: '/contrats',
        icon: FileText,
        label: 'Contrats énergie',
        desc: 'Contrats cadre, annexes, tarifs',
        keywords: ['contrats', 'cadre', 'annexe', 'fournisseur', 'tarif', 'pricing'],
      },
      {
        to: '/bill-intel',
        icon: Receipt,
        label: 'Facturation',
        desc: 'Anomalies factures, shadow billing',
        keywords: [
          'factures',
          'billing',
          'anomalies',
          'surfacturation',
          'historique',
          'shadow',
          'timeline',
        ],
      },
    ],
  },

  // === ACHAT (violet) — visible en normal ===
  {
    key: 'achat',
    module: 'achat',
    label: 'Achat',
    expertOnly: false,
    order: 5,
    items: [
      {
        to: '/renouvellements',
        icon: CalendarRange,
        label: 'Échéances',
        desc: 'Contrats à renouveler, radar portefeuille',
        keywords: ['renouvellements', 'contrats', 'echeances', 'radar', 'expiration'],
      },
      {
        to: '/achat-energie',
        icon: Calculator,
        label: "Scénarios d'achat",
        desc: 'Comparer offres, simuler, assistant achat',
        keywords: [
          'achat',
          'purchase',
          'scenarios',
          'strategie',
          'contrats',
          'assistant',
          'wizard',
          'rfp',
          'corridor',
          'negociation',
          'simulateur',
        ],
      },
    ],
  },

  // === ADMIN (slate) — module expertOnly ===
  {
    key: 'admin-data',
    module: 'admin',
    label: 'Données',
    expertOnly: true,
    order: 7,
    items: [
      {
        to: '/import',
        icon: Upload,
        label: 'Import données',
        keywords: ['import', 'csv', 'upload'],
      },
      {
        to: '/admin/users',
        icon: Users,
        label: 'Utilisateurs',
        requireAdmin: true,
        keywords: ['users', 'comptes'],
      },
      {
        to: '/watchers',
        icon: Eye,
        label: 'Veille réglementaire',
        keywords: ['veille', 'rss', 'reglementaire'],
      },
      {
        to: '/status',
        icon: Settings,
        label: 'Système',
        keywords: ['status', 'health', 'connecteurs', 'kb', 'segmentation'],
      },
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

/** Filter nav items according to expert mode (expertOnly items are hidden in normal) */
export function getVisibleItems(items, expertMode) {
  return expertMode ? items : items.filter((item) => !item.expertOnly);
}

/* ══════════════════════════════════════════════════════════════════════════
 * PANEL_SECTIONS_BY_ROUTE — configuration conforme maquette V2 raw
 *
 * Structure par route, chargée par SolPanel pour afficher les sections
 * sémantiques de la maquette (Cette semaine / Horizons / Vue d'ensemble)
 * au lieu des sections génériques NAV_SECTIONS (qui restent le fallback).
 *
 * Routes sans entrée ici → SolPanel retombe sur `getSectionsForModule()`
 * (comportement legacy non-cassant).
 * ══════════════════════════════════════════════════════════════════════════ */
export const PANEL_SECTIONS_BY_ROUTE = {
  // ─────────────────────────────────────────────────────────────────────────
  // Cockpit — pré-configuré Phase 3
  // ─────────────────────────────────────────────────────────────────────────
  '/cockpit': [
    {
      key: 'semaine',
      label: 'Cette semaine',
      items: [
        { to: '/cockpit', label: "Vue d'accueil", desc: 'KPIs + signaux hebdo' },
        { to: '/actions', label: "Journal d'actions", desc: 'Actions Sol append-only', badgeKey: 'actions' },
        { to: '/notifications', label: 'Alertes', desc: 'Détection automatique', badgeKey: 'alertes' },
      ],
    },
    {
      key: 'horizons',
      label: 'Horizons',
      items: [
        { to: '/conformite', label: 'Trajectoire 2030', desc: 'Décret tertiaire −25 %' },
        { to: '/conformite/aper', label: 'Trajectoire 2040', desc: 'APER + solarisation' },
      ],
    },
    {
      key: 'ensemble',
      label: "Vue d'ensemble",
      items: [
        { to: '/patrimoine', label: 'Patrimoine', desc: 'Sites + contrats + factures' },
        { to: '/cockpit-fixtures', label: 'Vue démo', desc: 'Fixtures Sol V1', expertOnly: true },
      ],
    },
  ],
  // ─────────────────────────────────────────────────────────────────────────
  // Conformité — pré-rempli Phase 4.0 (items affinés lors Phase 4.1 audit)
  // ─────────────────────────────────────────────────────────────────────────
  '/conformite': [
    {
      key: 'surveillance',
      label: 'Surveillance',
      items: [
        { to: '/conformite', label: "Vue d'ensemble", desc: 'Score global + risques' },
        { to: '/conformite/audit-sme', label: 'Audit SMÉ', desc: 'Audit énergétique ISO 50001', expertOnly: true },
      ],
    },
    {
      key: 'echeances',
      label: 'Échéances',
      items: [
        { to: '/conformite/tertiaire', label: 'Décret tertiaire', desc: 'OPERAT · 30 septembre', badgeKey: 'dt_deadline' },
        { to: '/conformite/bacs', label: 'BACS / GTB', desc: 'Obligation > 290 kW', badgeKey: 'bacs_deadline' },
        { to: '/conformite/aper', label: 'Solarisation APER', desc: 'Parkings + toitures' },
      ],
    },
    {
      key: 'sites_critiques',
      label: 'Sites critiques',
      items: [
        { to: '/compliance/pipeline', label: 'Pipeline findings', desc: 'Non-conformités détectées', expertOnly: true },
        { to: '/regops/dashboard', label: 'Tableau RegOps', desc: 'Assessments par site', expertOnly: true },
      ],
    },
  ],
  // ─────────────────────────────────────────────────────────────────────────
  // Bill Intelligence — pré-rempli Phase 4.0
  // ─────────────────────────────────────────────────────────────────────────
  '/bill-intel': [
    {
      key: 'courant',
      label: 'Mois en cours',
      items: [
        { to: '/bill-intel', label: 'Vue synthèse', desc: 'Factures + anomalies' },
        { to: '/billing', label: 'Factures détaillées', desc: 'Liste + audit ligne-à-ligne' },
      ],
    },
    {
      key: 'anomalies',
      label: 'Anomalies',
      items: [
        { to: '/bill-intel?tab=anomalies', label: 'À contester', desc: "Anomalies détectées", badgeKey: 'anomalies_count' },
        { to: '/bill-intel?tab=contestations', label: 'En cours', desc: 'Courriers envoyés' },
      ],
    },
    {
      key: 'historique',
      label: 'Historique',
      items: [
        { to: '/portfolio-reconciliation', label: 'Réconciliation', desc: 'Couverture + gaps' },
        { to: '/payment-rules', label: 'Règles paiement', desc: 'Contrôles automatiques', expertOnly: true },
      ],
    },
  ],
  // ─────────────────────────────────────────────────────────────────────────
  // Patrimoine — pré-rempli Phase 4.0
  // ─────────────────────────────────────────────────────────────────────────
  '/patrimoine': [
    {
      key: 'global',
      label: 'Vue globale',
      items: [
        { to: '/patrimoine', label: 'Sites & bâtiments', desc: 'Registre consolidé' },
        { to: '/contrats', label: 'Contrats énergie', desc: 'Cadre + annexes + tarifs' },
      ],
    },
    {
      key: 'par_type',
      label: 'Par type',
      items: [
        { to: '/patrimoine?type=bureau', label: 'Bureaux', desc: 'Tertiaire administratif' },
        { to: '/patrimoine?type=entrepot', label: 'Entrepôts', desc: 'Logistique + process' },
        { to: '/patrimoine?type=enseignement', label: 'Enseignement', desc: 'Écoles + universités' },
      ],
    },
    {
      key: 'actions',
      label: 'Actions',
      items: [
        { to: '/bill-intel', label: 'Facturation', desc: 'Anomalies + contestations' },
        { to: '/onboarding/sirene', label: 'Nouveau site', desc: 'Onboarding depuis SIRENE' },
      ],
    },
  ],
  // ─────────────────────────────────────────────────────────────────────────
  // Achat énergie — pré-rempli Phase 4.0
  // ─────────────────────────────────────────────────────────────────────────
  '/achat-energie': [
    {
      key: 'contrats',
      label: 'Contrats',
      items: [
        { to: '/renouvellements', label: 'Échéances', desc: 'Radar portefeuille', badgeKey: 'renewals_90j' },
        { to: '/contrats', label: 'Contrats référence', desc: 'Cadre + annexes', expertOnly: true },
      ],
    },
    {
      key: 'marche',
      label: 'Marché',
      items: [
        { to: '/achat-energie', label: 'Simulateur', desc: 'Prix post-ARENH' },
        { to: '/achat-energie?tab=marche', label: 'Prix spot & forward', desc: 'EPEX + Powernext' },
      ],
    },
    {
      key: 'scenarios',
      label: 'Scénarios',
      items: [
        { to: '/achat-energie?tab=assistant', label: "Assistant d'achat", desc: 'Wizard RFP + corridor' },
        { to: '/achat-energie?tab=portefeuille', label: 'Vue portefeuille', desc: 'Agrégé multi-sites' },
      ],
    },
  ],
};

/**
 * Résout les sections à afficher dans SolPanel pour une route donnée.
 * Priorité : PANEL_SECTIONS_BY_ROUTE[route] → getSectionsForModule(moduleKey).
 */
export function getPanelSections(pathname, expertMode) {
  const clean = (pathname || '').split('?')[0].split('#')[0];
  // 1. Match exact route
  if (PANEL_SECTIONS_BY_ROUTE[clean]) {
    return PANEL_SECTIONS_BY_ROUTE[clean]
      .map((s) => ({ ...s, items: getVisibleItems(s.items, expertMode) }))
      .filter((s) => s.items.length > 0);
  }
  // 2. Fallback : sections génériques du module courant
  const { moduleId } = matchRouteToModule(clean);
  const fallback = getSectionsForModule(moduleId);
  return fallback.map((s) => ({
    key: s.key,
    label: s.label,
    items: getVisibleItems(s.items || [], expertMode),
  })).filter((s) => s.items.length > 0);
}

/** Flat list of all nav items (for CommandPalette search) — base path only (no query) */
export const ALL_NAV_ITEMS = NAV_SECTIONS.flatMap((s) =>
  s.items.map((item) => ({ ...item, section: s.label, module: s.module }))
);

/* ── Section tints (derived from parent module) ── */
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
  const mod = NAV_MODULES.find((m) => m.key === keyOrPath);
  if (mod) return TINT_PALETTE[mod.tint] || TINT_PALETTE.slate;
  const moduleKey = resolveModule(keyOrPath);
  const resolved = NAV_MODULES.find((m) => m.key === moduleKey);
  return TINT_PALETTE[resolved?.tint || 'slate'] || TINT_PALETTE.slate;
}

/* ══════════════════════════════════════════════════════════════════
 * ROLE-BASED module ordering — each role sees its most relevant
 * modules first on the rail. Fallback to default order.
 * ══════════════════════════════════════════════════════════════════ */
const ROLE_MODULE_ORDER = {
  // Direction / finance : focus décisionnel
  dg_owner: ['cockpit', 'achat', 'conformite', 'patrimoine', 'energie'],
  daf: ['cockpit', 'patrimoine', 'achat', 'conformite', 'energie'],
  acheteur: ['cockpit', 'achat', 'patrimoine', 'conformite', 'energie'],

  // Technique / opérationnel : focus données + action
  energy_manager: ['cockpit', 'energie', 'conformite', 'patrimoine', 'achat'],
  resp_conformite: ['cockpit', 'conformite', 'patrimoine', 'energie', 'achat'],
  resp_immobilier: ['cockpit', 'patrimoine', 'conformite', 'energie', 'achat'],
  resp_site: ['cockpit', 'patrimoine', 'energie', 'conformite', 'achat'],

  // Default order (no role or unknown)
  default: ['cockpit', 'conformite', 'energie', 'patrimoine', 'achat'],
};

/**
 * Reorders NAV_MODULES based on user role. Admin module always last.
 * @param {string} role - User role key
 * @param {boolean} isExpert - Expert mode (shows admin)
 * @returns {Array} Ordered modules
 */
export function getOrderedModules(role, isExpert) {
  const order = ROLE_MODULE_ORDER[role] || ROLE_MODULE_ORDER.default;
  const byKey = Object.fromEntries(NAV_MODULES.map((m) => [m.key, m]));
  const ordered = order.map((key) => byKey[key]).filter(Boolean);
  if (isExpert && byKey.admin) ordered.push(byKey.admin);
  return ordered;
}

/* ══════════════════════════════════════════════════════════════════
 * NAV_MAIN_SECTIONS — Miroir de NAV_SECTIONS utilisé par Breadcrumb.jsx.
 * Maintenu synchronisé avec NAV_SECTIONS (même labels, mêmes items).
 * ══════════════════════════════════════════════════════════════════ */

export const NAV_MAIN_SECTIONS = NAV_SECTIONS.filter((s) => s.module !== 'admin').map((s) => {
  const mod = NAV_MODULES.find((m) => m.key === s.module);
  return {
    key: s.key,
    label: mod?.label || s.label,
    icon: mod?.icon,
    tint: mod?.tint || 'slate',
    order: s.order,
    items: s.items,
  };
});

/** Items du menu secondaire (engrenage) — Administration */
export const NAV_ADMIN_ITEMS = NAV_SECTIONS.find((s) => s.module === 'admin')?.items || [];

/** Icon for the admin secondary menu */
export const NAV_ADMIN_ICON = Settings;

/** Route → section label map (for breadcrumb) — base path only */
export const ROUTE_SECTION_MAP = Object.fromEntries(
  NAV_MAIN_SECTIONS.flatMap((section) =>
    section.items.map((item) => {
      const basePath = item.to.split('?')[0].split('#')[0];
      return [basePath, section.label];
    })
  )
);

/** Pages retirées du menu mais trouvables via CommandPalette (Ctrl+K) */
export const HIDDEN_PAGES = [
  {
    to: '/kb',
    icon: BookOpen,
    label: 'Mémobox / Base de connaissances',
    keywords: ['kb', 'knowledge', 'memobox', 'documents'],
    section: 'Autres',
    hidden: true,
  },
  {
    to: '/segmentation',
    icon: Users,
    label: 'Segmentation',
    keywords: ['segment', 'profil'],
    section: 'Autres',
    hidden: true,
  },
  {
    to: '/connectors',
    icon: Link2,
    label: 'Connecteurs',
    keywords: ['connecteurs', 'api', 'sync'],
    section: 'Autres',
    hidden: true,
  },
  {
    to: '/usages-horaires',
    icon: Activity,
    label: 'Usages & Horaires',
    keywords: ['usages', 'horaires', 'profil', 'heatmap', 'comportement'],
    section: 'Énergie',
    hidden: true,
  },
  {
    to: '/conformite/tertiaire',
    icon: Building2,
    label: 'Tertiaire / OPERAT',
    keywords: ['tertiaire', 'operat', 'efa', 'décret'],
    section: 'Conformité',
    hidden: true,
  },
  {
    to: '/compliance/pipeline',
    icon: ListChecks,
    label: 'Pipeline conformité',
    keywords: ['pipeline', 'findings'],
    section: 'Conformité',
    hidden: true,
  },
  {
    to: '/anomalies',
    icon: AlertTriangle,
    label: 'Détection automatique',
    keywords: ['anomalies', 'inbox', 'detection', 'automatique'],
    section: 'Accueil',
    hidden: true,
  },
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
  {
    key: 'creer-action',
    label: 'Créer une action',
    icon: Target,
    to: '/actions/new',
    shortcut: 'Ctrl+Shift+A',
    keywords: ['créer', 'action', 'nouvelle'],
  },
  {
    key: 'importer',
    label: 'Importer des données',
    icon: Import,
    to: '/import',
    shortcut: 'Ctrl+Shift+I',
    keywords: ['import', 'csv', 'upload', 'données'],
  },
  {
    key: 'centre-actions',
    label: "Centre d'actions",
    icon: AlertTriangle,
    to: '/?actionCenter=open&tab=actions',
    shortcut: 'Ctrl+Shift+L',
    keywords: ['alertes', 'anomalies', 'actions', 'centre', 'notifications'],
  },
  {
    key: 'cockpit',
    label: 'Aller au cockpit',
    icon: LayoutDashboard,
    to: '/cockpit',
    shortcut: 'Ctrl+Shift+C',
    keywords: ['cockpit', 'executive', 'synthese'],
  },
  {
    key: 'changer-site',
    label: 'Changer de site',
    icon: Building2,
    to: '/patrimoine',
    shortcut: 'Ctrl+Shift+S',
    keywords: ['site', 'patrimoine', 'changer'],
  },
  {
    key: 'exporter',
    label: 'Exporter CSV',
    icon: Download,
    to: '/consommations/explorer',
    shortcut: 'Ctrl+Shift+E',
    keywords: ['export', 'csv', 'télécharger'],
  },
  {
    key: 'conformite',
    label: 'Voir la conformité',
    icon: ShieldCheck,
    to: '/conformite',
    shortcut: 'Ctrl+Shift+F',
    keywords: ['conformité', 'compliance', 'décret'],
  },
  {
    key: 'factures',
    label: 'Voir les factures',
    icon: Receipt,
    to: '/bill-intel',
    shortcut: 'Ctrl+Shift+B',
    keywords: ['factures', 'billing', 'anomalies'],
  },
  {
    key: 'expert',
    label: 'Mode expert',
    icon: ToggleRight,
    to: '#expert-toggle',
    shortcut: 'Ctrl+Shift+X',
    keywords: ['expert', 'mode', 'pro', 'avancé'],
  },
  {
    key: 'aide',
    label: 'Aide',
    icon: HelpCircle,
    to: '/onboarding',
    shortcut: 'F1',
    keywords: ['aide', 'help', 'documentation', 'onboarding'],
  },
];
