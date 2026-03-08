/**
 * PROMEOS — Step 34 source-guard : Carte sites geolocalises
 */
import { describe, it, expect } from 'vitest';
import { readFileSync, existsSync } from 'fs';
import { join } from 'path';

const src_dir = join(__dirname, '..');
const mapCandidates = [
  join(src_dir, 'components', 'patrimoine', 'SitesMap.jsx'),
  join(src_dir, 'components', 'SitesMap.jsx'),
];
const patrimoinePath = join(src_dir, 'pages', 'Patrimoine.jsx');

function findMap() {
  const found = mapCandidates.find((f) => existsSync(f));
  return found ? readFileSync(found, 'utf-8') : null;
}

function read(p) {
  return existsSync(p) ? readFileSync(p, 'utf-8') : null;
}

describe('Step 34 — SitesMap component', () => {
  const mapSrc = findMap();

  it('SitesMap component exists', () => {
    expect(mapSrc).not.toBeNull();
  });

  it('has color coding by compliance status (green/amber/red)', () => {
    expect(mapSrc).toMatch(/#10b981|emerald|green/i);
    expect(mapSrc).toMatch(/#f59e0b|amber|orange/i);
    expect(mapSrc).toMatch(/#ef4444|red/i);
  });

  it('has legend with Conforme / A risque / Non conforme', () => {
    expect(mapSrc).toMatch(/Conforme/);
    expect(mapSrc).toMatch(/risque/i);
    expect(mapSrc).toMatch(/Non conforme/i);
  });

  it('has site click handler (onSiteClick or navigate)', () => {
    expect(mapSrc).toMatch(/onSiteClick|onClick|navigate/);
  });

  it('has popup with site details', () => {
    expect(mapSrc).toMatch(/Popup|popup/);
    expect(mapSrc).toMatch(/Voir le site/);
  });

  it('handles missing coordinates gracefully', () => {
    expect(mapSrc).toMatch(/latitude|coordonn|filter|lat/i);
    expect(mapSrc).toMatch(/sans coordonn|missing/i);
  });

  it('uses SVG or Leaflet for rendering', () => {
    expect(mapSrc).toMatch(/svg|SVG|MapContainer|leaflet/i);
  });

  it('has France-centered projection', () => {
    // France lat ~46, lng ~2
    expect(mapSrc).toMatch(/46|France|FRANCE|BOUNDS/);
  });

  it('has data-testid sites-map', () => {
    expect(mapSrc).toMatch(/sites-map/);
  });
});

describe('Step 34 — Patrimoine integration', () => {
  const src = read(patrimoinePath);

  it('imports SitesMap', () => {
    expect(src).toMatch(/SitesMap/);
  });

  it('has viewMode state (table/map toggle)', () => {
    expect(src).toMatch(/viewMode/);
    expect(src).toMatch(/setViewMode/);
  });

  it('has Tableau / Carte toggle buttons', () => {
    expect(src).toMatch(/Tableau/);
    expect(src).toMatch(/Carte/);
  });

  it('renders SitesMap when viewMode is map', () => {
    expect(src).toMatch(/viewMode.*map.*SitesMap|SitesMap.*viewMode/s);
  });
});
