/**
 * Phase 14.A — source-guards CockpitDecision migration vers `usePageBriefing`.
 *
 * Audit Sol2 (29/04/2026 → 01/05/2026) : la page « Synthèse stratégique »
 * (`/cockpit/strategique`) rendait sa narrative en JSX inline et bypassait
 * tout le pipeline narrative_generator typology-aware (Phases 4 → 13.bis).
 * Conséquences observables sur la capture utilisateur :
 *   1. « Votre patrimoine de N sites » (Grand-Groupe) au lieu de
 *      « Votre parc tertiaire de N sites » (ETI_TERTIAIRE).
 *   2. « pour CODIR » inconditionnel dans le H1 (audit Marie banni hors GG).
 *   3. Sourcing §7 « (source X, confiance Y) » manquant.
 *   4. Closing forward-looking « à porter au prochain comité » (Phase 11.B)
 *      manquant.
 *   5. Archetype enrichi Phase 12.A (« 15 sites, 35 k m² ») partiel.
 *
 * Phase 14.A migre la page sur l'endpoint canonique
 * `/api/pages/cockpit_comex/briefing` via `usePageBriefing` + `<SolNarrative>`.
 * Ces source-guards verrouillent la migration : tout commit qui ressuscite
 * la narrative inline ou hardcode « pour CODIR » casse le test.
 */

import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

const __dirname = dirname(fileURLToPath(import.meta.url));
const SRC = readFileSync(join(__dirname, '..', 'pages', 'CockpitDecision.jsx'), 'utf-8');

describe('Phase 14.A — CockpitDecision migration vers usePageBriefing', () => {
  it('importe usePageBriefing depuis hooks/usePageBriefing', () => {
    expect(SRC).toMatch(
      /import\s+\{\s*usePageBriefing\s*\}\s+from\s+['"]\.\.\/hooks\/usePageBriefing['"]/
    );
  });

  it('importe SolNarrative depuis ui/sol/SolNarrative', () => {
    expect(SRC).toMatch(/import\s+SolNarrative\s+from\s+['"]\.\.\/ui\/sol\/SolNarrative['"]/);
  });

  it("appelle usePageBriefing('cockpit_comex', { persona: 'comex' })", () => {
    expect(SRC).toMatch(
      /usePageBriefing\(\s*['"]cockpit_comex['"]\s*,\s*\{\s*persona:\s*['"]comex['"]/
    );
  });

  it('rend <SolNarrative> avec primaryPush + primaryTrigger + typology cascadés', () => {
    // Vérifie que la page cascade les payloads structurés Phase 4.0.B au
    // composant Sol (non plus inline).
    expect(SRC).toMatch(
      /<SolNarrative[\s\S]*?primaryPush=\{briefing\?\.primaryPush\}[\s\S]*?primaryTrigger=\{briefing\?\.primaryTrigger\}[\s\S]*?typology=\{briefing\?\.typology\}/
    );
  });

  it('ne déclare plus de fonction StrategicNarrative inline', () => {
    // Phase 14.A — la fonction inline `StrategicNarrative({ facts })` qui
    // composait la narrative côté frontend (« Votre patrimoine de … ») a
    // été supprimée au profit de `<SolNarrative>` consommant le briefing.
    expect(SRC).not.toMatch(/function\s+StrategicNarrative\s*\(/);
  });

  it("ne hardcode plus 'Votre patrimoine de' inline (Phase 9.B/13.bis ETI)", () => {
    // Le builder backend choisit le bon descriptor par typology
    // (parc tertiaire / patrimoine / portefeuille). Aucune occurrence ne
    // doit subsister côté frontend.
    expect(SRC).not.toContain('Votre patrimoine de');
  });

  it("ne hardcode plus '· pour CODIR' inconditionnel dans le H1", () => {
    // Le suffix « · pour CODIR » doit être conditionnel sur typology=
    // 'grand_groupe_tertiaire'. Tout littéral inconditionnel implique
    // une régression de l'audit Marie (audit ETI tertiaire avril 2026).
    expect(SRC).toMatch(/typology\s*===\s*['"]grand_groupe_tertiaire['"]/);
    expect(SRC).toMatch(/typology[\s\S]{0,80}\?\s*['"][\s·]+pour CODIR['"]/);
  });
});
