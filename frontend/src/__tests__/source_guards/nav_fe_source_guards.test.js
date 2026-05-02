/**
 * PROMEOS — Source guards FE nav (Phase 2.C — P1.3).
 *
 * Verrou anti-régression côté frontend après le sprint nav P0 + P1.2 +
 * P1.2.bis. Aucun calcul métier ne doit réapparaître dans les composants
 * nav (Sidebar, NavRail, NavPanel) ni dans le NavigationBadgesContext,
 * et aucun fetch direct vers /api/* ne doit être réintroduit hors du
 * Context (point d'entrée canonique).
 *
 * Doctrine §8.1 zero business logic FE + Phase 2.B P1.2.bis (TECH-badge-
 * context-dedup résolu : 1 seul fetch nav consolidé).
 *
 * Pattern repo : source-guard via readFileSync + regex (env=node, pas
 * testing-library).
 */

import { describe, it, expect } from 'vitest';
import { readFileSync, readdirSync, statSync } from 'fs';
import { dirname, join } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
// Remontée jusqu'à frontend/ : __tests__/source_guards/ → src/__tests__/source_guards/
// → src/ → frontend/. Un seul join racine évite les chemins fragiles.
const SRC_ROOT = join(__dirname, '..', '..');

// Fichiers nav surveillés. La liste est intentionnellement étroite —
// on ne couvre QUE les composants/contexts qui orchestrent le rail/panel.
// Les pages (Cockpit, Dashboard…) ont leur propres source-guards.
const NAV_FILES = [
  'layout/Sidebar.jsx',
  'layout/NavRail.jsx',
  'layout/NavPanel.jsx',
  'contexts/NavigationBadgesContext.jsx',
];

// Le Context est seul autorisé à fetcher /api/v1/navigation/badges —
// les autres composants doivent passer par useNavigationBadges().
const ALLOWED_API_FETCHERS = new Set(['contexts/NavigationBadgesContext.jsx']);

// Files qui ont le droit de consommer useNavigationBadges (whitelist
// intentionnelle — un nouveau consommateur doit être ajouté ici
// délibérément, pas par accident).
const ALLOWED_CONSUMERS = new Set([
  'layout/Sidebar.jsx',
  'layout/NavPanel.jsx', // panel rend les progress conformité
  'layout/AppShell.jsx', // cloche action center
  // Le Context lui-même définit le hook, ne le "consomme" pas.
]);

function readNavFile(relPath) {
  return readFileSync(join(SRC_ROOT, relPath), 'utf-8');
}

/**
 * Strip les lignes qui sont uniquement des commentaires (slash-slash et
 * asterisque-prefix dans un block JSDoc), pour ne pas matcher les
 * seuils ou références citées en commentaire (ex. PURCHASE_WINDOW_DAYS
 * = 90 documenté en commentaire d'un autre service).
 */
function stripComments(content) {
  return content
    .split('\n')
    .filter((line) => {
      const trimmed = line.trim();
      if (trimmed.startsWith('//')) return false;
      if (trimmed.startsWith('*') && !trimmed.startsWith('*/')) return false;
      if (trimmed.startsWith('/*') || trimmed.startsWith('*/')) return false;
      return true;
    })
    .join('\n');
}

/**
 * Récursivement collecte tous les .jsx/.js sous un répertoire (hors
 * dossiers de tests / node_modules / __pycache__).
 */
function collectSourceFiles(dir) {
  const files = [];
  for (const entry of readdirSync(dir)) {
    if (entry.startsWith('__') || entry === 'node_modules') continue;
    const full = join(dir, entry);
    const st = statSync(full);
    if (st.isDirectory()) {
      files.push(...collectSourceFiles(full));
    } else if (entry.endsWith('.jsx') || entry.endsWith('.js')) {
      files.push(full);
    }
  }
  return files;
}

// ── SG_NAV_FE_01 : pas de seuils métier dans les composants nav ─────────

describe('SG_NAV_FE_01 — no math thresholds in nav components', () => {
  // Constantes métier interdites dans les fichiers nav. Toute valeur ici
  // doit vivre dans une SoT canonique :
  //   - 7500     : seuil DT m² (regs.yaml)
  //   - 0.052    : facteur CO₂ électricité (config_emission_factors)
  //   - 0.227    : facteur CO₂ gaz
  //   - 0.0569   : ancien facteur CO₂ retiré (audit FE)
  //   - 1.9      : taux IPC fictif
  //   - 3750     : seuil €/m²/an
  //   - 5000     : seuil m² alternatif
  //   - 23600000 : kWh patrimoine
  //   - 2750000  : € patrimoine
  //   - 146      : kWh/m² PT 2030
  const FORBIDDEN_NUMBERS = [
    '7500',
    '0.052',
    '0.227',
    '0.0569',
    '3750',
    '5000',
    '23600000',
    '2750000',
    '146',
  ];

  for (const relPath of NAV_FILES) {
    it(`${relPath} ne contient aucun seuil métier hardcodé`, () => {
      const content = readNavFile(relPath);
      const stripped = stripComments(content);
      const violations = [];
      for (const num of FORBIDDEN_NUMBERS) {
        // Match littéral, mais pas dans des chaînes URL ou clés API.
        // Heuristique : on cherche le nombre entouré de bornes
        // non-alphanumériques (pas d'identifiant qui contient ce nombre).
        const re = new RegExp(`(?<![\\w.])${num.replace('.', '\\.')}(?![\\w])`);
        const lines = stripped.split('\n');
        lines.forEach((line, idx) => {
          if (re.test(line)) {
            violations.push(`L${idx + 1}: "${line.trim().slice(0, 80)}" contient ${num}`);
          }
        });
      }
      expect(violations, `Violations dans ${relPath}:\n  ${violations.join('\n  ')}`).toEqual([]);
    });
  }

  it('aucun fichier nav ne contient une formule CO₂ inline (* 0.0569 / * 0.052 / * 0.227)', () => {
    // Patterns explicites de formule métier — plus précis que la simple
    // présence du nombre. Rattrape un éventuel `kwh * 0.052` glissé dans
    // un useMemo ou un mapping inline.
    const PATTERNS = [/\*\s*0\.0569/, /\*\s*0\.052/, /\*\s*0\.227/];
    for (const relPath of NAV_FILES) {
      const content = readNavFile(relPath);
      const stripped = stripComments(content);
      for (const pattern of PATTERNS) {
        expect(stripped, `${relPath}: formule CO₂ inline détectée (${pattern})`).not.toMatch(
          pattern
        );
      }
    }
  });
});

// ── SG_NAV_FE_02 : pas de fetch direct /api/* hors Context ──────────────

describe('SG_NAV_FE_02 — no direct /api fetch outside NavigationBadgesContext', () => {
  // Patterns d'appels HTTP directs : fetch('/api/...'), axios.get('/api'),
  // les variantes apiClient/api.get/api.post, et les imports nominatifs
  // de services api/* qui pointent sur des endpoints nav.
  const FORBIDDEN_PATTERNS = [
    { name: 'fetch literal', re: /\bfetch\(\s*['"`]\/api\b/ },
    { name: 'axios method', re: /\baxios\.\w+\(\s*['"`]\/api\b/ },
    { name: 'apiClient method', re: /\bapiClient\.\w+\(\s*['"`]\/api\b/ },
    { name: 'api.get/post bare', re: /\bapi\.(get|post|put|patch|delete)\(\s*['"`]\/api\b/ },
  ];

  for (const relPath of NAV_FILES) {
    if (ALLOWED_API_FETCHERS.has(relPath)) {
      // Le Context EST autorisé — on ne lui interdit rien (il a sa propre
      // suite de tests fonctionnels NavigationBadgesContext.test.js).
      continue;
    }
    it(`${relPath} ne fait aucun fetch direct vers /api`, () => {
      const content = readNavFile(relPath);
      const stripped = stripComments(content);
      for (const { name, re } of FORBIDDEN_PATTERNS) {
        expect(
          stripped,
          `${relPath}: pattern "${name}" trouvé — passer par NavigationBadgesContext`
        ).not.toMatch(re);
      }
    });
  }

  it('NavigationBadgesContext.jsx EST le seul fichier nav à appeler getNavigationBadges', () => {
    // Garde-fou symétrique : si quelqu'un copie/colle l'appel ailleurs,
    // on perd la SoT. On vérifie l'unicité par scan large.
    const allFiles = collectSourceFiles(SRC_ROOT).map((f) => f.slice(SRC_ROOT.length + 1));
    const callers = allFiles.filter((f) => {
      const content = readFileSync(join(SRC_ROOT, f), 'utf-8');
      // Match l'appel `getNavigationBadges(` (pas la simple mention).
      return /\bgetNavigationBadges\(/.test(content);
    });
    // Autorisés : le Context (appelle), et accessoirement les tests
    // (mock du wrapper). Pas d'autre composant ne doit invoquer la
    // fonction directement — sinon le Context ne sert plus à rien.
    const unauthorized = callers.filter((f) => {
      if (f === 'contexts/NavigationBadgesContext.jsx') return false;
      if (f === 'services/api/navigation.js') return false; // définit la fn
      if (f.includes('__tests__')) return false; // tests mockent
      return true;
    });
    expect(
      unauthorized,
      `getNavigationBadges appelée hors Context :\n  ${unauthorized.join('\n  ')}`
    ).toEqual([]);
  });
});

// ── SG_NAV_FE_03 : whitelist consommateurs useNavigationBadges ──────────

describe('SG_NAV_FE_03 — useNavigationBadges consumed only by allowed components', () => {
  it('consommateurs de useNavigationBadges = whitelist explicite', () => {
    const allFiles = collectSourceFiles(SRC_ROOT).map((f) => f.slice(SRC_ROOT.length + 1));
    const consumers = allFiles.filter((f) => {
      // On ignore le fichier qui DÉFINIT le hook (pas un consommateur)
      if (f === 'contexts/NavigationBadgesContext.jsx') return false;
      if (f.includes('__tests__')) return false; // tests source-guards autorisés
      const content = readFileSync(join(SRC_ROOT, f), 'utf-8');
      return /\buseNavigationBadges\(/.test(content);
    });

    const unauthorized = consumers.filter((f) => !ALLOWED_CONSUMERS.has(f));
    expect(
      unauthorized,
      `useNavigationBadges consommée hors whitelist :\n  ${unauthorized.join('\n  ')}\n` +
        `Ajouter le fichier à ALLOWED_CONSUMERS si l'usage est intentionnel.`
    ).toEqual([]);
  });
});

// ── SG_NAV_FE_04 : HIDDEN_PAGES masquage justifié explicitement ─────────

describe('SG_NAV_FE_04 — HIDDEN_PAGES require documented `reason`', () => {
  // Phase 3.C — P1.6 : tout futur ajout HIDDEN_PAGES doit justifier
  // doctrinalement son masquage via le champ `reason`. Empêche le
  // pattern "caché par négligence" — chaque entrée doit pouvoir être
  // défendue à l'audit (audit Phase 0.bis §5 Q3 + livrable
  // docs/audits/navigation_panels_audit_20260502.md).

  it('chaque entrée HIDDEN_PAGES expose un champ `reason` non-vide', async () => {
    const { HIDDEN_PAGES } = await import('../../layout/NavRegistry');

    expect(Array.isArray(HIDDEN_PAGES), 'HIDDEN_PAGES doit être un tableau').toBe(true);
    expect(HIDDEN_PAGES.length, 'HIDDEN_PAGES ne doit pas être vide (à ce stade)').toBeGreaterThan(
      0
    );

    const violations = [];
    for (const page of HIDDEN_PAGES) {
      if (typeof page.reason !== 'string') {
        violations.push(
          `${page.to} (label "${page.label}") : champ \`reason\` absent ou non-string`
        );
        continue;
      }
      // Min 30 caractères pour forcer une justification réelle (pas
      // un placeholder type "TODO" / "n/a"). Encourage à pointer la
      // doctrine ou le sprint qui a décidé du masquage.
      if (page.reason.trim().length < 30) {
        violations.push(
          `${page.to} (label "${page.label}") : \`reason\` trop courte (${page.reason.trim().length} chars, minimum 30) — justifier doctrinalement`
        );
      }
    }

    expect(
      violations,
      `HIDDEN_PAGES non documentées :\n  ${violations.join('\n  ')}\n\n` +
        `Convention : chaque entrée HIDDEN_PAGES expose un champ \`reason\` (string, ≥ 30 chars) ` +
        `qui justifie pourquoi la page n'est pas exposée en panel rail. ` +
        `Catégories acceptées : doublon-sub-page, outil-interne, setup-technique, ` +
        `workflow-specialise, deep-link-only, doctrine-§N.N. ` +
        `Cf. NavRegistry.js:HIDDEN_PAGES docstring + audit Phase 0.bis Q3.`
    ).toEqual([]);
  });

  it('aucune entrée HIDDEN_PAGES ne contient un placeholder de raison (TODO, n/a, ...)', async () => {
    const { HIDDEN_PAGES } = await import('../../layout/NavRegistry');
    const FORBIDDEN_PLACEHOLDERS = [/^\s*todo\b/i, /^\s*n\/?a\b/i, /^\s*tbd\b/i, /^\s*\?\?\?/];

    const violations = [];
    for (const page of HIDDEN_PAGES) {
      const reason = (page.reason || '').trim();
      for (const pattern of FORBIDDEN_PLACEHOLDERS) {
        if (pattern.test(reason)) {
          violations.push(`${page.to} : placeholder "${reason.slice(0, 40)}" interdit`);
        }
      }
    }
    expect(violations, `Placeholders détectés :\n  ${violations.join('\n  ')}`).toEqual([]);
  });
});

// ── SG_NAV_FE_06 : tout UserRole couvert ou fallback documenté ──────────

describe('SG_NAV_FE_06 — UserRole coverage in ROLE_MODULE_ORDER', () => {
  // Phase 3.G — P5.0.1 (audit personas docs/audits/personas/personas_audit_20260502.md
  // §4 P0.1 + §5 R2.1) : garde-fou anti-régression couverture personas.
  // Tout UserRole défini backend doit avoir un ordre rail dédié OU être
  // explicitement listé en fallback intentionnel.
  //
  // Si une dérive silencieuse fait disparaître un persona ou en ajoute un
  // sans ordre dédié, ce test flag immédiatement avant qu'un user impacté
  // ne le découvre en prod.

  // Source de vérité côté backend : models/enums.py UserRole (11 rôles).
  // Cette liste est dupliquée ici intentionnellement — la cohérence est
  // vérifiée par un test backend dédié (test_user_role_nav_coverage).
  const ALL_USER_ROLES = [
    'dg_owner',
    'dsi_admin',
    'daf',
    'acheteur',
    'resp_conformite',
    'energy_manager',
    'resp_immobilier',
    'resp_site',
    'prestataire',
    'auditeur',
    'pmo_acc',
  ];

  // Fallback intentionnel = rôles documentés comme retombant sur `default`
  // par décision produit. Ajouter ici tout nouveau rôle qui DOIT rester
  // sur le fallback (ex: rôle technique sans nav métier dédiée).
  const ALLOWED_FALLBACKS = new Set([
    'dsi_admin', // power user, mode expert auto-on prévu (P1)
    'prestataire', // audit ponctuel mandat — fallback acceptable
    'pmo_acc', // pilotage ACC — fallback acceptable
  ]);

  it('tout UserRole défini doit avoir un ordre dédié ou être un fallback documenté', async () => {
    const navRegistrySrc = readFileSync(join(SRC_ROOT, 'layout', 'NavRegistry.js'), 'utf-8');

    const violations = [];
    for (const role of ALL_USER_ROLES) {
      // Cherche `role:` au début d'une ligne dans ROLE_MODULE_ORDER.
      const re = new RegExp(`^\\s+${role}:\\s*\\[`, 'm');
      const hasDedicatedOrder = re.test(navRegistrySrc);
      if (!hasDedicatedOrder && !ALLOWED_FALLBACKS.has(role)) {
        violations.push(
          `${role} : pas d'ordre dédié dans ROLE_MODULE_ORDER et pas dans ALLOWED_FALLBACKS`
        );
      }
    }
    expect(
      violations,
      `Personas non couverts :\n  ${violations.join('\n  ')}\n\n` +
        `Solutions : (a) ajouter un ordre dédié dans ROLE_MODULE_ORDER, ` +
        `OU (b) ajouter le rôle à ALLOWED_FALLBACKS dans ce test avec ` +
        `commentaire de justification.`
    ).toEqual([]);
  });

  it('aucun rôle dans ALLOWED_FALLBACKS ne doit avoir un ordre dédié (sinon retirer du fallback)', async () => {
    const navRegistrySrc = readFileSync(join(SRC_ROOT, 'layout', 'NavRegistry.js'), 'utf-8');
    const violations = [];
    for (const role of ALLOWED_FALLBACKS) {
      const re = new RegExp(`^\\s+${role}:\\s*\\[`, 'm');
      if (re.test(navRegistrySrc)) {
        violations.push(`${role} : a un ordre dédié — retirer de ALLOWED_FALLBACKS`);
      }
    }
    expect(violations).toEqual([]);
  });
});

// ── SG_NAV_FE_05 : NavRail ne mute pas l'output getOrderedModules ───────

describe('SG_NAV_FE_05 — NavRail must not mutate getOrderedModules output', () => {
  // Phase 3.D — P1.7 (audit Phase 0.ter recommandation §5) : verrou
  // statique anti-régression rendu rail. Si NavRail.jsx chaînait un
  // .sort/.reverse/.filter/.splice après getOrderedModules, l'ordre
  // ROLE_MODULE_ORDER serait silencieusement corrompu — les tests pure
  // logique resteraient verts mais le DOM divergerait.
  //
  // L'output de getOrderedModules est doctrine §11 source de vérité —
  // toute manipulation post-call doit passer par une extension de
  // ROLE_MODULE_ORDER (config-driven), pas par un patch inline.

  it('NavRail.jsx ne chaîne aucun mutateur sur getOrderedModules(...)', () => {
    const navRailPath = join(SRC_ROOT, 'layout', 'NavRail.jsx');
    const content = readFileSync(navRailPath, 'utf-8');
    const cleaned = stripComments(content);

    const FORBIDDEN_PATTERNS = [
      { name: '.sort()', re: /getOrderedModules\([^)]*\)\s*\.\s*sort\b/ },
      { name: '.reverse()', re: /getOrderedModules\([^)]*\)\s*\.\s*reverse\b/ },
      { name: '.filter()', re: /getOrderedModules\([^)]*\)\s*\.\s*filter\b/ },
      { name: '.splice()', re: /getOrderedModules\([^)]*\)\s*\.\s*splice\b/ },
    ];

    const violations = [];
    for (const { name, re } of FORBIDDEN_PATTERNS) {
      if (re.test(cleaned)) {
        violations.push(name);
      }
    }
    expect(
      violations,
      `NavRail.jsx mute l'output getOrderedModules via : ${violations.join(', ')}.\n` +
        `L'ordre retourné par ROLE_MODULE_ORDER doit être consommé as-is — ` +
        `toute manipulation doit passer par une extension de ROLE_MODULE_ORDER ` +
        `(config-driven, doctrine §11 + audit Phase 0.ter §5).`
    ).toEqual([]);
  });

  it('NavRail.jsx ne tri pas la variable visibleModules après assignation', () => {
    // Garde-fou symétrique : couvre `const x = getOrderedModules(...); x.sort(...)`
    // (pattern non-chainé). Heuristique simple : aucune des méthodes
    // mutables n'apparaît juste après le mot-clé visibleModules.
    const navRailPath = join(SRC_ROOT, 'layout', 'NavRail.jsx');
    const content = readFileSync(navRailPath, 'utf-8');
    const cleaned = stripComments(content);

    const FORBIDDEN_VAR_PATTERNS = [
      /visibleModules\.sort\(/,
      /visibleModules\.reverse\(/,
      /visibleModules\.splice\(/,
      // .filter peut être légitime (ex: filter expertOnly) — on tolère
      // mais on flag .sort/.reverse/.splice qui ne devraient jamais
      // appartenir au rendu rail.
    ];
    const violations = [];
    for (const re of FORBIDDEN_VAR_PATTERNS) {
      if (re.test(cleaned)) violations.push(re.source);
    }
    expect(
      violations,
      `NavRail.jsx contient un mutateur sur visibleModules :\n  ${violations.join('\n  ')}`
    ).toEqual([]);
  });
});
