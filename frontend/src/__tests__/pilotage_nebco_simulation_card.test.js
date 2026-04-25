/**
 * PROMEOS — Pilotage Vague 2 : NebcoSimulationCard source-guard.
 *
 * Couvre :
 *   - API service `getNebcoSimulation` cable + endpoint correct
 *   - useScope() consomme (+ fallback scope.siteId)
 *   - fmtEur importe depuis utils/format (pas de fmtEuro local)
 *   - 3 composantes (gain_spread / compensation / net) affichees
 *   - Wording doctrine : "gain simule" present, zero "NEBCO" visible client
 *   - data-testid racine stable pour Playwright
 *   - CTA navigate vers toSite(scope.siteId) fallback /sites
 *   - Intl.DateTimeFormat Europe/Paris pour la periode
 */
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const cardsDir = join(__dirname, '..', 'components', 'pilotage');
const servicesDir = join(__dirname, '..', 'services', 'api');

const cardSrc = readFileSync(join(cardsDir, 'NebcoSimulationCard.jsx'), 'utf-8');
const serviceSrc = readFileSync(join(servicesDir, 'pilotage.js'), 'utf-8');

// ── API service ──────────────────────────────────────────────────────
describe('pilotage.js — getNebcoSimulation', () => {
  it('expose getNebcoSimulation avec siteId + periodDays param', () => {
    expect(serviceSrc).toMatch(/export const getNebcoSimulation/);
    expect(serviceSrc).toMatch(/\/pilotage\/nebco-simulation\/\$\{siteId\}/);
    expect(serviceSrc).toMatch(/period_days/);
  });

  it('utilise cachedGet (pattern des autres endpoints Pilotage)', () => {
    expect(serviceSrc).toMatch(/cachedGet\(`\/pilotage\/nebco-simulation/);
  });
});

// ── Import & helpers partages ────────────────────────────────────────
describe('NebcoSimulationCard — imports partages', () => {
  it('consomme getNebcoSimulation depuis services/api/pilotage', () => {
    expect(cardSrc).toMatch(
      /import\s+\{\s*getNebcoSimulation\s*\}\s+from\s+['"]\.\.\/\.\.\/services\/api\/pilotage['"]/
    );
  });

  it('utilise fmtEur de utils/format (pas de fmtEuro local)', () => {
    expect(cardSrc).toMatch(/import\s+\{\s*fmtEur\s*\}\s+from\s+['"]\.\.\/\.\.\/utils\/format['"]/);
    // Pas de helper local concurrent
    const codeOnly = cardSrc.replace(/\/\*[\s\S]*?\*\//g, '').replace(/\/\/.*$/gm, '');
    expect(codeOnly).not.toMatch(/function\s+fmtEuro\b/);
    expect(codeOnly).not.toMatch(/const\s+fmtEuro\s*=/);
  });

  it('utilise useNavigate + toSite (pattern Sprint 1b)', () => {
    expect(cardSrc).toMatch(/useNavigate/);
    expect(cardSrc).toMatch(/toSite\(scope\.siteId\)/);
  });

  it('utilise Intl.DateTimeFormat avec timeZone Europe/Paris', () => {
    expect(cardSrc).toMatch(/new Intl\.DateTimeFormat/);
    expect(cardSrc).toMatch(/timeZone:\s*['"]Europe\/Paris['"]/);
  });
});

// ── Scope ────────────────────────────────────────────────────────────
describe('NebcoSimulationCard — scope', () => {
  it('consomme useScope() et fallback sur scope.siteId si prop absente', () => {
    expect(cardSrc).toMatch(/from\s+['"]\.\.\/\.\.\/contexts\/ScopeContext['"]/);
    expect(cardSrc).toMatch(/useScope\(\)/);
    expect(cardSrc).toMatch(/scope\?\.siteId/);
  });
});

// ── 3 composantes (doctrine data model) ──────────────────────────────
describe('NebcoSimulationCard — 3 composantes affichees', () => {
  it('affiche gain_spread_eur (amber)', () => {
    expect(cardSrc).toMatch(/gain_spread_eur/);
    expect(cardSrc).toMatch(/bg-amber-500/);
  });

  it('affiche compensation_fournisseur_eur (gris fonce)', () => {
    expect(cardSrc).toMatch(/compensation_fournisseur_eur/);
    expect(cardSrc).toMatch(/bg-gray-500/);
    // Tooltip doctrine : expliquer que c'est la part reversee au fournisseur
    expect(cardSrc).toMatch(/fournisseur d'énergie historique/);
  });

  it('affiche net_eur (emerald dominant)', () => {
    expect(cardSrc).toMatch(/net_eur/);
    expect(cardSrc).toMatch(/bg-emerald-500/);
  });
});

// ── Wording doctrine cote client ─────────────────────────────────────
describe('NebcoSimulationCard — wording doctrine', () => {
  it('affiche "gain simule" comme hero copy', () => {
    // Presence du wording oblige (insensible a la casse)
    expect(cardSrc.toLowerCase()).toMatch(/gain simulé/);
  });

  it('ne rend jamais "NEBCO" cote client (JSX)', () => {
    // Le terme peut rester dans les commentaires/docstrings (reference
    // technique interne), mais pas dans les noeuds JSX rendus.
    const codeOnly = cardSrc.replace(/\/\*[\s\S]*?\*\//g, '').replace(/\/\/.*$/gm, '');
    expect(codeOnly).not.toMatch(/>[^<]*NEBCO[^<]*</);
    expect(codeOnly).not.toMatch(/label=["'][^"']*NEBCO[^"']*["']/);
  });

  it('ne rend jamais "prix negatif" cote client', () => {
    // Note : "flex" reste tolere dans (a) classes Tailwind `flex/inline-flex`
    // et (b) la reference bibliographique "Barometre Flex 2026" (nom officiel
    // du rapport RTE/Enedis/GIMELEC). Le test anti-"flex" des autres cartes
    // est couvert par pilotage_cards_sprint1.test.js avec un scope plus serre.
    const codeOnly = cardSrc.replace(/\/\*[\s\S]*?\*\//g, '').replace(/\/\/.*$/gm, '');
    expect(codeOnly).not.toMatch(/>[^<]*prix négatif[^<]*</i);
  });

  it('ne rend pas "usages flexibles" (doctrine fix audit Vague 2)', () => {
    // L'audit post-merge a flag "usages flexibles" comme leak doctrine.
    // Wording canonique : "usages décalables" ou "usages pilotables".
    const codeOnly = cardSrc.replace(/\/\*[\s\S]*?\*\//g, '').replace(/\/\/.*$/gm, '');
    expect(codeOnly).not.toMatch(/usages flexibles/i);
    expect(cardSrc).toMatch(/usages (pilotables|décalables)/);
  });

  it('distingue 404 (CDC absente) vs 500/timeout (backend KO) dans error state', () => {
    // Fix P1 audit : un backend down affichait "CDC non seedée" faux.
    expect(cardSrc).toMatch(/err\?\.response\?\.status/);
    expect(cardSrc).toMatch(/cdc_missing/);
    expect(cardSrc).toMatch(/backend_error/);
    expect(cardSrc).toMatch(/Rejeu temporairement indisponible/);
  });

  it('affiche confiance en minuscules (doctrine Sprint 1b)', () => {
    // "confiance indicative" — pas "INDICATIVE" screaming caps
    expect(cardSrc).toMatch(/confiance \{confiance/);
  });
});

// ── Data-testid stables (Playwright) ─────────────────────────────────
describe('NebcoSimulationCard — data-testid stables', () => {
  it('porte data-testid="pilotage-nebco-card" sur la racine', () => {
    expect(cardSrc).toMatch(/data-testid=["']pilotage-nebco-card["']/);
  });

  it('expose un testid pour le hero big number + CTA', () => {
    expect(cardSrc).toMatch(/data-testid=["']pilotage-nebco-hero["']/);
    expect(cardSrc).toMatch(/data-testid=["']pilotage-nebco-cta["']/);
  });
});

// ── Integration Cockpit ──────────────────────────────────────────────
describe('Cockpit.jsx — integre NebcoSimulationCard', () => {
  it('importe et rend la carte dans la section Pilotage', () => {
    const cockpitSrc = readFileSync(join(__dirname, '..', 'pages', 'Cockpit.jsx'), 'utf-8');
    expect(cockpitSrc).toMatch(/import\s+NebcoSimulationCard/);
    expect(cockpitSrc).toMatch(/<NebcoSimulationCard\b/);
  });
});
