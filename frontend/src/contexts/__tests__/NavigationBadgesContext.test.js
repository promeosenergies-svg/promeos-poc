/**
 * PROMEOS — Source guards NavigationBadgesContext (Phase 2.B P1.2.bis).
 *
 * Pattern aligné sur expertMode.test.js, blocB_guards.test.js : lecture
 * du source + assertions structurelles. L'environnement de test est
 * node (pas jsdom) → pas de render React, on garantit la structure du
 * Provider et du hook par lecture statique.
 *
 * Couvre : Provider exporté, hook exporté, fetch initial, stale-while-
 * revalidate, retry counter, dégradation après seuil, TTL backend-driven,
 * garde-fou hook hors Provider, intégration App/Sidebar/AppShell/NavPanel.
 */

import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const CONTEXT_PATH = join(__dirname, '..', 'NavigationBadgesContext.jsx');
const SIDEBAR_PATH = join(__dirname, '..', '..', 'layout', 'Sidebar.jsx');
const APPSHELL_PATH = join(__dirname, '..', '..', 'layout', 'AppShell.jsx');
const NAVPANEL_PATH = join(__dirname, '..', '..', 'layout', 'NavPanel.jsx');
const APP_PATH = join(__dirname, '..', '..', 'App.jsx');
const NAV_API_PATH = join(__dirname, '..', '..', 'services', 'api', 'navigation.js');

const src = readFileSync(CONTEXT_PATH, 'utf-8');

// ── A. Module structure ──────────────────────────────────────────────────

describe('A. NavigationBadgesContext — module exports', () => {
  it('exporte NavigationBadgesProvider', () => {
    expect(src).toMatch(/export function NavigationBadgesProvider/);
  });

  it('exporte useNavigationBadges hook', () => {
    expect(src).toMatch(/export function useNavigationBadges/);
  });

  it('crée le Context via createContext (initialisé à null pour garde-fou)', () => {
    expect(src).toMatch(/createContext\(null\)/);
  });

  it('importe getNavigationBadges depuis services/api', () => {
    expect(src).toMatch(/from '\.\.\/services\/api'/);
    expect(src).toMatch(/getNavigationBadges/);
  });
});

// ── B. Stratégie fetch / polling ─────────────────────────────────────────

describe('B. NavigationBadgesContext — fetch & polling', () => {
  it('appelle getNavigationBadges au mount via useEffect', () => {
    expect(src).toMatch(/useEffect/);
    expect(src).toMatch(/fetchBadges\(\)/);
  });

  it('persiste cache_ttl_seconds dans une ref pour piloter le polling', () => {
    expect(src).toMatch(/ttlRef/);
    expect(src).toMatch(/data\?\.cache_ttl_seconds|data\.cache_ttl_seconds/);
  });

  it('utilise setTimeout récursif pour adopter le TTL courant', () => {
    expect(src).toMatch(/setTimeout/);
    expect(src).toMatch(/clearTimeout/);
  });

  it('default TTL = 60 s si payload ne fournit pas cache_ttl_seconds', () => {
    expect(src).toMatch(/DEFAULT_TTL_SECONDS\s*=\s*60/);
  });
});

// ── C. Stale-while-revalidate + retry ────────────────────────────────────

describe('C. NavigationBadgesContext — stale-while-revalidate', () => {
  it('garde la dernière valeur (prev.data) sur erreur', () => {
    expect(src).toMatch(/setState\(\(prev\)/);
    expect(src).toMatch(/data:\s*prev\.data/);
  });

  it('compte les échecs consécutifs via failureCountRef', () => {
    expect(src).toMatch(/failureCountRef/);
    expect(src).toMatch(/failureCountRef\.current\s*\+=\s*1/);
  });

  it("reset le compteur d'échecs après un fetch réussi", () => {
    expect(src).toMatch(/failureCountRef\.current\s*=\s*0/);
  });

  it('expose error seulement après 3 échecs consécutifs (mode dégradé)', () => {
    expect(src).toMatch(/MAX_RETRY_BEFORE_DEGRADED\s*=\s*3/);
    expect(src).toMatch(/failureCountRef\.current\s*>=\s*MAX_RETRY_BEFORE_DEGRADED/);
  });

  it('PAS de toast utilisateur sur erreur réseau (dégradation silencieuse)', () => {
    expect(src).not.toMatch(/toast\.error/);
    expect(src).not.toMatch(/showToast/);
    expect(src).not.toMatch(/window\.Notification\(/);
  });
});

// ── D. Garde-fou consommateur ────────────────────────────────────────────

describe('D. NavigationBadgesContext — guard hook hors Provider', () => {
  it('useNavigationBadges throws si Context null (hors Provider)', () => {
    expect(src).toMatch(/must be used within NavigationBadgesProvider/);
    expect(src).toMatch(/throw new Error/);
  });
});

// ── E. Intégration application ───────────────────────────────────────────

describe('E. NavigationBadgesProvider — wrapping App', () => {
  const app = readFileSync(APP_PATH, 'utf-8');

  it('App.jsx importe NavigationBadgesProvider', () => {
    expect(app).toMatch(/NavigationBadgesProvider/);
  });

  it('App.jsx ouvre et ferme le Provider autour des routes protégées', () => {
    expect(app).toMatch(/<NavigationBadgesProvider>/);
    expect(app).toMatch(/<\/NavigationBadgesProvider>/);
  });
});

// ── F. Sidebar — refacto fetch → hook ────────────────────────────────────

describe('F. Sidebar — consommation via useNavigationBadges', () => {
  const sidebar = readFileSync(SIDEBAR_PATH, 'utf-8');

  it('importe useNavigationBadges', () => {
    expect(sidebar).toMatch(/useNavigationBadges/);
  });

  it("ne fait plus d'appel direct getNotificationsSummary", () => {
    expect(sidebar).not.toMatch(/getNotificationsSummary\(\)/);
  });

  it("ne fait plus d'appel direct getMonitoringAlerts", () => {
    expect(sidebar).not.toMatch(/getMonitoringAlerts\(/);
  });

  it("ne fait plus d'appel direct getActionCenterActionsSummary", () => {
    expect(sidebar).not.toMatch(/getActionCenterActionsSummary\(\)/);
  });

  it("ne fait plus d'appel direct getActionCenterNotifications", () => {
    expect(sidebar).not.toMatch(/getActionCenterNotifications\(/);
  });

  it("ne fait plus d'appel à computeActionCenterBadge", () => {
    expect(sidebar).not.toMatch(/computeActionCenterBadge\(/);
  });

  it('expose les progress conformité dans badges (recâblage post-P0.4)', () => {
    expect(sidebar).toMatch(/conformiteDt/);
    expect(sidebar).toMatch(/conformiteBacs/);
    expect(sidebar).toMatch(/conformiteAper/);
  });
});

// ── G. AppShell — refacto fetch → hook ───────────────────────────────────

describe('G. AppShell — consommation via useNavigationBadges', () => {
  const shell = readFileSync(APPSHELL_PATH, 'utf-8');

  it('importe useNavigationBadges', () => {
    expect(shell).toMatch(/useNavigationBadges/);
  });

  it("ne fait plus d'appel direct getActionCenterActionsSummary", () => {
    expect(shell).not.toMatch(/getActionCenterActionsSummary\(/);
  });

  it("ne fait plus d'appel direct getActionCenterNotifications", () => {
    expect(shell).not.toMatch(/getActionCenterNotifications\(/);
  });

  it('ne fait plus appel à computeActionCenterBadge', () => {
    expect(shell).not.toMatch(/computeActionCenterBadge\(/);
  });
});

// ── H. NavPanel — recâblage progress conformité ──────────────────────────

describe('H. NavPanel — progress conformité recâblées (post-P0.4)', () => {
  const panel = readFileSync(NAVPANEL_PATH, 'utf-8');

  it('rend le bloc Progression obligations quand module Conformité actif', () => {
    expect(panel).toMatch(/Progression obligations/);
    expect(panel).toMatch(/activeModule\s*===\s*'conformite'/);
  });

  it('expose les 3 frameworks DT/BACS/APER avec barres', () => {
    expect(panel).toMatch(/'DT'/);
    expect(panel).toMatch(/'BACS'/);
    expect(panel).toMatch(/'APER'/);
  });

  it('lit conformiteDt/Bacs/Aper depuis prop badges (alimenté Context)', () => {
    expect(panel).toMatch(/badges\.conformiteDt/);
    expect(panel).toMatch(/badges\.conformiteBacs/);
    expect(panel).toMatch(/badges\.conformiteAper/);
  });

  it('a11y : role="progressbar" + aria-valuenow/min/max sur chaque barre', () => {
    expect(panel).toMatch(/role="progressbar"/);
    expect(panel).toMatch(/aria-valuenow/);
    expect(panel).toMatch(/aria-valuemin=\{0\}/);
    expect(panel).toMatch(/aria-valuemax=\{100\}/);
  });
});

// ── I. API service ────────────────────────────────────────────────────────

describe('I. services/api/navigation.js — endpoint wrapper', () => {
  const api = readFileSync(NAV_API_PATH, 'utf-8');

  it('exporte getNavigationBadges qui appelle /v1/navigation/badges (axios baseURL=/api)', () => {
    // Note : core.js axios baseURL='/api' → URL réelle dans le code = `/v1/navigation/badges`.
    // Bug double-prefix /api/api/v1/... fixé post-merge ccfb6420 (cf. events.js Phase 1.A).
    expect(api).toMatch(/export const getNavigationBadges/);
    expect(api).toMatch(/'\/v1\/navigation\/badges'/);
  });

  it("n'utilise PAS cachedGet (TTL piloté par le Context, pas par le cache GET)", () => {
    // Match l'appel ou l'import, pas la mention en commentaire/docstring.
    expect(api).not.toMatch(/cachedGet\(/);
    expect(api).not.toMatch(/import.*cachedGet/);
  });
});
