/**
 * PROMEOS — Pilotage V1 Sprint 1 P0 UX — Source Guards.
 *
 * Couvre :
 *   - Wording doctrine : zero "NEBCO" cote client
 *   - Scope switcher : useScope() cable sur les 2 cartes concernees
 *   - CTA present sur les 3 cartes
 *   - RadarPrixNegatifsCard utilise Intl.DateTimeFormat avec timeZone Europe/Paris
 */
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const cardsDir = join(__dirname, '..', 'components', 'pilotage');

const radarSrc = readFileSync(join(cardsDir, 'RadarPrixNegatifsCard.jsx'), 'utf-8');
const roiSrc = readFileSync(join(cardsDir, 'RoiFlexReadyCard.jsx'), 'utf-8');
const portefeuilleSrc = readFileSync(join(cardsDir, 'PortefeuilleScoringCard.jsx'), 'utf-8');

// ── Doctrine wording (fix #3 audit) ──────────────────────────────────
describe('Pilotage cards — wording doctrine', () => {
  it('RoiFlexReadyCard ne doit pas afficher "NEBCO" cote client', () => {
    // Le terme peut rester dans les commentaires/docstrings (reference
    // technique interne), mais pas dans les JSX rendus.
    const codeOnly = roiSrc.replace(/\/\*[\s\S]*?\*\//g, '').replace(/\/\/.*$/gm, '');
    expect(codeOnly).not.toMatch(/>[^<]*NEBCO[^<]*</);
    expect(codeOnly).not.toMatch(/label=["'][^"']*NEBCO[^"']*["']/);
  });

  it('RoiFlexReadyCard utilise "Effacement rémunéré" pour la composante decalage', () => {
    expect(roiSrc).toMatch(/Effacement rémunéré/);
  });

  it('RadarPrixNegatifsCard ne doit pas dire "prix negatif" cote client', () => {
    const codeOnly = radarSrc.replace(/\/\*[\s\S]*?\*\//g, '').replace(/\/\/.*$/gm, '');
    expect(codeOnly).not.toMatch(/>[^<]*prix négatif[^<]*</i);
  });
});

// ── Scope switcher (fix #1 audit) ────────────────────────────────────
describe('Pilotage cards — scope switcher', () => {
  it('RoiFlexReadyCard utilise useScope (plus de hardcode site)', () => {
    expect(roiSrc).toMatch(/from\s+['"]\.\.\/\.\.\/contexts\/ScopeContext['"]/);
    expect(roiSrc).toMatch(/useScope\(\)/);
    // scope.siteId prioritaire sur le fallback demo
    expect(roiSrc).toMatch(/scope\?\.siteId/);
  });

  it('PortefeuilleScoringCard re-fetch au changement de scope', () => {
    expect(portefeuilleSrc).toMatch(/useScope\(\)/);
    // useEffect doit avoir une dependance qui change au switch d'org/portefeuille
    expect(portefeuilleSrc).toMatch(/scopeKey/);
  });
});

// ── CTAs (fix #2 audit) ──────────────────────────────────────────────
describe('Pilotage cards — CTAs actionnables', () => {
  it('RadarPrixNegatifsCard propose un CTA "Planifier" via ActionDrawer, desactive si pas de site scope', () => {
    expect(radarSrc).toMatch(/useActionDrawer/);
    expect(radarSrc).toMatch(/openActionDrawer\(/);
    // Le backend actions n'accepte que "manual" ou "insight" comme source_type.
    // On utilise donc sourceType: 'insight' + sourceId prefixe `pilotage_radar:`
    // pour conserver la tracabilite sans casser la validation enum.
    expect(radarSrc).toMatch(/sourceType:\s*['"]insight['"]/);
    expect(radarSrc).toMatch(/sourceId:\s*`pilotage_radar:/);
    expect(radarSrc).toMatch(/Planifier/);
    // Bouton disabled si scope.siteId absent (evite actions sans rattachement)
    expect(radarSrc).toMatch(/disabled=\{!hasSite\}/);
  });

  it('RoiFlexReadyCard expose un CTA navigation vers la fiche site (via toSite)', () => {
    expect(roiSrc).toMatch(/useNavigate/);
    expect(roiSrc).toMatch(/navigate\(ctaTarget\)/);
    expect(roiSrc).toMatch(/toSite\(scope\.siteId\)/);
    expect(roiSrc).toMatch(/data-testid=["']pilotage-roi-cta["']/);
  });

  it('PortefeuilleScoringCard rend les lignes top-5 cliquables via <Link> vers /sites/:id', () => {
    expect(portefeuilleSrc).toMatch(/from ['"]react-router-dom['"]/);
    expect(portefeuilleSrc).toMatch(/<Link\b/);
    expect(portefeuilleSrc).toMatch(/toSite\(/);
    // Seules les lignes avec Site.id numerique doivent etre cliquables
    expect(portefeuilleSrc).toMatch(/NUMERIC_ID_RE/);
  });
});

// ── Timezone Europe/Paris (audit utilisation #6) ─────────────────────
describe('RadarPrixNegatifsCard — timezone Europe/Paris force', () => {
  it('utilise Intl.DateTimeFormat avec timeZone Europe/Paris (pas new Date().getHours())', () => {
    expect(radarSrc).toMatch(/new Intl\.DateTimeFormat/);
    expect(radarSrc).toMatch(/timeZone:\s*['"]Europe\/Paris['"]/);
    // Plus de getHours() direct sur new Date(iso) pour affichage
    const codeOnly = radarSrc.replace(/\/\*[\s\S]*?\*\//g, '').replace(/\/\/.*$/gm, '');
    expect(codeOnly).not.toMatch(/new Date\([^)]+\)\.getHours\(\)/);
  });
});

// ── Wording fixes Sprint 1b (audit visuel agents SDK) ───────────────
describe('Pilotage cards — Sprint 1b wording FAIL corriges', () => {
  it('Radar sous-titre utilise "Fenetres favorables probables" (pas "cout efface")', () => {
    expect(radarSrc).toMatch(/Fenêtres favorables probables/);
    const codeOnly = radarSrc.replace(/\/\*[\s\S]*?\*\//g, '').replace(/\/\/.*$/gm, '');
    expect(codeOnly).not.toMatch(/coût effacé/);
  });

  it('Radar badge confiance affiche "confiance indicative" (pas "INDICATIVE" majuscules)', () => {
    expect(radarSrc).toMatch(/confiance \{data\?\.confiance/);
    const codeOnly = radarSrc.replace(/\/\*[\s\S]*?\*\//g, '').replace(/\/\/.*$/gm, '');
    expect(codeOnly).not.toMatch(/uppercase tracking-wide[^}]*confiance/);
  });

  it('RoiFlexReadyCard humanise archetype + site_id (plus de codes SCREAMING_SNAKE cote UI)', () => {
    expect(roiSrc).toMatch(/humaniseArchetype/);
    expect(roiSrc).toMatch(/humaniseSiteId/);
  });

  it('PortefeuilleScoringCard humanise archetype + mappe "INCONNU" en "A qualifier"', () => {
    expect(portefeuilleSrc).toMatch(/humaniseArchetype/);
    expect(portefeuilleSrc).toMatch(/HEATMAP_INCONNU_LABEL/);
    expect(portefeuilleSrc).toMatch(/À qualifier/);
  });
});

// ── Data-testid stability (audit robustesse) ─────────────────────────
describe('Pilotage cards — data-testid stable pour Playwright', () => {
  it('chaque carte porte son data-testid racine', () => {
    expect(radarSrc).toMatch(/data-testid=["']pilotage-radar-card["']/);
    expect(roiSrc).toMatch(/data-testid=["']pilotage-roi-card["']/);
    expect(portefeuilleSrc).toMatch(/data-testid=["']pilotage-portefeuille-card["']/);
  });
});
