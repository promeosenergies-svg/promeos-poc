/**
 * PROMEOS — EnergySignatureCard — Source Guards + Structure Tests
 *
 * Card analytics : scatter T° vs kWh + fit piecewise + classification
 * (heating/cooling/mixed/flat) + R² + 4 KPI tiles.
 *
 * Pattern identique à MarketWidget.test.js : guards de source (export,
 * imports, patterns) sans render RTL ni mocks axios (convention projet).
 *
 * Introduit Lot 7 post-audit : l'audit /simplify + /review a identifié
 * l'absence de test unitaire dédié comme dette P2 à combler.
 */
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const cardPath = join(__dirname, '..', 'components', 'analytics', 'EnergySignatureCard.jsx');
const cardSrc = readFileSync(cardPath, 'utf-8');

// ── Source Guards (no-calc) ──────────────────────────────────────────

describe('EnergySignatureCard — source guard (no-calc)', () => {
  it('zéro .toFixed() (migration Lot 7 vers fmtNum)', () => {
    expect(cardSrc).not.toMatch(/\.toFixed\(/);
  });

  it('importe fmtNum depuis utils/format (helper FR null-safe)', () => {
    expect(cardSrc).toMatch(
      /import\s*\{[^}]*fmtNum[^}]*\}\s*from\s*['"]\.\.\/\.\.\/utils\/format['"]/
    );
  });

  it('utilise fmtNum pour R² avec 3 décimales', () => {
    expect(cardSrc).toMatch(/fmtNum\(model\.r_squared,\s*3\)/);
  });

  it('utilise fmtNum pour baseload (0 décimales)', () => {
    expect(cardSrc).toMatch(/fmtNum\(model\.base_kwh_day,\s*0\)/);
  });

  it('utilise fmtNum pour pentes chauffage/clim (1 décimale)', () => {
    expect(cardSrc).toMatch(/fmtNum\(model\.a_heating_kwh_per_c,\s*1\)/);
    expect(cardSrc).toMatch(/fmtNum\(model\.b_cooling_kwh_per_c,\s*1\)/);
  });
});

// ── Structure card ──────────────────────────────────────────

describe('EnergySignatureCard — structure', () => {
  it('consomme GET /api/usages/energy-signature/{siteId}/advanced', () => {
    expect(cardSrc).toMatch(/getEnergySignatureAdvanced/);
  });

  it('déclare les 4 labels métier (heating/cooling/mixed/flat)', () => {
    expect(cardSrc).toMatch(/heating_dominant/);
    expect(cardSrc).toMatch(/cooling_dominant/);
    expect(cardSrc).toMatch(/mixed/);
    expect(cardSrc).toMatch(/flat/);
  });

  it('utilise les 4 icônes sémantiques (Flame, Snowflake, Thermometer, TrendingUp)', () => {
    expect(cardSrc).toMatch(/Flame/);
    expect(cardSrc).toMatch(/Snowflake/);
    expect(cardSrc).toMatch(/Thermometer/);
    expect(cardSrc).toMatch(/TrendingUp/);
  });

  it('gère les 3 états loading / error / data', () => {
    expect(cardSrc).toMatch(/\bloading\b/);
    expect(cardSrc).toMatch(/\berror\b/);
    expect(cardSrc).toMatch(/animate-pulse/);
    expect(cardSrc).toMatch(/AlertTriangle/);
  });

  it('rend un scatter + fit line via recharts ComposedChart', () => {
    expect(cardSrc).toMatch(/ComposedChart/);
    expect(cardSrc).toMatch(/Scatter/);
    expect(cardSrc).toMatch(/\bLine\b/);
    expect(cardSrc).toMatch(/ResponsiveContainer/);
  });

  it('expose 4 KPI tiles (baseload, pente chauffage, pente clim, part thermo)', () => {
    expect(cardSrc).toMatch(/Baseload/);
    expect(cardSrc).toMatch(/Pente chauffage/);
    expect(cardSrc).toMatch(/Pente clim/);
    expect(cardSrc).toMatch(/Part thermosens\./);
  });

  it('affiche le R² dans le header (qualité du fit)', () => {
    expect(cardSrc).toMatch(/R²/);
    expect(cardSrc).toMatch(/r_squared/);
  });

  it('cleanup useEffect via flag stale (anti race-condition)', () => {
    expect(cardSrc).toMatch(/let stale = false/);
    expect(cardSrc).toMatch(/if\s*\(!stale\)/);
  });
});

// ── Null-safety contract (fmtNum retourne "—") ──────────────────────

describe('EnergySignatureCard — null-safety via fmtNum', () => {
  it('ne contient plus le pattern `?.toFixed(n) || "—"` (remplacé par fmtNum)', () => {
    expect(cardSrc).not.toMatch(/\?\.toFixed\(\d+\)\s*\|\|\s*['"]—['"]/);
  });

  it('pas de fallback "—" hand-rolled sur les KPI (géré par fmtNum)', () => {
    // On tolère "—" dans l'AlertTriangle message error et dans le footer
    // "source —" mais les KPI tiles ne doivent plus avoir de fallback manuel.
    const kpiBlock = cardSrc.match(/KPIs[\s\S]*?<\/div>\s*<\/div>\s*\n\s*<div className="mt-3/);
    if (kpiBlock) {
      expect(kpiBlock[0]).not.toMatch(/\|\|\s*['"]—['"]/);
    }
  });
});
