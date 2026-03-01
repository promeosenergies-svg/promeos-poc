/**
 * PROMEOS — ScheduleEditor V1 — Validation tests
 * Source-guard: validates that ScheduleEditor.jsx has time validation logic.
 *
 * Vérifie :
 *   1. openTime >= closeTime → message d'erreur visible
 *   2. Bouton Save désactivé si timeError
 *   3. data-testid="time-error" présent pour l'UX
 */
import { readFileSync } from 'fs';
import { resolve } from 'path';
import { describe, it, expect } from 'vitest';

const root = resolve(__dirname, '../../../');
const readSrc = (...parts) => readFileSync(resolve(root, 'src', ...parts), 'utf-8');

describe('ScheduleEditor — time validation', () => {
  const code = readSrc('pages', 'consumption', 'ScheduleEditor.jsx');

  it('computes timeError when openTime >= closeTime', () => {
    expect(code).toMatch(/timeError/);
    expect(code).toMatch(/openTime.*>=.*closeTime|openTime && closeTime && openTime >= closeTime/);
  });

  it('displays error message with data-testid', () => {
    expect(code).toMatch(/data-testid=["']time-error["']/);
  });

  it('disables Save button when timeError is truthy', () => {
    expect(code).toMatch(/disabled=\{.*timeError/);
  });

  it('shows French error message about opening < closing', () => {
    expect(code).toMatch(/ouverture.*rieure.*fermeture/i);
  });

  it('applies red border on time inputs when error', () => {
    expect(code).toMatch(/border-red-300/);
  });
});

describe('ScheduleEditor — existing features preserved', () => {
  const code = readSrc('pages', 'consumption', 'ScheduleEditor.jsx');

  it('has handleSave function', () => {
    expect(code).toMatch(/handleSave/);
  });

  it('has handleSuggest for NAF', () => {
    expect(code).toMatch(/handleSuggest/);
  });

  it('has is_24_7 toggle', () => {
    expect(code).toMatch(/is247|is_24_7/);
  });

  it('calls putSiteSchedule on save', () => {
    expect(code).toMatch(/putSiteSchedule/);
  });

  it('calls refreshConsumptionDiagnose after save', () => {
    expect(code).toMatch(/refreshConsumptionDiagnose/);
  });

  it('has dirty state tracking', () => {
    expect(code).toMatch(/setDirty\(true\)/);
  });
});

describe('ProfileHeatmapTab — useMemo optimization', () => {
  const code = readSrc('pages', 'consumption', 'ProfileHeatmapTab.jsx');

  it('uses useMemo for HeatmapGrid data', () => {
    expect(code).toMatch(/useMemo/);
  });

  it('uses useMemo for DailyProfileChart chartData', () => {
    // The chartData should be wrapped in useMemo
    expect(code).toMatch(/useMemo\(\(\)\s*=>\s*\(dailyProfile/);
  });
});

describe('Backend service — V1 error handling', () => {
  const code = readFileSync(
    resolve(root, '..', 'backend', 'services', 'consumption_context_service.py'),
    'utf-8'
  );

  it('uses structured logging', () => {
    expect(code).toMatch(/logger = logging\.getLogger/);
  });

  it('does NOT use bare except Exception: pass', () => {
    expect(code).not.toMatch(/except\s+Exception\s*:\s*\n\s*pass/);
  });

  it('raises HTTPException for missing site in get_activity_context', () => {
    expect(code).toMatch(/raise HTTPException\(status_code=404/);
  });

  it('uses proper org join (EntiteJuridique) for portfolio', () => {
    expect(code).toMatch(/EntiteJuridique\.organisation_id == org_id/);
    expect(code).not.toMatch(/Site\.org_id/);
  });
});
