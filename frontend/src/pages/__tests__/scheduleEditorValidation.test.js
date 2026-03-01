/**
 * PROMEOS — ScheduleEditor V1.1 — Validation tests
 * Source-guard + unit tests for multi-interval validation logic.
 *
 * Vérifie :
 *   1. Multi-interval validation (start < end, no overlap, adjacent OK)
 *   2. Save bloqué si erreur
 *   3. data-testid stables pour les jours/intervalles
 *   4. Backend error handling preserved
 */
import { readFileSync } from 'fs';
import { resolve } from 'path';
import { describe, it, expect } from 'vitest';

const root = resolve(__dirname, '../../../');
const readSrc = (...parts) => readFileSync(resolve(root, 'src', ...parts), 'utf-8');

// ============================================================
// A. Source-guard: ScheduleEditor structure
// ============================================================
describe('ScheduleEditor V1.1 — source structure', () => {
  const code = readSrc('pages', 'consumption', 'ScheduleEditor.jsx');

  it('imports validateDay from scheduleValidation', () => {
    expect(code).toMatch(/import.*validateDay.*scheduleValidation/);
  });

  it('manages intervals state (not openTime/closeTime)', () => {
    expect(code).toMatch(/useState.*scheduleToIntervals/);
  });

  it('has addSlot callback', () => {
    expect(code).toMatch(/addSlot/);
  });

  it('has removeSlot callback', () => {
    expect(code).toMatch(/removeSlot/);
  });

  it('has updateSlot callback', () => {
    expect(code).toMatch(/updateSlot/);
  });

  it('computes dayErrors via useMemo', () => {
    expect(code).toMatch(/dayErrors/);
    expect(code).toMatch(/useMemo/);
  });

  it('disables Save when hasErrors', () => {
    expect(code).toMatch(/disabled=\{.*hasErrors/);
  });

  it('has data-testid for day rows', () => {
    expect(code).toMatch(/data-testid=\{`day-row-/);
  });

  it('has data-testid for interval start/end inputs', () => {
    expect(code).toMatch(/data-testid=\{`interval-start-/);
    expect(code).toMatch(/data-testid=\{`interval-end-/);
  });

  it('has data-testid for day errors', () => {
    expect(code).toMatch(/data-testid=\{`day-error-/);
  });

  it('has data-testid for add-interval button', () => {
    expect(code).toMatch(/data-testid=\{`add-interval-/);
  });

  it('has data-testid for remove-interval button', () => {
    expect(code).toMatch(/data-testid=\{`remove-interval-/);
  });

  it('has data-testid for save button', () => {
    expect(code).toMatch(/data-testid="schedule-save"/);
  });

  it('applies red border on error', () => {
    expect(code).toMatch(/border-red-300/);
  });

  it('sends intervals_json in payload', () => {
    expect(code).toMatch(/intervals_json/);
  });
});

// ============================================================
// B. Source-guard: preserved features
// ============================================================
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

  it('handles legacy schedule conversion', () => {
    expect(code).toMatch(/scheduleToIntervals/);
  });

  it('converts intervals to legacy payload', () => {
    expect(code).toMatch(/intervalsToPayload/);
  });
});

// ============================================================
// C. Unit tests: validateDay
// ============================================================
describe('validateDay — unit tests', () => {
  const { validateDay } = require('../../pages/consumption/scheduleValidation.js');

  it('should accept empty slots (day closed)', () => {
    expect(validateDay([])).toEqual([]);
    expect(validateDay(null)).toEqual([]);
  });

  it('should accept a single valid interval', () => {
    expect(validateDay([{ start: '08:00', end: '19:00' }])).toEqual([]);
  });

  it('should accept multiple non-overlapping intervals', () => {
    const slots = [
      { start: '08:00', end: '12:00' },
      { start: '14:00', end: '18:00' },
    ];
    expect(validateDay(slots)).toEqual([]);
  });

  it('should accept adjacent intervals (end == next start)', () => {
    const slots = [
      { start: '08:00', end: '12:00' },
      { start: '12:00', end: '18:00' },
    ];
    expect(validateDay(slots)).toEqual([]);
  });

  it('should reject start >= end (midnight crossing)', () => {
    const errors = validateDay([{ start: '19:00', end: '08:00' }]);
    expect(errors.length).toBe(1);
    expect(errors[0]).toMatch(/d.but.*fin/i);
  });

  it('should reject start == end', () => {
    const errors = validateDay([{ start: '08:00', end: '08:00' }]);
    expect(errors.length).toBe(1);
  });

  it('should detect overlapping intervals', () => {
    const slots = [
      { start: '08:00', end: '14:00' },
      { start: '11:00', end: '18:00' },
    ];
    const errors = validateDay(slots);
    expect(errors.length).toBe(1);
    expect(errors[0]).toMatch(/[Cc]hevauchement/);
  });

  it('should detect overlap even when unsorted', () => {
    const slots = [
      { start: '14:00', end: '18:00' },
      { start: '08:00', end: '15:00' },
    ];
    const errors = validateDay(slots);
    expect(errors.length).toBe(1);
    expect(errors[0]).toMatch(/[Cc]hevauchement/);
  });

  it('should show readable error with times', () => {
    const slots = [
      { start: '08:00', end: '14:00' },
      { start: '11:00', end: '18:00' },
    ];
    const errors = validateDay(slots);
    // Should mention both time ranges
    expect(errors[0]).toContain('08:00');
    expect(errors[0]).toContain('14:00');
    expect(errors[0]).toContain('11:00');
    expect(errors[0]).toContain('18:00');
  });
});

// ============================================================
// D. ProfileHeatmapTab — useMemo optimization
// ============================================================
describe('ProfileHeatmapTab — useMemo optimization', () => {
  const code = readSrc('pages', 'consumption', 'ProfileHeatmapTab.jsx');

  it('uses useMemo for HeatmapGrid data', () => {
    expect(code).toMatch(/useMemo/);
  });

  it('uses useMemo for DailyProfileChart chartData', () => {
    expect(code).toMatch(/useMemo\(\(\)\s*=>\s*\(dailyProfile/);
  });
});

// ============================================================
// E. Backend service — V1 error handling
// ============================================================
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

// ============================================================
// F. Backend route — validate_intervals
// ============================================================
describe('Backend route — site_config.py V1.1', () => {
  const code = readFileSync(
    resolve(root, '..', 'backend', 'routes', 'site_config.py'),
    'utf-8'
  );

  it('defines validate_intervals function', () => {
    expect(code).toMatch(/def validate_intervals/);
  });

  it('checks for overlap in validation', () => {
    expect(code).toMatch(/overlap/);
  });

  it('checks for start >= end', () => {
    expect(code).toMatch(/start_ge_end/);
  });

  it('validates HH:MM format', () => {
    expect(code).toMatch(/HH_MM_RE/);
  });

  it('accepts intervals_json in ScheduleIn schema', () => {
    expect(code).toMatch(/intervals_json/);
  });

  it('returns intervals_json in response', () => {
    expect(code).toMatch(/intervals_json.*sched\.intervals_json/);
  });
});
