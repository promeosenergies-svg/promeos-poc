/**
 * Phase 27 — Source-guard ConsoSevenDaysBars consomme weekly_breakdown.
 *
 * Avant : SVG rendait 7 hauteurs hardcodées (`_CONSO_7D_DAYS`), tooltips
 * inférés depuis position pixel (Phase 26.bis).
 * Après Phase 27 : composant accepte `weeklyBreakdown` prop, projette les
 * vraies MWh via `_projectBreakdownToBars()`, fallback placeholder si absent.
 */
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { resolve } from 'path';

const SRC = readFileSync(resolve(__dirname, '../pages/CockpitPilotage.jsx'), 'utf-8');

describe('Phase 27 — Conso 7 jours data-driven', () => {
  it('expose le helper _projectBreakdownToBars', () => {
    expect(SRC).toMatch(/function\s+_projectBreakdownToBars\s*\(\s*breakdown\s*\)/);
    // Échelle Y dynamique : max(MWh, baseline 12)
    expect(SRC).toMatch(/Math\.max\(\s*_CONSO_7D_MWH_TOP/);
    // Mapping vers structure projetée x/y/h/mwh/anomaly/etc.
    expect(SRC).toMatch(/anomaly:\s*!!d\.is_anomaly/);
    expect(SRC).toMatch(/lowConfidence:\s*!!d\.low_confidence/);
  });

  it('ConsoSevenDaysBars accepte weeklyBreakdown prop + isDataDriven flag', () => {
    expect(SRC).toMatch(/function ConsoSevenDaysBars\s*\(\s*\{[^}]*weeklyBreakdown[^}]*\}/);
    expect(SRC).toMatch(/const projected = _projectBreakdownToBars\(weeklyBreakdown\)/);
    expect(SRC).toMatch(/const isDataDriven = projected !== null/);
  });

  it('le call site CockpitPilotage passe facts.consumption.weekly_breakdown', () => {
    expect(SRC).toMatch(/weeklyBreakdown=\{facts\?\.consumption\?\.weekly_breakdown\}/);
  });

  it('tooltip data-driven inclut date ISO + baseline si dispo', () => {
    expect(SRC).toMatch(/dateSuffix/);
    expect(SRC).toMatch(/baselinePart/);
    expect(SRC).toMatch(/baseline\s+\$\{/);
  });

  it('labels delta % et lettres jour rendus dynamiquement (pas hardcodés)', () => {
    // Plus de "+ 39 %" hardcodé — on rend depuis days.filter(d => d.anomaly)
    expect(SRC).toMatch(/days\s*\.filter\(/);
    expect(SRC).not.toMatch(/\+&#x202f;39&#x202f;%/);
    // Lettres jour : map sur days, plus 7 <text> hardcodés L/M/M/J/V/S/D séparés
    expect(SRC).toMatch(/days\.map\(\(day\)\s*=>\s*\{[\s\S]*?day\.letter/);
  });

  it('fallback placeholder préservé (1er render avant fetch)', () => {
    // _CONSO_7D_DAYS reste défini (utilisé en fallback) mais n'est plus le
    // seul source — `days = projected || _CONSO_7D_DAYS`
    expect(SRC).toMatch(/_CONSO_7D_DAYS/);
    expect(SRC).toMatch(/days = projected \|\| _CONSO_7D_DAYS/);
  });
});
