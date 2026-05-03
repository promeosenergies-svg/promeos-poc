/**
 * PROMEOS — Source guards EventsContext (Phase 1.C Sprint α-fin).
 *
 * Pattern aligné NavigationBadgesContext.test.js : lecture du source +
 * assertions structurelles. Env de test = node, pas de render React —
 * on garantit la structure du Provider et du hook par lecture statique.
 *
 * Couvre : Provider exporté, hook bas-niveau exporté, fetch initial,
 * stale-while-revalidate, retry counter, dégradation après seuil, TTL
 * backend-driven, garde-fou hook hors Provider, AbortController cancel
 * race, params dynamiques (pageKey/persona/horizonDays), intégration
 * App.jsx + 2 pages cibles.
 */

import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const CONTEXT_PATH = join(__dirname, '..', 'EventsContext.jsx');
const HOOK_PATH = join(__dirname, '..', '..', 'hooks', 'useEvents.js');
const APP_PATH = join(__dirname, '..', '..', 'App.jsx');
const API_PATH = join(__dirname, '..', '..', 'services', 'api', 'events.js');
const CONFORMITE_PATH = join(__dirname, '..', '..', 'pages', 'ConformitePage.jsx');
const COMMAND_CENTER_PATH = join(__dirname, '..', '..', 'pages', 'CommandCenter.jsx');

const src = readFileSync(CONTEXT_PATH, 'utf-8');

// ── A. Module structure ──────────────────────────────────────────────────

describe('A. EventsContext — module exports', () => {
  it('exporte EventsProvider', () => {
    expect(src).toMatch(/export function EventsProvider/);
  });

  it('exporte useEventsContext (hook bas-niveau)', () => {
    expect(src).toMatch(/export function useEventsContext/);
  });

  it('crée le Context via createContext (initialisé à null pour garde-fou)', () => {
    expect(src).toMatch(/createContext\(null\)/);
  });

  it('importe getUpcomingEvents depuis services/api', () => {
    expect(src).toMatch(/from '\.\.\/services\/api'/);
    expect(src).toMatch(/getUpcomingEvents/);
  });
});

// ── B. Stratégie fetch / polling ─────────────────────────────────────────

describe('B. EventsContext — fetch & polling', () => {
  it('appelle fetchEvents au mount via useEffect', () => {
    expect(src).toMatch(/useEffect/);
    expect(src).toMatch(/fetchEvents\(currentParams\)/);
  });

  it('persiste cache_ttl_seconds dans une ref pour piloter le polling', () => {
    expect(src).toMatch(/ttlRef/);
    expect(src).toMatch(/data\?\.cache_ttl_seconds|data\.cache_ttl_seconds/);
  });

  it('utilise setTimeout récursif pour adopter le TTL courant', () => {
    expect(src).toMatch(/setTimeout/);
    expect(src).toMatch(/clearTimeout/);
  });

  it('default TTL = 300 s si payload ne fournit pas cache_ttl_seconds', () => {
    expect(src).toMatch(/DEFAULT_TTL_SECONDS\s*=\s*300/);
  });
});

// ── C. Stale-while-revalidate + retry ────────────────────────────────────

describe('C. EventsContext — stale-while-revalidate', () => {
  it('garde la dernière valeur (prev.data) sur erreur', () => {
    expect(src).toMatch(/setState\(\(prev\)/);
    expect(src).toMatch(/data:\s*prev\.data/);
  });

  it('compteur retry monotone (failureCountRef)', () => {
    expect(src).toMatch(/failureCountRef/);
    expect(src).toMatch(/failureCountRef\.current\s*\+=\s*1/);
    expect(src).toMatch(/failureCountRef\.current\s*=\s*0/);
  });

  it('bascule en mode dégradé après MAX_RETRY_BEFORE_DEGRADED', () => {
    expect(src).toMatch(/MAX_RETRY_BEFORE_DEGRADED\s*=\s*3/);
    expect(src).toMatch(/failureCountRef\.current\s*>=\s*MAX_RETRY_BEFORE_DEGRADED/);
  });
});

// ── D. AbortController cancel race (différence vs nav badges) ────────────

describe('D. EventsContext — AbortController anti-race', () => {
  it('crée un AbortController par fetch', () => {
    expect(src).toMatch(/new AbortController\(\)/);
  });

  it('abort le fetch précédent avant un nouveau (cancel race)', () => {
    expect(src).toMatch(/abortRef\.current\.abort\(\)/);
  });

  it('passe signal à getUpcomingEvents', () => {
    expect(src).toMatch(/signal:\s*controller\.signal/);
  });

  it('abort cleanup au unmount Provider', () => {
    expect(src).toMatch(/return\s*\(\s*\)\s*=>\s*\{[\s\S]*abortRef\.current\.abort/);
  });

  it('ignore les erreurs CanceledError (pas un échec retry)', () => {
    expect(src).toMatch(/CanceledError|ERR_CANCELED/);
  });
});

// ── E. Paramètres dynamiques pageKey / persona / horizonDays ────────────

describe('E. EventsContext — params dynamiques', () => {
  it('expose currentParams dans la value du Provider', () => {
    expect(src).toMatch(/currentParams/);
    expect(src).toMatch(/INITIAL_PARAMS\s*=\s*\{/);
  });

  it('refetch met à jour currentParams si différents', () => {
    expect(src).toMatch(/paramsEqual/);
    expect(src).toMatch(/setCurrentParams/);
  });

  it('useEffect dépend de pageKey / persona / horizonDays', () => {
    expect(src).toMatch(
      /currentParams\.pageKey,\s*currentParams\.persona,\s*currentParams\.horizonDays/
    );
  });
});

// ── F. Garde-fou hook hors Provider ──────────────────────────────────────

describe('F. EventsContext — garde-fou hook', () => {
  it('useEventsContext throw hors Provider', () => {
    expect(src).toMatch(/throw new Error.*useEvents must be used within EventsProvider/);
  });
});

// ── G. Hook canonique useEvents ──────────────────────────────────────────

describe('G. useEvents hook canonique', () => {
  const hookSrc = readFileSync(HOOK_PATH, 'utf-8');

  it('exporte useEvents depuis hooks/useEvents.js', () => {
    expect(hookSrc).toMatch(/export function useEvents/);
  });

  it('exporte ROLE_TO_PERSONA mapping pour tests/réutilisation', () => {
    expect(hookSrc).toMatch(/export\s*\{\s*ROLE_TO_PERSONA\s*\}/);
  });

  it('mapping role frontend → persona endpoint complet (4 personas core)', () => {
    expect(hookSrc).toMatch(/ENERGY_MANAGER:\s*'energy_manager'/);
    expect(hookSrc).toMatch(/DAF:\s*'daf'/);
    expect(hookSrc).toMatch(/ADMIN:\s*'admin'/);
    expect(hookSrc).toMatch(/OPERATOR:\s*'operator'/);
  });

  it('hook re-fetch sur changement pageKey ou persona via useEffect', () => {
    expect(hookSrc).toMatch(/useEffect/);
    expect(hookSrc).toMatch(/ctx\.refetch\(\{\s*pageKey,\s*persona:\s*resolvedPersona\s*\}\)/);
  });

  it('expose API plate (events / total / loading / error)', () => {
    expect(hookSrc).toMatch(/events:\s*ctx\.data\?\.events/);
    expect(hookSrc).toMatch(/total:\s*ctx\.data\?\.total/);
    expect(hookSrc).toMatch(/loading:\s*ctx\.loading/);
    expect(hookSrc).toMatch(/error:\s*ctx\.error/);
  });

  it('events fallback []  (anti-pattern §6.2 menus muets)', () => {
    expect(hookSrc).toMatch(/ctx\.data\?\.events\s*\?\?\s*\[\]/);
  });
});

// ── H. API wrapper ──────────────────────────────────────────────────────

describe('H. API wrapper events.js', () => {
  const apiSrc = readFileSync(API_PATH, 'utf-8');

  it('exporte getUpcomingEvents', () => {
    expect(apiSrc).toMatch(/export const getUpcomingEvents/);
  });

  it('appelle /v1/events/upcoming (axios baseURL=/api ajoute le prefix)', () => {
    // Note : core.js axios baseURL='/api' → events.js doit utiliser
    // `/v1/events/upcoming` (pas `/api/v1/...` qui causerait double prefix
    // /api/api/v1/...). Bug surfaced par smoke Playwright post-merge ccfb6420.
    // Strip docstrings + line comments pour éviter faux positifs sur le
    // commentaire explicatif du fix qui mentionne le bug pattern.
    const apiCode = apiSrc.replace(/\/\*[\s\S]*?\*\//g, '').replace(/\/\/.*$/gm, '');
    expect(apiCode).toMatch(/\/v1\/events\/upcoming/);
    // Anti-régression : pas de double prefix /api/v1/ dans le code (hors comments)
    expect(apiCode).not.toMatch(/\/api\/v1\/events\/upcoming/);
  });

  it('encode tous les query params optionnels', () => {
    expect(apiSrc).toMatch(/page_key/);
    expect(apiSrc).toMatch(/persona/);
    expect(apiSrc).toMatch(/horizon_days/);
    expect(apiSrc).toMatch(/cursor/);
    expect(apiSrc).toMatch(/limit/);
  });

  it('passe AbortSignal si fourni (cancel race)', () => {
    expect(apiSrc).toMatch(/signal/);
  });
});

// ── I. Intégration App.jsx + 2 pages cibles ──────────────────────────────

describe('I. Intégration App + pages', () => {
  it('App.jsx wrappe <EventsProvider> dans <NavigationBadgesProvider>', () => {
    const appSrc = readFileSync(APP_PATH, 'utf-8');
    expect(appSrc).toMatch(
      /import\s*\{\s*EventsProvider\s*\}\s*from\s*'\.\/contexts\/EventsContext'/
    );
    expect(appSrc).toMatch(/<EventsProvider>/);
    expect(appSrc).toMatch(/<\/EventsProvider>/);
  });

  it('ConformitePage importe useEvents + appel useEvents("conformite", role)', () => {
    const src = readFileSync(CONFORMITE_PATH, 'utf-8');
    expect(src).toMatch(/from\s*'\.\.\/hooks\/useEvents'/);
    expect(src).toMatch(/useEvents\(\s*'conformite'/);
  });

  it('CommandCenter importe useEvents + appel useEvents("cockpit_daily", role)', () => {
    const src = readFileSync(COMMAND_CENTER_PATH, 'utf-8');
    expect(src).toMatch(/from\s*'\.\.\/hooks\/useEvents'/);
    expect(src).toMatch(/useEvents\(\s*'cockpit_daily'/);
  });
});
