/**
 * PROMEOS — Source guards FE Patrimoine kWh/m² (Sprint C-2 Phase 4.3).
 *
 * Surveille frontend/src/pages/Patrimoine.jsx contre l'anti-pattern doctrine R7
 * (audit Phase B) : calcul kWh/m² inline ligne par site depuis annual_kwh / surface.
 *
 * Phase 4.2 backend a exposé Site.intensity_kwh_m2_total + intensity_kwh_m2_tertiaire
 * via _serialize_site (matrice v1 §4.4.F #56). Phase 4.3 retire le calcul inline
 * L1525-1531 (ligne table par site).
 *
 * SG_PATRIM_FE_01 — pas de Math.round(...site.surface_m2) (ligne par site)
 * SG_PATRIM_FE_02 — site.intensity_kwh_m2_total est consommé pour affichage par site
 *
 * Exception grandfathered (D-Phase4-3-Portfolio-Intensity-Backend-001 / Sprint C-3) :
 * - L825-830 (KpiStripItem global) : Σ(annual_kwh) / Σ(surface) reste calcul FE
 *   pour MVP car moyenne pondérée portfolio (≠ moyenne arithmétique des intensités
 *   sites). Endpoint backend agrégé prévu Sprint C-3.
 *
 * Pattern repo : readFileSync + regex (env=node).
 */

import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { dirname, join } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const SRC_ROOT = join(__dirname, '..', '..');
const PATRIMOINE_PATH = join(SRC_ROOT, 'pages', 'Patrimoine.jsx');
const PERFORMANCE_SITES_PATH = join(SRC_ROOT, 'pages', 'cockpit', 'PerformanceSitesCard.jsx');

function stripComments(src) {
  return src.replace(/\/\*[\s\S]*?\*\//g, '').replace(/\/\/.*$/gm, '');
}

describe('SG_PATRIM_FE — Patrimoine.jsx kWh/m² doctrine guards', () => {
  const raw = readFileSync(PATRIMOINE_PATH, 'utf-8');
  const src = stripComments(raw);

  it('SG_PATRIM_FE_01 — no inline Math.round of conso/site.surface_m2 per-site', () => {
    // Anti-pattern Phase B R7 : calcul kWh/m² inline ligne par site
    // Pattern interdit : Math.round((site.conso_kwh_an || 0) / site.surface_m2)
    const FORBIDDEN = /Math\.round\([^)]*site\.surface_m2[^)]*\)/g;
    const matches = src.match(FORBIDDEN) || [];
    expect(
      matches,
      `Anti-pattern doctrine R7 détecté : Math.round(.../site.surface_m2). ` +
        `Utiliser site.intensity_kwh_m2_total exposé par backend (Phase 4.2).`
    ).toEqual([]);
  });

  it('SG_PATRIM_FE_02 — uses site.intensity_kwh_m2_total for per-site display', () => {
    // Phase 4.3 : pattern requis après refonte L1525-1531
    expect(
      src,
      `site.intensity_kwh_m2_total doit être consommé pour l'affichage kWh/m² par site. ` +
        `Source : backend _serialize_site (Phase 4.2).`
    ).toMatch(/site\.intensity_kwh_m2_total/);
  });

  it('SG_PATRIM_FE_03 — grandfathered portfolio aggregate references debt entry', () => {
    // L'agrégat portfolio (KpiStripItem global) reste calcul FE pour MVP.
    // On exige une référence inline à la dette tracée pour traçabilité.
    expect(
      raw, // sur version brute pour inclure les commentaires inline
      `L'agrégat portfolio kWh/m² doit référencer D-Phase4-3-Portfolio-Intensity-Backend-001 ` +
        `(commentaire inline) pour traçabilité dette.`
    ).toMatch(/D-Phase4-3-Portfolio-Intensity-Backend-001/);
  });

  it('SG_PATRIM_FE_04 — PerformanceSitesCard.jsx no inline conso/surface division (Phase 4.5d)', () => {
    // P0 cleanup cockpit (2026-05-25) — PerformanceSitesCard.jsx supprimé
    // (orphelin post suppression Cockpit.jsx). Le SG passe trivialement
    // si le fichier n'existe plus (l'anti-pattern ne peut pas exister).
    let perfSrc;
    try {
      perfSrc = stripComments(readFileSync(PERFORMANCE_SITES_PATH, 'utf-8'));
    } catch {
      return; // fichier supprimé → SG vacuously vrai
    }
    const FORBIDDEN = /Math\.round\([^)]*conso_kwh_an[^)]*\/[^)]*surface_m2[^)]*\)/g;
    const matches = perfSrc.match(FORBIDDEN) || [];
    expect(
      matches,
      `Anti-pattern doctrine R7 détecté dans PerformanceSitesCard.jsx : ` +
        `Math.round(conso_kwh_an / surface_m2). Utiliser site.intensity_kwh_m2_total.`
    ).toEqual([]);
  });
});
