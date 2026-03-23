/**
 * PROMEOS — CockpitHero — Source Guards + Structure Tests
 * Layout 4 cards : Score santé | Risque financier | Réduction DT | Actions en cours
 */
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const heroPath = join(__dirname, '..', 'pages', 'cockpit', 'CockpitHero.jsx');
const heroSrc = readFileSync(heroPath, 'utf-8');

// ── Source Guards (no-calc) ──────────────────────────────────────────

describe('CockpitHero — source guard (no-calc)', () => {
  it('ne contient aucun calcul de pourcentage (/ total * 100)', () => {
    expect(heroSrc).not.toMatch(/\/\s*total\s*\*\s*100/);
  });

  it('ne contient aucun calcul de reduction (1 - x/y * 100)', () => {
    expect(heroSrc).not.toMatch(/1\s*-\s*.*\/\s*.*\)\s*\*\s*100/);
  });

  it('ne contient pas de formule CO2 (* 0.0569)', () => {
    expect(heroSrc).not.toMatch(/\*\s*0\.0569/);
  });

  it('ne contient pas de formule risque hardcodee (* 7500 ou * 3750)', () => {
    expect(heroSrc).not.toMatch(/\*\s*7500/);
    expect(heroSrc).not.toMatch(/\*\s*3750/);
  });

  it('ne contient pas de calcul de score conformite', () => {
    expect(heroSrc).not.toMatch(/conformiteScore\s*=\s*Math/);
  });
});

// ── Design System ────────────────────────────────────────────────────

describe('CockpitHero — design system', () => {
  it('importe fmtEur pour les montants', () => {
    expect(heroSrc).toMatch(/import.*fmtEur/);
  });

  it('utilise fmtEur (pas de formatage EUR manuel)', () => {
    expect(heroSrc).not.toMatch(/toLocaleString.*EUR/);
  });

  it('importe Skeleton et ErrorState', () => {
    expect(heroSrc).toMatch(/Skeleton/);
    expect(heroSrc).toMatch(/ErrorState/);
  });
});

// ── Structure 4 cards ────────────────────────────────────────────────

describe('CockpitHero — structure 4 cards', () => {
  it('contient data-testid cockpit-hero', () => {
    expect(heroSrc).toContain('data-testid="cockpit-hero"');
  });

  it('contient data-testid gauge-conformite (card Score sante)', () => {
    expect(heroSrc).toContain('data-testid="gauge-conformite"');
  });

  it('contient data-testid kpi-risque (card Risque financier)', () => {
    expect(heroSrc).toContain('data-testid="kpi-risque"');
  });

  it('contient data-testid kpi-reduction-dt', () => {
    expect(heroSrc).toContain('data-testid="kpi-reduction-dt"');
  });

  it('contient data-testid kpi-actions-encours', () => {
    expect(heroSrc).toContain('data-testid="kpi-actions-encours"');
  });

  it('navigue vers /conformite au clic gauge', () => {
    expect(heroSrc).toMatch(/navigate\(['"]\/conformite['"]\)/);
  });

  it('utilise onEvidence callback', () => {
    expect(heroSrc).toMatch(/onEvidence/);
    expect(heroSrc).not.toMatch(/import.*EvidenceDrawer/);
  });

  it('accepte trajectoire en prop pour reductionPctActuelle', () => {
    expect(heroSrc).toMatch(/trajectoire\?\.reductionPctActuelle/);
  });

  it('affiche le label retard si reduction > objectif', () => {
    expect(heroSrc).toMatch(/isRetard/);
    expect(heroSrc).toMatch(/retard/);
  });
});

// ── Pondérations gauge ───────────────────────────────────────────────

describe('CockpitHero — ponderations gauge', () => {
  it('affiche DT 45%, BACS 30%, APER 25%', () => {
    expect(heroSrc).toMatch(/DT 45%/);
    expect(heroSrc).toMatch(/BACS 30%/);
    expect(heroSrc).toMatch(/APER 25%/);
  });

  it('ponderations sont des constantes (pas depuis API)', () => {
    expect(heroSrc).not.toMatch(/complianceMeta.*weights/);
  });
});

// ── Actions en cours card ────────────────────────────────────────────

describe('CockpitHero — card actions en cours', () => {
  it('affiche actions.enCours depuis les props', () => {
    expect(heroSrc).toMatch(/actions\?\.enCours/);
  });

  it('affiche actions.total', () => {
    expect(heroSrc).toMatch(/actions\?\.total/);
  });

  it('utilise fmtEur pour potentielEur', () => {
    expect(heroSrc).toMatch(/fmtEur\(actions\.potentielEur\)/);
  });
});

// ── Accessibilité ────────────────────────────────────────────────────

describe('CockpitHero — accessibilite', () => {
  it('a des aria-label sur les boutons interactifs', () => {
    expect(heroSrc).toMatch(/aria-label/);
  });

  it('a focus-visible:ring sur les elements interactifs', () => {
    expect(heroSrc).toMatch(/focus-visible:ring/);
  });
});
