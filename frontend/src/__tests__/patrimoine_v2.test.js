import { describe, test, expect } from 'vitest';
import fs from 'fs';

const SRC = fs.readFileSync('src/pages/Patrimoine.jsx', 'utf-8');

describe('Patrimoine V2 — Table as hero', () => {
  test('KPI strip existe (pas KpiCardCompact dans le flow principal)', () => {
    expect(SRC).toMatch(/KpiStripItem|kpi-strip|kpi.*strip/i);
  });

  test('PatrimoineHeatmap pas dans le flow principal', () => {
    const heatmapInFlow = SRC.split('\n').filter(
      (l) => l.includes('PatrimoineHeatmap') && !l.includes('//') && !l.includes('carte')
    );
    // Heatmap should only appear inside viewMode === 'carte' or be commented out
    expect(heatmapInFlow.every((l) => l.includes('carte') || l.includes('import'))).toBe(true);
  });

  test('Pagination existe', () => {
    expect(SRC).toMatch(/page.*Size|PAGE_SIZE|pagination|Pager/i);
  });

  test('Tri par colonnes', () => {
    expect(SRC).toMatch(/sortBy|handleSort|onSort/);
  });

  test('Clic ligne navigue vers /sites/:id', () => {
    expect(SRC).toMatch(/navigate.*sites.*id|\/sites\//);
  });

  test('Toggle Tableau/Carte', () => {
    expect(SRC).toMatch(/viewMode|table.*carte/i);
  });

  test('Pas de HealthBar dans le flow principal', () => {
    const healthInFlow = SRC.split('\n').filter(
      (l) => l.includes('PatrimoinePortfolioHealthBar') && !l.includes('//')
    );
    expect(healthInFlow.length).toBeLessThanOrEqual(1); // import only
  });
});
