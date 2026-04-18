/**
 * PROMEOS — Sprint Achat post-ARENH MVP : CostSimulationCard source-guard.
 *
 * Couvre :
 *   - API service `getCostSimulation2026` cable (endpoint + year param)
 *   - fmtEur importe depuis utils/format (pas de helper local)
 *   - useScope() consomme (+ fallback scope.siteId)
 *   - 6 composantes rendues : fourniture / TURPE / VNU / capacité / CBAM / taxes
 *   - Wording doctrine : "Post-ARENH" present, pas de "ARENH" standalone
 *   - Delta vs 2024 conditionnel (badge emerald si negatif, red si positif)
 *   - data-testid="purchase-cost-simulation-card" racine stable Playwright
 *   - Distinction 404 (site sans simulation) vs 500 (indispo) dans error state
 */
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const componentsDir = join(__dirname, '..', 'components', 'purchase');
const servicesDir = join(__dirname, '..', 'services', 'api');

const cardSrc = readFileSync(join(componentsDir, 'CostSimulationCard.jsx'), 'utf-8');
const serviceSrc = readFileSync(join(servicesDir, 'purchase.js'), 'utf-8');

// ── API service ──────────────────────────────────────────────────────
describe('purchase.js — getCostSimulation2026', () => {
  it('expose getCostSimulation2026 avec siteId + year param', () => {
    expect(serviceSrc).toMatch(/export const getCostSimulation2026/);
    expect(serviceSrc).toMatch(/\/purchase\/cost-simulation\/\$\{siteId\}/);
    expect(serviceSrc).toMatch(/params:\s*\{\s*year\s*\}/);
  });

  it('default year = 2026 (post-ARENH)', () => {
    expect(serviceSrc).toMatch(/year\s*=\s*2026/);
  });

  it('utilise cachedGet (pattern des autres endpoints)', () => {
    expect(serviceSrc).toMatch(/cachedGet\(`\/purchase\/cost-simulation/);
  });
});

// ── Import & helpers partages ────────────────────────────────────────
describe('CostSimulationCard — imports partages', () => {
  it('consomme getCostSimulation2026 depuis services/api/purchase', () => {
    expect(cardSrc).toMatch(
      /import\s+\{\s*getCostSimulation2026\s*\}\s+from\s+['"]\.\.\/\.\.\/services\/api\/purchase['"]/
    );
  });

  it('utilise fmtEur de utils/format (pas de helper local)', () => {
    expect(cardSrc).toMatch(/import\s+\{\s*fmtEur\s*\}\s+from\s+['"]\.\.\/\.\.\/utils\/format['"]/);
    const codeOnly = cardSrc.replace(/\/\*[\s\S]*?\*\//g, '').replace(/\/\/.*$/gm, '');
    expect(codeOnly).not.toMatch(/function\s+fmtEuro\b/);
    expect(codeOnly).not.toMatch(/const\s+fmtEuro\s*=/);
  });

  it('utilise useNavigate + toSite (pattern achats)', () => {
    expect(cardSrc).toMatch(/useNavigate/);
    expect(cardSrc).toMatch(/toSite\(resolvedSiteId/);
  });
});

// ── Scope ────────────────────────────────────────────────────────────
describe('CostSimulationCard — scope', () => {
  it('consomme useScope() et fallback sur scope.siteId si prop absente', () => {
    expect(cardSrc).toMatch(/from\s+['"]\.\.\/\.\.\/contexts\/ScopeContext['"]/);
    expect(cardSrc).toMatch(/useScope\(\)/);
    expect(cardSrc).toMatch(/scope\?\.siteId/);
  });
});

// ── 6 composantes reglementaires ─────────────────────────────────────
describe('CostSimulationCard — 6 composantes rendues', () => {
  it('affiche la composante fourniture (blue-500)', () => {
    expect(cardSrc).toMatch(/fourniture_eur/);
    expect(cardSrc).toMatch(/bg-blue-500/);
  });

  it('affiche la composante TURPE (gray-500)', () => {
    expect(cardSrc).toMatch(/turpe_eur/);
    expect(cardSrc).toMatch(/TURPE 7/);
    expect(cardSrc).toMatch(/bg-gray-500/);
  });

  it('affiche la composante VNU avec gestion statut dormant/actif (amber-500)', () => {
    expect(cardSrc).toMatch(/vnu_eur/);
    expect(cardSrc).toMatch(/vnu_statut/);
    expect(cardSrc).toMatch(/bg-amber-500/);
    // Statut dormant rendu sans montant 0 (mot-clé "dormant")
    expect(cardSrc).toMatch(/dormant/);
  });

  it('affiche la composante capacité RTE (orange-500)', () => {
    expect(cardSrc).toMatch(/capacite_eur/);
    expect(cardSrc).toMatch(/Capacité RTE/);
    expect(cardSrc).toMatch(/bg-orange-500/);
  });

  it('affiche la composante CBAM (slate-400) avec "non applicable" si 0', () => {
    expect(cardSrc).toMatch(/cbam_scope/);
    expect(cardSrc).toMatch(/bg-slate-400/);
    expect(cardSrc).toMatch(/non applicable/);
  });

  it('affiche la composante Taxes (accise + CTA + TVA, indigo-400)', () => {
    expect(cardSrc).toMatch(/accise_cta_tva_eur/);
    expect(cardSrc).toMatch(/Taxes/);
    expect(cardSrc).toMatch(/bg-indigo-400/);
  });
});

// ── Wording doctrine ─────────────────────────────────────────────────
describe('CostSimulationCard — wording doctrine', () => {
  it('affiche "Post-ARENH" dans le JSX (badge header)', () => {
    expect(cardSrc).toMatch(/Post-ARENH/);
  });

  it('ne contient pas "ARENH" standalone sans prefixe "Post-" dans le JSX', () => {
    const codeOnly = cardSrc.replace(/\/\*[\s\S]*?\*\//g, '').replace(/\/\/.*$/gm, '');
    // Récupère tous les contenus entre > et < (texte JSX uniquement)
    const jsxText = [...codeOnly.matchAll(/>([^<>{}]+)</g)].map((m) => m[1]).join(' ');
    // Chaque occurrence d'ARENH doit être précédée de "post-" (casse insensible)
    // Lookbehind case-insensitive via flag i (supporte Post-ARENH et post-ARENH)
    const matches = jsxText.match(/(?<!post-)ARENH/gi);
    expect(matches).toBeNull();
  });

  it('zéro mention "flex" / "NEBCO" / "prix négatif" standalone côté client', () => {
    const codeOnly = cardSrc.replace(/\/\*[\s\S]*?\*\//g, '').replace(/\/\/.*$/gm, '');
    expect(codeOnly).not.toMatch(/>[^<]*NEBCO[^<]*</);
    expect(codeOnly).not.toMatch(/>[^<]*prix négatif[^<]*</i);
  });
});

// ── Delta vs 2024 conditionnel ───────────────────────────────────────
describe('CostSimulationCard — delta vs 2024 conditionnel', () => {
  it('consomme delta_vs_2024_pct du backend', () => {
    expect(cardSrc).toMatch(/delta_vs_2024_pct/);
  });

  it('badge emerald si delta négatif (économies) et red si positif (hausse)', () => {
    expect(cardSrc).toMatch(/bg-emerald-50/);
    expect(cardSrc).toMatch(/bg-red-50/);
    // Les deux branches doivent coexister sur le badge delta
    expect(cardSrc).toMatch(/deltaIsNegative/);
    expect(cardSrc).toMatch(/deltaIsPositive/);
  });

  it('badge delta porte un data-testid stable', () => {
    expect(cardSrc).toMatch(/data-testid=["']cost-sim-delta-badge["']/);
  });
});

// ── Alert VNU actif ──────────────────────────────────────────────────
describe('CostSimulationCard — alert VNU actif conditionnel', () => {
  it('bandeau amber si vnu_statut="actif" avec mention seuil CRE', () => {
    expect(cardSrc).toMatch(/vnuActif/);
    expect(cardSrc).toMatch(/vnu_seuil_active_eur_mwh/);
    expect(cardSrc).toMatch(/seuil CRE/);
    expect(cardSrc).toMatch(/data-testid=["']cost-sim-vnu-alert["']/);
  });
});

// ── Error states distincts 404 vs 500 ────────────────────────────────
describe('CostSimulationCard — error states 404 vs 500', () => {
  it('distingue 404 (site sans simulation) et 500/timeout (indispo)', () => {
    expect(cardSrc).toMatch(/errorCode/);
    expect(cardSrc).toMatch(/404/);
    expect(cardSrc).toMatch(/500/);
  });

  it('wording 404 : "Site sans simulation — contactez votre CSM"', () => {
    expect(cardSrc).toMatch(/Site sans simulation/);
    expect(cardSrc).toMatch(/CSM/);
  });

  it('wording 500 : "temporairement indisponible"', () => {
    expect(cardSrc).toMatch(/temporairement indisponible/);
  });
});

// ── Data-testid stability ────────────────────────────────────────────
describe('CostSimulationCard — data-testid stables Playwright', () => {
  it('data-testid racine "purchase-cost-simulation-card"', () => {
    expect(cardSrc).toMatch(/data-testid=["']purchase-cost-simulation-card["']/);
  });

  it('data-testid hero total + CTA scénarios', () => {
    expect(cardSrc).toMatch(/data-testid=["']cost-sim-total["']/);
    expect(cardSrc).toMatch(/data-testid=["']cost-sim-cta-scenarios["']/);
  });
});

// ── Accessibilité ────────────────────────────────────────────────────
describe('CostSimulationCard — accessibilité', () => {
  it('CTA porte un aria-label explicite', () => {
    expect(cardSrc).toMatch(/aria-label=["']Voir les scénarios/);
  });

  it('button type="button" (pas de submit involontaire)', () => {
    expect(cardSrc).toMatch(/type=["']button["']/);
  });
});
