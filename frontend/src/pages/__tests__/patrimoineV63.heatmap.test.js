/**
 * patrimoineV63.heatmap.test.js — Guards V63 PatrimoineHeatmap
 *
 * Source guards (AST-free, regex-based) :
 *   A. PatrimoineHeatmap.jsx     : composant heatmap, tiles, filtres, couleurs
 *   B. Patrimoine.jsx            : import, état hmTiles, useEffect, <PatrimoineHeatmap>
 *   C. api.js                    : getPatrimoineAnomalies
 *
 * Vérifications clés :
 *   - PatrimoineHeatmap exporté comme default
 *   - Props tiles/onOpenSite/loading/error gérées
 *   - États loading (skeleton), error, empty (CTA Charger la démo)
 *   - getTileColorKey : quantiles + fallback sévérité
 *   - SiteTile rendu avec site_nom, risk, anomalies_count, framework
 *   - Filtres : fwFilter, sevFilter, search, sort
 *   - Tri : risk, anomalies, score
 *   - Patrimoine.jsx : hmTiles state, hmLoading, useEffect, Promise.all,
 *     getPatrimoineAnomalies, dominant_framework, max_severity
 *   - Pas de régression : openDrawerOnAnomalies toujours présent
 */
import { describe, test, expect } from 'vitest';
import { readFileSync } from 'fs';
import path from 'path';

const src = (rel) => readFileSync(path.resolve(__dirname, '..', '..', rel), 'utf8');

const HEATMAP_JSX = src('components/PatrimoineHeatmap.jsx');
const PATRIMOINE_JSX = src('pages/Patrimoine.jsx');
const API_JS = src('services/api.js');

// ── PatrimoineHeatmap.jsx — structure composant ───────────────────────────

describe('PatrimoineHeatmap V63 — export + props', () => {
  test('default export PatrimoineHeatmap', () => {
    expect(HEATMAP_JSX).toMatch(/export default function PatrimoineHeatmap/);
  });

  test('prop tiles acceptée', () => {
    expect(HEATMAP_JSX).toMatch(/tiles\s*=\s*\[\]/);
  });

  test('prop onOpenSite acceptée', () => {
    expect(HEATMAP_JSX).toMatch(/onOpenSite/);
  });

  test('prop loading acceptée', () => {
    expect(HEATMAP_JSX).toMatch(/loading\s*=\s*false/);
  });

  test('prop error acceptée', () => {
    expect(HEATMAP_JSX).toMatch(/error\s*=\s*null/);
  });
});

// ── PatrimoineHeatmap.jsx — états UI ─────────────────────────────────────

describe('PatrimoineHeatmap V63 — états UI', () => {
  test('état loading → skeleton (animate-pulse)', () => {
    expect(HEATMAP_JSX).toMatch(/animate-pulse/);
  });

  test('état error → AlertTriangle rendu', () => {
    expect(HEATMAP_JSX).toMatch(/AlertTriangle/);
  });

  test('état empty → CTA "Charger la démo"', () => {
    expect(HEATMAP_JSX).toMatch(/Charger la démo/);
  });

  test('état empty → lien vers /import', () => {
    expect(HEATMAP_JSX).toMatch(/\/import/);
  });

  test('état empty → navigate utilisé', () => {
    expect(HEATMAP_JSX).toMatch(/useNavigate|navigate/);
  });

  test('Upload icon utilisé (CTA import)', () => {
    expect(HEATMAP_JSX).toMatch(/Upload/);
  });
});

// ── PatrimoineHeatmap.jsx — SiteTile ─────────────────────────────────────

describe('PatrimoineHeatmap V63 — SiteTile rendu', () => {
  test('SiteTile défini', () => {
    expect(HEATMAP_JSX).toMatch(/function SiteTile/);
  });

  test('site_nom affiché dans tile', () => {
    expect(HEATMAP_JSX).toMatch(/site_nom/);
  });

  test('total_risk_eur affiché via fmtRisk', () => {
    expect(HEATMAP_JSX).toMatch(/total_risk_eur/);
    expect(HEATMAP_JSX).toMatch(/fmtRisk/);
  });

  test('anomalies_count affiché dans tile', () => {
    expect(HEATMAP_JSX).toMatch(/anomalies_count/);
  });

  test('dominant_framework utilisé pour chip', () => {
    expect(HEATMAP_JSX).toMatch(/dominant_framework/);
  });

  test('completude_score affiché', () => {
    expect(HEATMAP_JSX).toMatch(/completude_score/);
  });

  test('top_anomalies preview affiché', () => {
    expect(HEATMAP_JSX).toMatch(/top_anomalies/);
  });

  test('tile cliquable → onOpenSite appelé', () => {
    expect(HEATMAP_JSX).toMatch(/onOpenSite\?\.\(tile\.site_id\)|onOpenSite\(tile\.site_id\)/);
  });

  test('bande couleur haut tile présente (h-1)', () => {
    expect(HEATMAP_JSX).toMatch(/h-1\b/);
  });

  test('barre couleur bg-red + bg-orange + bg-amber présentes', () => {
    expect(HEATMAP_JSX).toMatch(/bg-red-/);
    expect(HEATMAP_JSX).toMatch(/bg-orange-/);
    expect(HEATMAP_JSX).toMatch(/bg-amber-/);
  });
});

// ── PatrimoineHeatmap.jsx — getTileColorKey ───────────────────────────────

describe('PatrimoineHeatmap V63 — getTileColorKey couleur quantile', () => {
  test('getTileColorKey défini', () => {
    expect(HEATMAP_JSX).toMatch(/function getTileColorKey/);
  });

  test('logique quantile pct < 0.34', () => {
    expect(HEATMAP_JSX).toMatch(/pct.*0\.34|0\.34.*pct/);
  });

  test('logique quantile pct < 0.67', () => {
    expect(HEATMAP_JSX).toMatch(/pct.*0\.67|0\.67.*pct/);
  });

  test('fallback sévérité si risk = 0', () => {
    expect(HEATMAP_JSX).toMatch(/max_severity/);
    expect(HEATMAP_JSX).toMatch(/CRITICAL.*critical|critical.*CRITICAL/);
  });

  test('COLOR_CLASSES définit critical/high/medium/low/none', () => {
    expect(HEATMAP_JSX).toMatch(/critical/);
    expect(HEATMAP_JSX).toMatch(/high/);
    expect(HEATMAP_JSX).toMatch(/medium/);
    expect(HEATMAP_JSX).toMatch(/low/);
    expect(HEATMAP_JSX).toMatch(/none/);
  });
});

// ── PatrimoineHeatmap.jsx — Filtres ───────────────────────────────────────

describe('PatrimoineHeatmap V63 — filtres et tri', () => {
  test('filtre framework fwFilter défini', () => {
    expect(HEATMAP_JSX).toMatch(/fwFilter/);
  });

  test('filtre sévérité sevFilter défini', () => {
    expect(HEATMAP_JSX).toMatch(/sevFilter/);
  });

  test('filtre search texte défini', () => {
    expect(HEATMAP_JSX).toMatch(/search/);
  });

  test('tri sort défini (risk|anomalies|score)', () => {
    expect(HEATMAP_JSX).toMatch(/sort.*risk|risk.*sort/);
    expect(HEATMAP_JSX).toMatch(/anomalies/);
    expect(HEATMAP_JSX).toMatch(/score/);
  });

  test('bouton reset filtres présent', () => {
    expect(HEATMAP_JSX).toMatch(/Réinitialiser/);
  });

  test('useMemo pour filtered', () => {
    expect(HEATMAP_JSX).toMatch(/useMemo/);
  });

  test('message "Aucun site ne correspond" si filtered vide', () => {
    expect(HEATMAP_JSX).toMatch(/Aucun site ne correspond/);
  });

  test('options FW_OPTIONS contiennent DECRET_TERTIAIRE/FACTURATION/BACS', () => {
    expect(HEATMAP_JSX).toMatch(/DECRET_TERTIAIRE/);
    expect(HEATMAP_JSX).toMatch(/FACTURATION/);
    expect(HEATMAP_JSX).toMatch(/BACS/);
  });

  test('grille responsive grid-cols-2', () => {
    expect(HEATMAP_JSX).toMatch(/grid-cols-2/);
  });

  test('counter tiles affiché dans header', () => {
    expect(HEATMAP_JSX).toMatch(/tiles\.length/);
  });
});

// ── Patrimoine.jsx — intégration V63 ─────────────────────────────────────

describe('Patrimoine.jsx V63 — intégration heatmap', () => {
  test('PatrimoineHeatmap importé', () => {
    expect(PATRIMOINE_JSX).toMatch(/import PatrimoineHeatmap/);
  });

  test('getPatrimoineAnomalies importé', () => {
    expect(PATRIMOINE_JSX).toMatch(/getPatrimoineAnomalies/);
  });

  test('hmTiles state défini', () => {
    expect(PATRIMOINE_JSX).toMatch(/hmTiles/);
  });

  test('hmLoading state défini', () => {
    expect(PATRIMOINE_JSX).toMatch(/hmLoading/);
  });

  test('hmError state défini', () => {
    expect(PATRIMOINE_JSX).toMatch(/hmError/);
  });

  test('hmFetchIdRef useRef défini (guard stale)', () => {
    expect(PATRIMOINE_JSX).toMatch(/hmFetchIdRef/);
  });

  test('useEffect sur scopedSites pour enrichissement', () => {
    expect(PATRIMOINE_JSX).toMatch(/useEffect.*scopedSites|scopedSites.*useEffect/s);
  });

  test('Promise.all pour fetch parallèle', () => {
    expect(PATRIMOINE_JSX).toMatch(/Promise\.all/);
  });

  test('guard stale fetchId présent', () => {
    expect(PATRIMOINE_JSX).toMatch(/fetchId|hmFetchIdRef\.current/);
  });

  test('dominant_framework calculé', () => {
    expect(PATRIMOINE_JSX).toMatch(/dominant_framework/);
  });

  test('max_severity calculé', () => {
    expect(PATRIMOINE_JSX).toMatch(/max_severity/);
  });

  test('completude_score transmis au tile model', () => {
    expect(PATRIMOINE_JSX).toMatch(/completude_score/);
  });

  test('top_anomalies slice(0,2) transmis', () => {
    expect(PATRIMOINE_JSX).toMatch(/top_anomalies/);
    expect(PATRIMOINE_JSX).toMatch(/slice\s*\(\s*0\s*,\s*2\s*\)/);
  });

  test('guard scopedSites.length === 0 → reset hmTiles', () => {
    expect(PATRIMOINE_JSX).toMatch(/scopedSites\.length\s*===\s*0/);
  });

  test('guard 10 sites max (HEATMAP_MAX_SITES)', () => {
    expect(PATRIMOINE_JSX).toMatch(/HEATMAP_MAX_SITES\s*=\s*10/);
    expect(PATRIMOINE_JSX).toMatch(/slice\s*\(\s*0\s*,\s*HEATMAP_MAX_SITES\s*\)/);
  });

  test('<PatrimoineHeatmap> rendu dans JSX', () => {
    expect(PATRIMOINE_JSX).toMatch(/<PatrimoineHeatmap/);
  });

  test('tiles={hmTiles} passé à PatrimoineHeatmap', () => {
    expect(PATRIMOINE_JSX).toMatch(/tiles=\{hmTiles\}/);
  });

  test('onOpenSite={openDrawerOnAnomalies} passé', () => {
    expect(PATRIMOINE_JSX).toMatch(/onOpenSite=\{openDrawerOnAnomalies\}/);
  });

  test('loading={hmLoading} passé', () => {
    expect(PATRIMOINE_JSX).toMatch(/loading=\{hmLoading\}/);
  });

  test('error={hmError} passé', () => {
    expect(PATRIMOINE_JSX).toMatch(/error=\{hmError\}/);
  });

  test('openDrawerOnAnomalies toujours présent (pas de régression V60)', () => {
    expect(PATRIMOINE_JSX).toMatch(/openDrawerOnAnomalies/);
  });
});

// ── api.js — wrappers ────────────────────────────────────────────────────

describe('api.js V63 — getPatrimoineAnomalies', () => {
  test('getPatrimoineAnomalies exporté dans api.js', () => {
    expect(API_JS).toMatch(/export const getPatrimoineAnomalies/);
  });

  test('endpoint /patrimoine/sites/{id}/anomalies', () => {
    expect(API_JS).toMatch(/patrimoine\/sites.*anomalies/);
  });
});

// ── Top-15 scalabilité (cas de test a/b/c/d du cahier des charges) ────────

describe('PatrimoineHeatmap V63-scale — Top-15 tiles', () => {
  test('MAX_TILES = 15 défini', () => {
    expect(HEATMAP_JSX).toMatch(/MAX_TILES\s*=\s*15/);
  });

  test('visibleTiles calculé depuis filtered', () => {
    expect(HEATMAP_JSX).toMatch(/visibleTiles/);
  });

  test('showTopBanner conditionnel sur filtered.length > MAX_TILES', () => {
    expect(HEATMAP_JSX).toMatch(/showTopBanner/);
    expect(HEATMAP_JSX).toMatch(/filtered\.length\s*>\s*MAX_TILES/);
  });

  // cas (a) : 5 sites → pas de bandeau (showTopBanner = false quand filtered.length ≤ 15)
  test('pas de bandeau si filtered.length ≤ MAX_TILES (condition guard)', () => {
    // Le bandeau n'est rendu que si showTopBanner est vrai
    expect(HEATMAP_JSX).toMatch(/\{showTopBanner/);
  });

  // cas (b) : 20 sites → bandeau "15 / 20 (Top risques)"
  test('bandeau affiche visibleTiles.length / filtered.length (Top risques)', () => {
    expect(HEATMAP_JSX).toMatch(/visibleTiles\.length/);
    expect(HEATMAP_JSX).toMatch(/filtered\.length/);
    expect(HEATMAP_JSX).toMatch(/Top\s+risques/s);
  });

  // cas (b) : 20 sites → slice(0, MAX_TILES) pour sélection top-15
  test('slice sur MAX_TILES pour sélection top-15', () => {
    expect(HEATMAP_JSX).toMatch(/\.slice\s*\(\s*0\s*,\s*MAX_TILES\s*\)/);
  });

  // cas (b) : selection triée par total_risk_eur DESC avant slice
  test('tri par total_risk_eur DESC avant slice', () => {
    expect(HEATMAP_JSX).toMatch(/total_risk_eur.*sort|sort.*total_risk_eur/s);
  });

  // cas (c) : filtres réduisent à 8 → pas de bandeau (8 ≤ 15)
  test('visibleTiles = filtered quand filtered.length ≤ MAX_TILES (no banner)', () => {
    // La condition ternaire couvre les deux cas
    expect(HEATMAP_JSX).toMatch(
      /filtered\.length\s*>\s*MAX_TILES[\s\S]*?\?[\s\S]*?:[\s\S]*?filtered/
    );
  });

  // cas (d) : CTA "Voir tous les sites" uniquement quand showTopBanner
  test('CTA "Voir tous les sites" présent dans le bandeau', () => {
    expect(HEATMAP_JSX).toMatch(/Voir tous les sites/);
  });

  test('CTA scroll vers id="sites-table"', () => {
    expect(HEATMAP_JSX).toMatch(/sites-table/);
    expect(HEATMAP_JSX).toMatch(/scrollIntoView/);
  });

  test('grille utilise visibleTiles.map (pas filtered.map)', () => {
    expect(HEATMAP_JSX).toMatch(/visibleTiles\.map/);
  });
});

// ── Patrimoine.jsx — id="sites-table" sur la table ───────────────────────

describe('Patrimoine.jsx V63-scale — id sites-table', () => {
  test('id="sites-table" présent sur l\'élément Card de la table', () => {
    expect(PATRIMOINE_JSX).toMatch(/id="sites-table"/);
  });
});
