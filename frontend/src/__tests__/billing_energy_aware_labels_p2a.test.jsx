/**
 * PROMEOS — Bill Intelligence P2-A (2026-05-24) :
 * Source-guard FE : InsightDrawer.getBreakdownRows() doit produire des labels
 * ÉNERGIE-AWARE distincts (élec = TURPE, gaz = ATRD+ATRT).
 *
 * Bug racine signalé par user en P1 + persistant en P2-A pour le drawer :
 * une facture GAZ ne doit JAMAIS afficher "Réseau (TURPE)" — doctrinalement
 * impossible (TURPE = élec uniquement, CRE 2025-78). Pour le gaz, le label
 * réseau doit être "Acheminement (ATRD + ATRT)".
 */
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { resolve } from 'path';

const SRC = resolve(__dirname, '..');
const INSIGHT_DRAWER = readFileSync(resolve(SRC, 'components/InsightDrawer.jsx'), 'utf-8');

describe('Bill Intelligence P2-A — labels énergie-aware (InsightDrawer)', () => {
  it('getBreakdownRows : label réseau gaz contient ATRD + ATRT (pas TURPE)', () => {
    // Extrait la fonction getBreakdownRows (corps complet)
    const match = INSIGHT_DRAWER.match(/function getBreakdownRows\(energyType\)[\s\S]*?\n\}/);
    expect(match, 'getBreakdownRows doit être défini').not.toBeNull();
    const body = match[0];

    // Doit contenir un chemin pour GAZ avec ATRD + ATRT
    expect(body).toMatch(/Acheminement.*ATRD.*ATRT/);
    expect(body).toMatch(/TICGN/);

    // Doit conserver TURPE pour ELEC seulement
    expect(body).toMatch(/Réseau.*TURPE/);
    expect(body).toMatch(/CSPE\/TICFE/);

    // GAZ branche ne doit JAMAIS mentionner TURPE comme label
    // (on cherche la branche conditionnelle gaz et on vérifie l'absence)
    const gazBranchMatch = body.match(/const reseauLabel = isGaz \? \(([\s\S]*?)\) :/);
    expect(gazBranchMatch, 'Branche gaz reseauLabel doit exister').not.toBeNull();
    const gazBranch = gazBranchMatch[1];
    expect(gazBranch).not.toContain('TURPE');
  });

  it('CAUSE_LABELS.reseau_mismatch : wording énergie-aware (ATRD/ATRT pour gaz)', () => {
    // Vérifie le wording dynamique du cause label réseau
    const causeMatch = INSIGHT_DRAWER.match(
      /reseau_mismatch:\s*\(m\)\s*=>\s*\{[\s\S]*?const isGaz[\s\S]*?\},/
    );
    expect(
      causeMatch,
      'cause label reseau_mismatch doit être une fonction énergie-aware'
    ).not.toBeNull();
    expect(causeMatch[0]).toContain('ATRD');
    expect(causeMatch[0]).toContain('ATRT');
    expect(causeMatch[0]).toContain('isGaz');
  });

  it("Pas de chaîne fixe 'Réseau (TURPE)' dans InsightDrawer côté hardcoded", () => {
    // Doctrine : aucun label "Réseau (TURPE)" hardcodé en dehors de la
    // branche conditionnelle (énergie === ELEC). Le seul match autorisé est
    // dans une expression ternaire / branche conditionnelle.
    const occurrences = [...INSIGHT_DRAWER.matchAll(/Réseau\s*\(/g)];
    occurrences.forEach((m) => {
      const ctx = INSIGHT_DRAWER.substring(Math.max(0, m.index - 100), m.index + 50);
      // Chaque occurrence doit être dans une branche conditionnelle (ternaire ou if).
      // Tolérance : on accepte si le code contient "isGaz" dans les 200 chars précédents.
      const broaderCtx = INSIGHT_DRAWER.substring(Math.max(0, m.index - 300), m.index + 50);
      expect(broaderCtx).toMatch(/isGaz|energyType|energy_type|et === ['"]ELEC/i);
    });
  });
});
