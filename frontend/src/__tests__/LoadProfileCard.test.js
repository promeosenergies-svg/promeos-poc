/**
 * PROMEOS — LoadProfileCard — Source Guards + Structure Tests
 *
 * Card analytics : profil horaire type 24h + 5 KPI tiles (baseload P5,
 * load factor, ratios nuit/jour et WE/semaine, pic moyen).
 *
 * Pattern identique à MarketWidget.test.js : guards de source sans
 * render RTL ni mocks axios (convention projet).
 *
 * Introduit Lot 7 post-audit : l'audit /simplify + /review a identifié
 * l'absence de test unitaire dédié comme dette P2 à combler.
 */
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const cardPath = join(__dirname, '..', 'components', 'analytics', 'LoadProfileCard.jsx');
const cardSrc = readFileSync(cardPath, 'utf-8');

// ── Source Guards (no-calc) ──────────────────────────────────────────

describe('LoadProfileCard — source guard (no-calc)', () => {
  it('zéro .toFixed() (migration Lot 7 vers fmtNum)', () => {
    expect(cardSrc).not.toMatch(/\.toFixed\(/);
  });

  it('importe fmtNum depuis utils/format (helper FR null-safe)', () => {
    expect(cardSrc).toMatch(/import\s*\{[^}]*fmtNum[^}]*\}\s*from\s*['"]\.\.\/\.\.\/utils\/format['"]/);
  });

  it('utilise fmtNum pour kWh moyen dans le tooltip (2 décimales)', () => {
    expect(cardSrc).toMatch(/fmtNum\(d\.kwh,\s*2\)/);
  });

  it('utilise fmtNum pour baseload P5 (1 décimale)', () => {
    expect(cardSrc).toMatch(/fmtNum\(baseload\.p5_kwh,\s*1\)/);
  });

  it('utilise fmtNum pour load factor + ratios (2 décimales)', () => {
    expect(cardSrc).toMatch(/fmtNum\(data\.load_factor,\s*2\)/);
    expect(cardSrc).toMatch(/fmtNum\(ratios\.night_day,\s*2\)/);
    expect(cardSrc).toMatch(/fmtNum\(ratios\.weekend_weekday,\s*2\)/);
  });

  it('utilise fmtNum pour pic moyen (1 décimale)', () => {
    expect(cardSrc).toMatch(/fmtNum\(peakHour\.kwh,\s*1\)/);
  });
});

// ── Structure card ──────────────────────────────────────────

describe('LoadProfileCard — structure', () => {
  it('consomme GET /api/usages/load-profile/{siteId}', () => {
    expect(cardSrc).toMatch(/getLoadProfile/);
  });

  it('déclare les 4 niveaux de qualité données (excellent/bon/acceptable/insuffisant)', () => {
    expect(cardSrc).toMatch(/\bexcellent\b/);
    expect(cardSrc).toMatch(/\bbon\b/);
    expect(cardSrc).toMatch(/\bacceptable\b/);
    expect(cardSrc).toMatch(/\binsuffisant\b/);
  });

  it('déclare les 3 verdicts baseload (normal/modere/eleve)', () => {
    expect(cardSrc).toMatch(/normal/);
    expect(cardSrc).toMatch(/modere/);
    expect(cardSrc).toMatch(/eleve/);
  });

  it('utilise les icônes sémantiques (Activity, CheckCircle2, Moon)', () => {
    expect(cardSrc).toMatch(/Activity/);
    expect(cardSrc).toMatch(/CheckCircle2/);
    expect(cardSrc).toMatch(/Moon/);
  });

  it('gère les 3 états loading / error / data', () => {
    expect(cardSrc).toMatch(/\bloading\b/);
    expect(cardSrc).toMatch(/\berror\b/);
    expect(cardSrc).toMatch(/animate-pulse/);
    expect(cardSrc).toMatch(/AlertTriangle/);
  });

  it('rend un BarChart 24h via recharts avec Cell highlight du pic', () => {
    expect(cardSrc).toMatch(/BarChart/);
    expect(cardSrc).toMatch(/\bBar\b/);
    expect(cardSrc).toMatch(/\bCell\b/);
    expect(cardSrc).toMatch(/ResponsiveContainer/);
    expect(cardSrc).toMatch(/peakHour/);
  });

  it('expose les 4 KPI tiles (Baseload P5, Load factor, Nuit/Jour, WE/Semaine)', () => {
    expect(cardSrc).toMatch(/Baseload P5/);
    expect(cardSrc).toMatch(/Load factor/);
    expect(cardSrc).toMatch(/Nuit \/ Jour/);
    expect(cardSrc).toMatch(/WE \/ Semaine/);
  });

  it('affiche les sublabels métier (Pics marqués, Actif 7\\/7, Fermé WE, etc.)', () => {
    expect(cardSrc).toMatch(/Pics marqués/);
    expect(cardSrc).toMatch(/Usage régulier/);
    expect(cardSrc).toMatch(/Actif 7\/7/);
    expect(cardSrc).toMatch(/Fermé WE/);
  });

  it('cleanup useEffect via flag stale (anti race-condition)', () => {
    expect(cardSrc).toMatch(/let stale = false/);
    expect(cardSrc).toMatch(/if\s*\(!stale\)/);
  });
});

// ── Null-safety contract (fmtNum retourne "—") ──────────────────────

describe('LoadProfileCard — null-safety via fmtNum', () => {
  it('ne contient plus le pattern `?.toFixed(n) || "—"` (remplacé par fmtNum)', () => {
    expect(cardSrc).not.toMatch(/\?\.toFixed\(\d+\)\s*\|\|\s*['"]—['"]/);
  });

  it('pas de fallback "—" hand-rolled sur les KPI tiles (géré par fmtNum)', () => {
    // Le KpiTile accepte `value` déjà formaté. fmtNum retourne "—" si null.
    // On vérifie qu'aucun appel KpiTile ne wrap encore avec || "—".
    const kpiCalls = cardSrc.match(/<KpiTile[\s\S]*?\/>/g) || [];
    for (const call of kpiCalls) {
      expect(call).not.toMatch(/\?\.\w+\(\s*\d+\s*\)\s*\|\|\s*['"]—['"]/);
    }
  });
});
