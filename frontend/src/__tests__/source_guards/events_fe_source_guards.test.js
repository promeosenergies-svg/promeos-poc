/**
 * PROMEOS — Source guards FE events (Phase 1.C Sprint α-fin).
 *
 * Verrou anti-régression côté frontend après l'intégration du Context
 * EventsProvider + hook useEvents. Aucun fetch direct vers
 * /api/v1/events ne doit être réintroduit hors du Context, et la
 * frontière `events_query_service` (backend) ↔ EventsContext (FE) doit
 * rester intacte.
 *
 * Doctrine §8.1 zero business logic FE + Phase 1.A endpoint REST canonique.
 *
 * Pattern repo : source-guard via readFileSync + regex (env=node, pas
 * testing-library), aligné nav_fe_source_guards.test.js.
 */

import { describe, it, expect } from 'vitest';
import { readFileSync, readdirSync, statSync } from 'fs';
import { dirname, join } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const SRC_ROOT = join(__dirname, '..', '..');

// Whitelist des fichiers autorisés à appeler getUpcomingEvents
// directement (sans passer par useEvents). Sinon : violation §8.1.
const GET_UPCOMING_DIRECT_WHITELIST = new Set([
  join(SRC_ROOT, 'contexts', 'EventsContext.jsx'),
  join(SRC_ROOT, 'services', 'api', 'events.js'), // l'export lui-même
  join(SRC_ROOT, 'services', 'api', 'index.js'), // re-export
]);

// Whitelist des fichiers autorisés à utiliser useEvents
// (hors hook lui-même). À étendre lors d'ajouts de pages cibles.
const USE_EVENTS_WHITELIST = new Set([
  join(SRC_ROOT, 'hooks', 'useEvents.js'), // l'export
  join(SRC_ROOT, 'pages', 'ConformitePage.jsx'),
  join(SRC_ROOT, 'pages', 'CommandCenter.jsx'),
]);

function walk(dir, exclude = ['node_modules', '__tests__', '__pycache__', 'dist']) {
  const out = [];
  for (const entry of readdirSync(dir)) {
    if (exclude.includes(entry)) continue;
    const full = join(dir, entry);
    const st = statSync(full);
    if (st.isDirectory()) out.push(...walk(full, exclude));
    else if (full.endsWith('.js') || full.endsWith('.jsx')) out.push(full);
  }
  return out;
}

const allFiles = walk(SRC_ROOT);

// ── SG_EVENTS_FE_01 ─────────────────────────────────────────────────────

// Strip comments helper (block + line). Évite faux positifs sur les
// docstrings explicatives qui mentionnent l'endpoint canonique.
function stripComments(src) {
  return src.replace(/\/\*[\s\S]*?\*\//g, '').replace(/\/\/.*$/gm, '');
}

describe('SG_EVENTS_FE_01 — fetch /api/v1/events/upcoming uniquement via Context', () => {
  it('aucun fetch direct vers /api/v1/events hors EventsContext + api/events', () => {
    const violations = [];
    const FORBIDDEN = /\/api\/v1\/events\/upcoming/;
    for (const file of allFiles) {
      if (GET_UPCOMING_DIRECT_WHITELIST.has(file)) continue;
      const cleaned = stripComments(readFileSync(file, 'utf-8'));
      if (FORBIDDEN.test(cleaned)) {
        violations.push(file);
      }
    }
    expect(violations).toEqual([]);
  });

  it('aucun import direct de getUpcomingEvents hors whitelist', () => {
    const violations = [];
    const PATTERN = /\bgetUpcomingEvents\b/;
    for (const file of allFiles) {
      if (GET_UPCOMING_DIRECT_WHITELIST.has(file)) continue;
      const cleaned = stripComments(readFileSync(file, 'utf-8'));
      if (PATTERN.test(cleaned)) {
        violations.push(file);
      }
    }
    expect(violations).toEqual([]);
  });
});

// ── SG_EVENTS_FE_02 ─────────────────────────────────────────────────────

describe('SG_EVENTS_FE_02 — useEvents whitelist consommateurs', () => {
  it('useEvents importé uniquement par les pages whitelistées', () => {
    const violations = [];
    const PATTERN = /from\s*['"][^'"]*\/hooks\/useEvents['"]/;
    for (const file of allFiles) {
      if (USE_EVENTS_WHITELIST.has(file)) continue;
      const src = readFileSync(file, 'utf-8');
      if (PATTERN.test(src)) {
        violations.push(file);
      }
    }
    expect(violations).toEqual([]);
  });
});

// ── SG_EVENTS_FE_03 ─────────────────────────────────────────────────────

describe('SG_EVENTS_FE_03 — pas de seuils métier hardcodés', () => {
  it('EventsContext.jsx ne contient pas de constantes physiques inline', () => {
    const ctxPath = join(SRC_ROOT, 'contexts', 'EventsContext.jsx');
    const src = readFileSync(ctxPath, 'utf-8');
    // Sentinelles connues : prix énergie, seuils CO₂, accise
    const FORBIDDEN_VALUES = ['7500', '0.052', '0.227', '0.02658', '0.068', '8.50'];
    for (const value of FORBIDDEN_VALUES) {
      expect(src).not.toMatch(new RegExp(`\\b${value.replace('.', '\\.')}\\b`));
    }
  });

  it('useEvents.js ne contient pas de constantes physiques inline', () => {
    const hookPath = join(SRC_ROOT, 'hooks', 'useEvents.js');
    const src = readFileSync(hookPath, 'utf-8');
    const FORBIDDEN_VALUES = ['7500', '0.052', '0.227', '0.02658', '0.068', '8.50'];
    for (const value of FORBIDDEN_VALUES) {
      expect(src).not.toMatch(new RegExp(`\\b${value.replace('.', '\\.')}\\b`));
    }
  });
});

// ── SG_EVENTS_FE_04 ─────────────────────────────────────────────────────

describe('SG_EVENTS_FE_04 — Provider unique (pas de duplication)', () => {
  it('EventsProvider défini une seule fois dans contexts/', () => {
    const violations = [];
    const PATTERN = /export\s+function\s+EventsProvider/;
    for (const file of allFiles) {
      const src = readFileSync(file, 'utf-8');
      if (PATTERN.test(src)) {
        violations.push(file);
      }
    }
    expect(violations.length).toBe(1);
    expect(violations[0]).toContain('EventsContext.jsx');
  });

  it('EventsProvider référencé par App.jsx dans la chaîne Provider', () => {
    const appPath = join(SRC_ROOT, 'App.jsx');
    const src = readFileSync(appPath, 'utf-8');
    expect(src).toMatch(/<EventsProvider>/);
    expect(src).toMatch(/<\/EventsProvider>/);
  });
});

// ── SG_EVENTS_FE_05 ─────────────────────────────────────────────────────

describe('SG_EVENTS_FE_05 — buildWatchlist forbidden (use useEvents instead)', () => {
  // Les SG eux-mêmes peuvent mentionner les noms interdits dans leur
  // propre logique de garde-fou (auto-référence). Tolérance whitelist :
  const SG_SELF_REFERENCE_WHITELIST = new Set([
    join(SRC_ROOT, '__tests__', 'source_guards', 'events_fe_source_guards.test.js'),
    join(SRC_ROOT, '__tests__', 'source_guards', 'nav_fe_source_guards.test.js'),
  ]);

  it('aucun fichier frontend ne référence buildWatchlist / computeWatchlist / generateWatchlist', () => {
    const FORBIDDEN_PATTERNS = ['buildWatchlist', 'computeWatchlist', 'generateWatchlist'];
    const violations = [];

    for (const file of allFiles) {
      if (SG_SELF_REFERENCE_WHITELIST.has(file)) continue;
      const src = readFileSync(file, 'utf-8');
      // Strip line comments + block comments pour éviter faux positifs
      // (les commentaires explicatifs Phase 1.D peuvent légitimement
      // mentionner l'ancienne fonction supprimée).
      const cleaned = src.replace(/\/\*[\s\S]*?\*\//g, '').replace(/\/\/.*$/gm, '');

      for (const pattern of FORBIDDEN_PATTERNS) {
        if (cleaned.includes(pattern)) {
          violations.push(`${file} → "${pattern}"`);
        }
      }
    }

    expect(violations).toEqual([]);
  });

  it('useEvents whitelist contient ConformitePage et CommandCenter (pages cibles Phase 1.C/1.D)', () => {
    // Vérifie que ces pages utilisent bien useEvents en remplacement
    // des appels buildWatchlist supprimés.
    const conformitePath = join(SRC_ROOT, 'pages', 'ConformitePage.jsx');
    const commandCenterPath = join(SRC_ROOT, 'pages', 'CommandCenter.jsx');

    const conformiteSrc = readFileSync(conformitePath, 'utf-8');
    const commandCenterSrc = readFileSync(commandCenterPath, 'utf-8');

    expect(conformiteSrc).toMatch(/from\s*['"][^'"]*\/hooks\/useEvents['"]/);
    expect(conformiteSrc).toMatch(/useEvents\(\s*['"]conformite['"]/);

    expect(commandCenterSrc).toMatch(/from\s*['"][^'"]*\/hooks\/useEvents['"]/);
    expect(commandCenterSrc).toMatch(/useEvents\(\s*['"]cockpit_daily['"]/);
  });

  it("aucun fichier dans pages/cockpit/ ne s'appelle WatchlistCard.jsx (orphelin supprimé)", () => {
    // Garde-fou contre une réintroduction du composant orphelin.
    const cockpitDir = join(SRC_ROOT, 'pages', 'cockpit');
    const files = readdirSync(cockpitDir);
    expect(files).not.toContain('WatchlistCard.jsx');
  });
});
