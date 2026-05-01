/**
 * Phase 26.bis (hot-fix UX 2026-05-01) — tooltips natifs sur ConsoSevenDaysBars.
 *
 * Avant : le SVG `Conso 7 jours` rendait 7 <rect> hardcodés sans aucun
 * tooltip au hover (signalé par utilisateur 2026-05-01).
 * Après : chaque barre a un <title> natif SVG avec libellé jour + valeur MWh
 * + contexte (anomalie ou confiance faible).
 */
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { resolve } from 'path';

const SRC = readFileSync(resolve(__dirname, '../pages/CockpitPilotage.jsx'), 'utf-8');

describe('Phase 26.bis — Conso 7 jours tooltips', () => {
  it('expose un array de 7 jours nommés (pas 5 lettres anonymes)', () => {
    expect(SRC).toMatch(/_CONSO_7D_DAYS/);
    // 7 noms de jours complets attendus
    for (const day of ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche']) {
      expect(SRC).toMatch(new RegExp(`label:\\s*['"]${day}['"]`));
    }
  });

  it('chaque rect rendu inclut un <title> natif avec MWh', () => {
    // Pattern : <title>{tooltipText}</title> à l'intérieur du map
    expect(SRC).toMatch(/<title>\{tooltipText\}<\/title>/);
    // Tooltip text mentionne MWh
    expect(SRC).toMatch(/['"`].*MWh.*['"`]/);
  });

  it('mention spéciale anomalie + confiance faible dans le tooltip', () => {
    expect(SRC).toMatch(/anomalie\s*\+/);
    expect(SRC).toMatch(/confiance faible/);
  });

  it('le sous-titre invite à survoler les barres pour le détail', () => {
    expect(SRC).toMatch(/[Ss]urvolez/);
  });

  it('les hauteurs SVG des 7 barres sont préservées (pas de régression visuelle)', () => {
    // Le visuel V1 doit rester 1:1 — on vérifie que les 7 paires (y, h)
    // historiques sont toutes présentes dans le code (via _CONSO_7D_DAYS).
    const expectedYH = [
      ['48', '55'], // L
      ['50', '53'], // M
      ['44', '59'], // M
      ['46', '57'], // J
      ['49', '54'], // V
      ['22', '81'], // S anomalie
      ['55', '48'], // D faded
    ];
    for (const [y, h] of expectedYH) {
      const re = new RegExp(`y:\\s*${y}\\s*,\\s*h:\\s*${h}`);
      expect(SRC).toMatch(re);
    }
  });
});
