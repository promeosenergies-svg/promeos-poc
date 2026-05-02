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
  Inbox,
} from 'lucide-react';

/* ── Route → module mapping ── */
export const ROUTE_MODULE_MAP = {
  // Cockpit (ex-pilotage)
  '/': 'cockpit',
  '/cockpit': 'cockpit',
  // Refonte WOW Cockpit dual sol2 (29/04/2026) : routes canoniques §11.3
  '/cockpit/jour': 'cockpit', // Briefing du jour = Pilotage 30s
  '/cockpit/strategique': 'cockpit', // Synthèse stratégique = Décision 3min
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
  // Phase 17.bis.B — Flex Intelligence rattachée au module Énergie
  // (auparavant orpheline → fallback 'cockpit' dans matchRouteToModule).
  '/flex': 'energie',

  // Patrimoine
  // Phase 1.D — P0.1 : Facturation extraite vers module dédié `facturation`
  // (cf. ROUTE_MODULE_MAP section facturation infra). Patrimoine garde
  // sites + contrats uniquement.
  '/patrimoine': 'patrimoine',
  '/patrimoine/nouveau': 'patrimoine',
  '/sites/:id': 'patrimoine',
  '/contrats': 'patrimoine',

  // Facturation (Phase 1.D — P0.1 : Bill Intelligence pilier doctrine
  // §4.4 promu module rail autonome)
  '/billing': 'facturation',
  '/bill-intel': 'facturation',
  '/payment-rules': 'facturation',
  '/portfolio-reconciliation': 'facturation',

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
  // Phase 1.E — P0.5 (audit navigation_audit_20260501.md §4 + §7 Q4) :
  // `groupBoundary: 'config'` marque la frontière "config / lookup" dans
  // l'ordre rail. NavRail rend un séparateur visuel discret AVANT ce
  // module (cf. NavRail.jsx). Patrimoine est systématiquement en dernière
  // position visible peu importe le persona — usage one-shot setup
  // (audit §5.3 fréquence).
  // Anti-pattern §6.2 strict : pas de label "Configuration", pas de
  // groupement niveau menu. Juste un trait fin de séparation rendering.
  {
    key: 'patrimoine',
    label: 'Patrimoine',
    icon: Building2,
    tint: 'amber',
    expertOnly: false,
    order: 4,
    desc: 'Sites, contrats & factures',
    groupBoundary: 'config',
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
  // Phase 1.D — P0.1 (audit navigation_audit_20260501.md §4.5 trou MVP P0
  // + §11 intention "Facture, anomalie, contestation" + doctrine §4.4
  // Bill Intelligence pilier autonome) : promotion de Bill Intelligence
  // depuis item enfoui sous Patrimoine vers module rail dédié.
  // Position 6 = avant-dernière (avant admin). L'ordre cible Sol v1.1
  // (Accueil → Énergie → Conformité → Facturation → Achat → [sep] →
  // Patrimoine) sera fixé par P0.5 séparément (decoupling structure /
  // ordre). Tint cyan ajouté à TINT_PALETTE.
  {
    key: 'facturation',
    label: 'Facturation',
    icon: Receipt,
    tint: 'cyan',
    expertOnly: false,
    order: 6,
    desc: 'Audit factures & anomalies',
  },
  {
    key: 'admin',
    label: 'Administration',
    icon: Settings,
    tint: 'slate',
    expertOnly: true,
    order: 7,
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
  // Phase 1.D — P0.1 (audit navigation_audit_20260501.md §4.5 trou MVP P0
  // #1) : tint dédié pour le module Bill Intelligence promu en module rail.
  // Cyan choisi pour le différencier du blue/indigo/emerald (modules voisins
  // Cockpit/Énergie/Conformité) tout en restant dans la famille "froide"
  // sémantique factures/audit. Pattern identique aux autres tints existants
  // (12 propriétés Tailwind v4) — aucun divergence.
  cyan: {
    headerBand: 'from-cyan-50/50 to-transparent',
    panelHeader: 'from-cyan-50/30 to-transparent',
    softBg: 'bg-cyan-50/40',
    hoverBg: 'bg-cyan-50/30',
    activeBg: 'bg-cyan-50/60',
    activeText: 'text-cyan-700',
    activeBorder: 'border-cyan-500',
    railActiveBg: 'bg-cyan-50/70',
    railActiveRing: 'ring-cyan-300/50',
    railActiveText: 'text-cyan-600',
    dot: 'bg-cyan-400',
    icon: 'text-cyan-500',
    pillBg: 'bg-cyan-50',
    pillText: 'text-cyan-700',
    pillRing: 'ring-cyan-200/60',
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
    // Phase 3.B — P1.5 : retargeté `/anomalies` → `/action-center`. Le
    // Centre d'action panel Accueil (Phase 1.C — P0.3) est devenu le
    // hub canonique pour anomalies + actions + notifications. Pointer
    // la Quick Action sur la page dédiée évite le doublon sémantique
    // signalé audit Phase 0.bis §5 (`/anomalies` brut redondant avec
    // l'item panel "Centre d'action"). L'URL `/anomalies` reste
    // accessible (HIDDEN_PAGES + redirect implicite côté ActionCenterPage).
    key: 'centre',
    label: 'Détection automatique',
    icon: AlertTriangle,
    to: '/action-center',
    keywords: ['anomalies', 'actions', 'inbox', 'centre', 'detection'],
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
      // Phase 1.A — P0.2 (audit navigation_audit_20260501.md §3 trou P0 #2) :
      // hard-cut renommage des libellés legacy panel Cockpit vers les libellés
      // canoniques doctrine Sol §11.3 (page de décision = aboutissement
      // narratif) + grammaire éditoriale §5 (titres narratifs).
      //   - "Vue exécutive"   → "Synthèse stratégique" (`/cockpit/strategique`,
      //                          page Décision DG/CFO 3 min).
      //   - "Tableau de bord" → "Briefing du jour"     (`/cockpit/jour`, page
      //                          Pilotage energy manager 30 s).
      //
      // Q5 audit (arbitrage Amine 2026-05-01) : keywords étendus pour
      // rétro-compat search palette (⌘K) — anciens libellés (`vue`,
      // `executive`, `tableau`, `dashboard`) restent indexés ; aucun terme
      // legacy retiré des keywords.
      //
      // Phase 1.C — P0.3 (audit navigation_audit_20260501.md §5 cible
      // persona Energy Manager dominant Sol §2) : ordre cockpit panel
      // révisé Briefing du jour → Synthèse stratégique. Cohérent avec
      // l'usage quotidien EM (Marc) : entrée par le briefing
      // opérationnel 30 s puis montée vers la synthèse stratégique 3 min.
      // Override l'ordre Phase 13.D (Synthèse premier pour démo CFO) —
      // la démo CFO reste servie par le redirect /cockpit → /cockpit/strategique
      // (legacyRedirects.js) qui ouvre directement la page Décision.
      {
        to: '/cockpit/jour',
        icon: LayoutDashboard,
        label: 'Briefing du jour',
        desc: "Quoi traiter aujourd'hui (30 s)",
        keywords: [
          'briefing',
          'jour',
          'pilotage',
          'accueil',
          'home',
          'aujourdhui',
          // rétro-compat search palette — anciens libellés legacy
          'tableau',
          'dashboard',
        ],
      },
      {
        to: '/cockpit/strategique',
        icon: BarChart3,
        label: 'Synthèse stratégique',
        desc: 'Où en sommes-nous (3 min)',
        keywords: [
          'synthese',
          'strategique',
          'cockpit',
          'decision',
          'codir',
          'cfo',
          'comex',
          // rétro-compat search palette — anciens libellés legacy
          'vue',
          'executive',
        ],
      },
      // Phase 1.C — P0.3 (audit navigation_audit_20260501.md §4.4 + §7 Q2) :
      // exposition du Centre d'action en item Accueil. La cloche header
      // (AppShell.jsx:328-332) reste autonome — surface complémentaire,
      // contexte d'usage distinct (cloche = peek transverse, item panel =
      // navigation explicite). Voir doctrine §6.2 anti-pattern "chemins
      // multiples" : 3 surfaces (panel / cloche / Ctrl+Shift+L) acceptables
      // car contextes d'usage distincts.
      {
        to: '/action-center',
        icon: Inbox,
        label: "Centre d'action",
        desc: 'Anomalies, actions et notifications à traiter',
        badgeKey: 'actionCenter',
        keywords: [
          'action',
          'actions',
          'centre',
          'inbox',
          'anomalies',
          'notifications',
          'alertes',
          'detection',
          'todo',
          'todos',
          'tâches',
        ],
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
        // Phase 17.bis.C — promotion Tertiaire/OPERAT en item sidebar
        // (était hidden, accessible uniquement via Quick Action ou breadcrumb).
        // Persona Marie DAF tertiaire : c'est la page principale de son funnel
        // (déclaration OPERAT annuelle + jalons -40 % / -50 % / -60 %).
        to: '/conformite/tertiaire',
        icon: Building2,
        label: 'Décret Tertiaire / OPERAT',
        desc: 'EFA, jalons 2030/2040/2050, simulation mutualisation',
        keywords: ['tertiaire', 'operat', 'dt', 'efa', 'jalons', 'mutualisation'],
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
      {
        // Phase 17.bis.B — Flex Intelligence rattaché au module Énergie
        // (était orpheline nav après S1.10 — accessible via deep-link uniquement).
        // Différenciant produit majeur (NEBCO + AOFD + capacité RTE).
        to: '/flex',
        icon: Zap,
        label: 'Flex Intelligence',
        desc: 'Effacement industriel — NEBCO, AOFD, mécanisme capacité',
        keywords: ['flex', 'effacement', 'nebco', 'aofd', 'capacite', 'rte', 'agregateur'],
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
      // Phase 1.D — P0.1 : item Facturation extrait vers module dédié
      // `facturation` (NAV_SECTIONS.facturation infra). Doctrine §4.4 +
      // §11 — pilier autonome, plus enfoui sous Patrimoine.
    ],
  },

  // === FACTURATION (cyan) — Phase 1.D — P0.1 ===
  // Promotion Bill Intelligence depuis item enfoui sous Patrimoine vers
  // module rail. 1 item panel "Vue d'ensemble" pointant sur /bill-intel
  // (point d'entrée unique : pas de sous-routes /bill-intel/* exposées
  // dans App.jsx — les variantes utilisent query-strings ?filter=...).
  {
    key: 'facturation',
    module: 'facturation',
    label: 'Facturation',
    expertOnly: false,
    order: 6,
    items: [
      {
        to: '/bill-intel',
        icon: Receipt,
        label: "Vue d'ensemble",
        desc: 'Anomalies factures, shadow billing',
        keywords: [
          'facturation',
          'factures',
          'billing',
          'bill-intel',
          'anomalies',
          'surfacturation',
          'historique',
          'shadow',
          'timeline',
          'reclaim',
          'audit',
          // rétro-compat search palette — ancien emplacement Patrimoine
          'patrimoine',
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
// Phase 1.E — P0.5 (audit navigation_audit_20260501.md §4 matrice d'écart
// + §7 Q3) : adoption de l'ordre rail final cible Sol v1.1 pour persona
// dominant Energy Manager (= default) :
//   Accueil → Énergie → Conformité → Facturation → Achat → [sep] → Patrimoine
//
// Multi-persona conservé (8 ROLE_MODULE_ORDER) — la matrice n'est pas
// supprimée (différenciation B2B forte). Mais Patrimoine est désormais
// systématiquement en dernière position visible peu importe le rôle :
// l'usage one-shot setup (audit §5.3) le justifie. Le séparateur graphique
// rendu par NavRail signale visuellement la frontière "config / lookup".
//
// Insertion `facturation` selon table fréquence §5.3 :
//   - DAF / DG : facturation #2 (hebdo / mensuel finance)
//   - Acheteur : facturation #3 (proximité achat)
//   - Energy Manager / default / resp_site : facturation #4
//   - RegOps / Resp. immobilier : facturation #4 (alignés default)
//
// Le séparateur lui-même est un détail rendering (groupBoundary='config'
// sur NAV_MODULES.patrimoine, cf. infra) — il n'apparaît jamais dans
// les arrays d'ordre.
const ROLE_MODULE_ORDER = {
  // Direction / finance : focus décisionnel
  dg_owner: ['cockpit', 'facturation', 'achat', 'conformite', 'energie', 'patrimoine'],
  daf: ['cockpit', 'facturation', 'conformite', 'energie', 'achat', 'patrimoine'],
  acheteur: ['cockpit', 'achat', 'facturation', 'energie', 'conformite', 'patrimoine'],

  // Technique / opérationnel : focus données + action
  energy_manager: ['cockpit', 'energie', 'conformite', 'facturation', 'achat', 'patrimoine'],
  resp_conformite: ['cockpit', 'conformite', 'energie', 'facturation', 'achat', 'patrimoine'],
  resp_immobilier: ['cockpit', 'conformite', 'energie', 'facturation', 'achat', 'patrimoine'],
  resp_site: ['cockpit', 'energie', 'conformite', 'facturation', 'achat', 'patrimoine'],

  // Default order (no role or unknown) = aligné sur energy_manager (cible Sol §2)
  default: ['cockpit', 'energie', 'conformite', 'facturation', 'achat', 'patrimoine'],
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

/**
 * HIDDEN_PAGES — Pages retirées du menu rail/panel mais indexées dans
 * la CommandPalette (⌘K) pour discovery via search.
 *
 * Phase 3.C — P1.6 (audit Phase 0.bis Q3) : chaque entrée DOIT
 * désormais documenter sa raison de masquage via le champ `reason`
 * (string non-vide). Le source-guard SG_NAV_FE_04 vérifie cette
 * convention en CI — empêche tout futur "caché par négligence".
 *
 * Catégories de raison acceptées (libre, mais cohérentes) :
 *   - "doublon-sub-page"   : sub-page d'un item visible (variante)
 *   - "outil-interne"      : page admin/marketing non destinée aux
 *                            persona client
 *   - "setup-technique"    : config/connecteurs accédés par admin
 *   - "workflow-specialise" : audience persona très réduite (RegOps...)
 *   - "deep-link-only"     : URL utile en deep-link mais sans entrée
 *                            rail (ex: alias d'un item promu)
 *   - "doctrine-§N.N"      : justification doctrinale explicite
 *
 * Phase 18.A — `/conformite/tertiaire` retiré de HIDDEN_PAGES (doublon
 * signalé audit Phase 17 cumulée). La route est désormais item visible
 * dans NAV_SECTIONS module Conformité (Phase 17.bis.C). Conserver dans
 * HIDDEN_PAGES créait un doublon CommandPalette via ALL_MAIN_ITEMS.
 */
export const HIDDEN_PAGES = [
  {
    to: '/kb',
    icon: BookOpen,
    label: 'Mémobox / Base de connaissances',
    keywords: ['kb', 'knowledge', 'memobox', 'documents'],
    section: 'Autres',
    hidden: true,
    reason:
      'outil-interne : référence documentaire pour power users. Search ⌘K adapté à un usage ponctuel — pas de signal rail justifiant un slot module dédié (doctrine §6.2 anti-pattern menu surchargé).',
  },
  {
    to: '/segmentation',
    icon: Users,
    label: 'Segmentation',
    keywords: ['segment', 'profil'],
    section: 'Autres',
    hidden: true,
    reason:
      'outil-interne : profilage marketing/produit, audience PROMEOS-team uniquement. Non destinée aux persona client — pas exposée rail.',
  },
  {
    to: '/connectors',
    icon: Link2,
    label: 'Connecteurs',
    keywords: ['connecteurs', 'api', 'sync'],
    section: 'Autres',
    hidden: true,
    reason:
      'setup-technique : configuration des connecteurs Enedis/GRDF/CSV. Accédée via /admin (rôle admin) ou onboarding. Pas de slot rail justifié — usage one-shot par admin.',
  },
  {
    to: '/usages-horaires',
    icon: Activity,
    label: 'Usages & Horaires',
    keywords: ['usages', 'horaires', 'profil', 'heatmap', 'comportement'],
    section: 'Énergie',
    hidden: true,
    reason:
      'doublon-sub-page : variante détaillée de /usages (item visible Énergie). Exposer les deux créerait un doublon pathologique anti-pattern §6.2 — keep hidden, reachable via search ou drill-down /usages.',
  },
  {
    to: '/compliance/pipeline',
    icon: ListChecks,
    label: 'Pipeline conformité',
    keywords: ['pipeline', 'findings'],
    section: 'Conformité',
    hidden: true,
    reason:
      'workflow-specialise : audience RegOps spécialisée (revue findings DT/BACS/APER batch). Audit Phase 0.bis Q3 a explicitement choisi keep-hidden — promotion item Conformité jugée non justifiée pour la majorité des persona (Marie DAF, Marc EM, Sophie DG).',
  },
  {
    to: '/anomalies',
    icon: AlertTriangle,
    label: 'Détection automatique',
    keywords: ['anomalies', 'inbox', 'detection', 'automatique'],
    section: 'Accueil',
    hidden: true,
    reason:
      "deep-link-only : URL legacy maintenue pour rétro-compat search palette + redirects. Le hub canonique est désormais /action-center (Phase 1.C — P0.3). Phase 3.B — P1.5 a retargeté la Quick Action 'centre' vers /action-center ; cette HIDDEN_PAGE reste pour search ⌘K avec les keywords historiques.",
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
    // Phase 1.C — P0.3 : libellé harmonisé en singulier "Centre d'action"
    // pour cohérence avec l'item panel Accueil + grammaire éditoriale Sol
    // §5. La route diffère intentionnellement de l'item panel (slide-over
    // peek transverse `?actionCenter=open` vs page dédiée `/action-center`)
    // — contextes d'usage distincts (raccourci power user vs navigation).
    key: 'centre-actions',
    label: "Centre d'action",
    icon: AlertTriangle,
    to: '/?actionCenter=open&tab=actions',
    shortcut: 'Ctrl+Shift+L',
    keywords: ['alertes', 'anomalies', 'actions', 'centre', 'notifications', 'inbox'],
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
