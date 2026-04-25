/**
 * PROMEOS — CxDashboardPage source guards
 * Sprint CX 3 adoption réelle — P0.3
 *
 * Convention source-guard : assertions lexicales sur le source (readFileSync),
 * pas de React Testing Library. Vérifie que la page consomme bien les 3 endpoints
 * drivers, utilise Explain pour les termes techniques, et implémente le guard
 * admin (hasPermission / rôle plateforme).
 */
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { resolve } from 'path';

const pagePath = resolve(__dirname, '../CxDashboardPage.jsx');
const pageSrc = readFileSync(pagePath, 'utf-8');

const apiPath = resolve(__dirname, '../../../services/api/cxDashboard.js');
const apiSrc = readFileSync(apiPath, 'utf-8');

const glossaryPath = resolve(__dirname, '../../../ui/glossary.js');
const glossarySrc = readFileSync(glossaryPath, 'utf-8');

const appPath = resolve(__dirname, '../../../App.jsx');
const appSrc = readFileSync(appPath, 'utf-8');

// ── Service API : 4 endpoints CX dashboard ───────────────────────────────────

describe('CxDashboard API service', () => {
  it('exporte getCxDashboard, getT2V, getIAR, getWauMau', () => {
    expect(apiSrc).toMatch(/export\s+const\s+getCxDashboard\b/);
    expect(apiSrc).toMatch(/export\s+const\s+getT2V\b/);
    expect(apiSrc).toMatch(/export\s+const\s+getIAR\b/);
    expect(apiSrc).toMatch(/export\s+const\s+getWauMau\b/);
  });

  it('cible les 4 endpoints backend admin cx-dashboard', () => {
    expect(apiSrc).toContain("'/admin/cx-dashboard'");
    expect(apiSrc).toContain("'/admin/cx-dashboard/t2v'");
    expect(apiSrc).toContain("'/admin/cx-dashboard/iar'");
    expect(apiSrc).toContain("'/admin/cx-dashboard/wau-mau'");
  });

  it('utilise axios instance partagée (import api from ./core)', () => {
    expect(apiSrc).toMatch(/import\s+api\s+from\s+['"]\.\/core['"]/);
  });

  it('getT2V default days=180 et getIAR default days=30', () => {
    expect(apiSrc).toMatch(/getT2V\s*=\s*\(\s*days\s*=\s*180\s*\)/);
    expect(apiSrc).toMatch(/getIAR\s*=\s*\(\s*days\s*=\s*30\s*\)/);
  });
});

// ── Page : consommation des 3 drivers + tiles North-Star ─────────────────────

describe('CxDashboardPage — 3 drivers North-Star', () => {
  it('importe les 4 helpers API drivers', () => {
    expect(pageSrc).toMatch(/getCxDashboard/);
    expect(pageSrc).toMatch(/getT2V/);
    expect(pageSrc).toMatch(/getIAR/);
    expect(pageSrc).toMatch(/getWauMau/);
  });

  it('appelle les 3 endpoints drivers au montage (load callback)', () => {
    expect(pageSrc).toMatch(/getCxDashboard\s*\(/);
    expect(pageSrc).toMatch(/getT2V\s*\(/);
    expect(pageSrc).toMatch(/getIAR\s*\(/);
    expect(pageSrc).toMatch(/getWauMau\s*\(/);
  });

  it('affiche les 3 tiles North-Star (T2V / IAR / WAU/MAU)', () => {
    // Labels utilisés comme children de <Explain>
    expect(pageSrc).toMatch(/label=["']T2V \(p50\)["']/);
    expect(pageSrc).toMatch(/label=["']IAR["']/);
    expect(pageSrc).toMatch(/label=["']WAU\/MAU["']/);
  });

  it('affiche p50, p90 et p95 pour T2V', () => {
    expect(pageSrc).toMatch(/p50_days/);
    expect(pageSrc).toMatch(/p90_days/);
    expect(pageSrc).toMatch(/p95_days/);
  });

  it('gère l indicateur is_capped pour IAR (badge capped)', () => {
    expect(pageSrc).toMatch(/is_capped/);
    expect(pageSrc).toMatch(/capped/);
  });

  it('affiche l interpretation WAU/MAU (label textuel)', () => {
    expect(pageSrc).toMatch(/interpretation/);
    expect(pageSrc).toMatch(/wauInterp/);
  });

  it('applique seuils T2V couleurs (vert <7j, amber 7-14j, rouge >14j)', () => {
    // Fonction t2vTone existe avec les seuils 7 et 14
    expect(pageSrc).toMatch(/function\s+t2vTone/);
    expect(pageSrc).toMatch(/days\s*<\s*7/);
    expect(pageSrc).toMatch(/days\s*<=\s*14/);
  });
});

// ── Sections orgs (actives + inactives + breakdown) ──────────────────────────

describe('CxDashboardPage — sections orgs', () => {
  it('affiche top orgs actives et inactives (>10j)', () => {
    expect(pageSrc).toMatch(/topActiveOrgs/);
    expect(pageSrc).toMatch(/inactiveOrgs/);
    expect(pageSrc).toMatch(/inactive_orgs/);
  });

  it('affiche le breakdown par org (table T2V + IAR + events)', () => {
    expect(pageSrc).toMatch(/Breakdown par organisation/);
    expect(pageSrc).toMatch(/<Table>/);
    expect(pageSrc).toMatch(/byOrgEntries|by_org/);
  });
});

// ── Explain / glossary (labels techniques) ───────────────────────────────────

describe('CxDashboardPage — Explain & glossary', () => {
  it('utilise <Explain> pour les termes techniques T2V / IAR / WAU/MAU', () => {
    // Les tiles North-Star passent le term via prop explainTerm puis le composant
    // NorthStarTile rend <Explain term={explainTerm}>. Les 3 clés glossary doivent
    // être référencées dans le source (soit via <Explain term=...>, soit via
    // explainTerm="...").
    expect(pageSrc).toMatch(/(?:<Explain term|explainTerm)=["']t2v["']/);
    expect(pageSrc).toMatch(/(?:<Explain term|explainTerm)=["']iar["']/);
    expect(pageSrc).toMatch(/(?:<Explain term|explainTerm)=["']wau_mau["']/);
    // Et le composant <Explain term={explainTerm}> doit exister
    expect(pageSrc).toMatch(/<Explain term=\{explainTerm\}/);
  });

  it('termes t2v / iar / wau_mau présents dans glossary.js', () => {
    expect(glossarySrc).toMatch(/\bt2v:\s*\{/);
    expect(glossarySrc).toMatch(/\biar:\s*\{/);
    expect(glossarySrc).toMatch(/\bwau_mau:\s*\{/);
  });

  it('glossary T2V mentionne cible <7j', () => {
    // Cible métier North-Star
    expect(glossarySrc).toMatch(/T2V[\s\S]{0,500}<\s*7\s*j/);
  });
});

// ── Guard admin plateforme ───────────────────────────────────────────────────

describe('CxDashboardPage — admin guard', () => {
  it('utilise useAuth + hasPermission admin pour protéger la page', () => {
    expect(pageSrc).toMatch(/useAuth\s*\(/);
    expect(pageSrc).toMatch(/hasPermission\s*\(\s*['"]admin['"]\s*\)/);
  });

  it('affiche message accès réservé si !isAdmin', () => {
    expect(pageSrc).toMatch(/Accès réservé à l'administration plateforme/);
    expect(pageSrc).toMatch(/DG_OWNER\s+et\s+DSI_ADMIN/);
  });

  it('early return avant d appeler les endpoints si user non admin', () => {
    // Le guard retourne AVANT les useEffect/appels API
    expect(pageSrc).toMatch(/if\s*\(\s*!isAdmin\s*\)\s*\{[\s\S]*?return/);
  });
});

// ── Design system (PageShell + Card + Table + Skeleton) ──────────────────────

describe('CxDashboardPage — design system', () => {
  it('utilise PageShell comme convention du projet', () => {
    expect(pageSrc).toMatch(/<PageShell\b/);
    expect(pageSrc).toMatch(/from\s+['"]\.\.\/\.\.\/ui['"]/);
  });

  it('utilise Card / CardHeader / CardBody pour les sections', () => {
    expect(pageSrc).toMatch(/<Card>/);
    expect(pageSrc).toMatch(/<CardHeader>/);
    expect(pageSrc).toMatch(/<CardBody/);
  });

  it('utilise Skeleton pour l état de chargement', () => {
    expect(pageSrc).toMatch(/<Skeleton\b/);
  });

  it('utilise EmptyState pour les sections vides + guard', () => {
    expect(pageSrc).toMatch(/<EmptyState\b/);
  });

  it('utilise Table / Thead / Tbody / Th / Tr / Td pour le breakdown', () => {
    expect(pageSrc).toMatch(/<Table>/);
    expect(pageSrc).toMatch(/<Thead>/);
    expect(pageSrc).toMatch(/<Tbody>/);
    expect(pageSrc).toMatch(/<Th\b/);
    expect(pageSrc).toMatch(/<Tr\b/);
    expect(pageSrc).toMatch(/<Td\b/);
  });
});

// ── Routing — /admin/cx-dashboard câblé dans App.jsx ─────────────────────────

describe('CxDashboardPage — routing App.jsx', () => {
  it('App.jsx lazy-importe CxDashboardPage depuis ./pages/admin/CxDashboardPage', () => {
    expect(appSrc).toMatch(
      /lazy\s*\(\s*\(\)\s*=>\s*import\s*\(\s*['"]\.\/pages\/admin\/CxDashboardPage['"]\s*\)\s*\)/
    );
  });

  it('App.jsx monte la route /admin/cx-dashboard', () => {
    expect(appSrc).toMatch(/path=["']\/admin\/cx-dashboard["']/);
    expect(appSrc).toMatch(/<CxDashboardPage\s*\/>/);
  });
});

// ── Color-Life discipline (accent rouge uniquement si seuils dépassés) ───────

describe('CxDashboardPage — Color-Life discipline', () => {
  it('bg-red-* n est utilisé que via TONE_CLASS bad (seuils dépassés)', () => {
    // Aucune classe bg-red-* brute dans le JSX (seulement via TONE_CLASS.bad)
    // On autorise bg-red-50 dans TONE_CLASS object, mais pas ailleurs.
    const jsxBlocks = pageSrc.match(/className=["'`][^"'`]*bg-red-\d+[^"'`]*["'`]/g) || [];
    expect(jsxBlocks).toHaveLength(0);
  });

  it('fond neutre par défaut (bg-white / bg-gray-50) pour les tiles neutre', () => {
    expect(pageSrc).toMatch(/bg-white/);
  });
});
