/**
 * actionDrawerSuite.test.js — V92
 * Source-guard tests for CreateActionDrawer, ActionDetailDrawer, ActionDrawerContext.
 * Tests 100% readFileSync + regex — no DOM mock needed.
 *
 * Sections:
 * A. CreateActionDrawer — structure (~8 tests)
 * B. CreateActionDrawer — DEADLINE_DAYS values (~4 tests)
 * C. ActionDetailDrawer — 5-tab structure (~8 tests)
 * D. ActionDrawerContext — provider (~8 tests)
 * E. Integration wiring (~4 tests)
 * F. a11y guards (~3 tests)
 */
import { readFileSync } from 'fs';
import { resolve } from 'path';
import { describe, it, expect } from 'vitest';

const root = resolve(__dirname, '../../../');
const readSrc = (...parts) => readFileSync(resolve(root, 'src', ...parts), 'utf-8');

// ============================================================
// A. CreateActionDrawer — structure
// ============================================================
describe('A · CreateActionDrawer — structure', () => {
  const code = readSrc('components', 'CreateActionDrawer.jsx');

  it('uses Drawer (not Modal)', () => {
    expect(code).toContain('Drawer');
    expect(code).not.toMatch(/import.*Modal.*from/);
  });

  it('imports createAction from API', () => {
    expect(code).toMatch(/import.*createAction.*from.*api/);
  });

  it('imports computeEvidenceRequirement', () => {
    expect(code).toContain('computeEvidenceRequirement');
  });

  it('exports DEADLINE_DAYS', () => {
    expect(code).toMatch(/export const DEADLINE_DAYS/);
  });

  it('has evidence_required toggle', () => {
    expect(code).toContain('evidence_required');
  });

  it('has form fields: titre, type, priorite, due_date, owner, description', () => {
    expect(code).toContain('titre');
    expect(code).toContain('type');
    expect(code).toContain('priorite');
    expect(code).toContain('due_date');
    expect(code).toContain('owner');
    expect(code).toContain('description');
  });

  it('has FR labels: "À planifier", "Conformité", "Critique"', () => {
    expect(code).toContain('À planifier');
    expect(code).toContain('Conformité');
    expect(code).toContain('Critique');
  });

  it('has "Créer une action" drawer title', () => {
    expect(code).toContain('Créer une action');
  });
});

// ============================================================
// B. CreateActionDrawer — DEADLINE_DAYS values
// ============================================================
describe('B · CreateActionDrawer — DEADLINE_DAYS values', () => {
  const code = readSrc('components', 'CreateActionDrawer.jsx');
  // Parse DEADLINE_DAYS from source: export const DEADLINE_DAYS = { critical: 7, high: 14, medium: 30, low: 60 };
  const match = code.match(/DEADLINE_DAYS\s*=\s*\{([^}]+)\}/);
  const raw = match ? match[1] : '';

  it('critical = 7', () => {
    expect(raw).toMatch(/critical:\s*7/);
  });

  it('high = 14', () => {
    expect(raw).toMatch(/high:\s*14/);
  });

  it('medium = 30', () => {
    expect(raw).toMatch(/medium:\s*30/);
  });

  it('low = 60', () => {
    expect(raw).toMatch(/low:\s*60/);
  });
});

// ============================================================
// C. ActionDetailDrawer — 5-tab structure
// ============================================================
describe('C · ActionDetailDrawer — 5-tab structure', () => {
  const code = readSrc('components', 'ActionDetailDrawer.jsx');

  it('has 5 tabs: detail, impact, evidence/pièces, commentaires, historique', () => {
    expect(code).toContain("'detail'");
    expect(code).toContain("'impact'");
    expect(code).toContain("'evidence'");
    expect(code).toContain("'comments'");
    expect(code).toContain("'history'");
  });

  it('has tab labels in FR', () => {
    expect(code).toContain('Detail');
    expect(code).toContain('Impact');
    expect(code).toMatch(/Pi[eè]ces/);
    expect(code).toContain('Commentaires');
    expect(code).toContain('Historique');
  });

  it('has closureJustification state', () => {
    expect(code).toContain('closureJustification');
  });

  it('has evidence_required display', () => {
    expect(code).toContain('evidence_required');
  });

  it('has handleStatusChange with done check', () => {
    expect(code).toContain('handleStatusChange');
    expect(code).toMatch(/done|terminee|Terminée/i);
  });

  it('imports checkActionCloseability', () => {
    expect(code).toContain('checkActionCloseability');
  });

  it('has data-testid for E2E targeting', () => {
    expect(code).toContain('data-testid=');
  });

  it('defines TABS constant', () => {
    expect(code).toMatch(/const TABS\s*=/);
  });
});

// ============================================================
// D. ActionDrawerContext — provider
// ============================================================
describe('D · ActionDrawerContext — provider', () => {
  const code = readSrc('contexts', 'ActionDrawerContext.jsx');

  it('exports ActionDrawerProvider', () => {
    expect(code).toMatch(/export function ActionDrawerProvider/);
  });

  it('exports useActionDrawer', () => {
    expect(code).toMatch(/export function useActionDrawer/);
  });

  it('renders CreateActionDrawer internally', () => {
    expect(code).toContain('CreateActionDrawer');
  });

  it('passes open, onClose, onSave, prefill props to drawer', () => {
    expect(code).toContain('open');
    expect(code).toContain('onClose');
    expect(code).toContain('onSave');
    expect(code).toContain('prefill');
  });

  it('passes siteId, sourceType, sourceId props', () => {
    expect(code).toContain('siteId');
    expect(code).toContain('sourceType');
    expect(code).toContain('sourceId');
  });

  it('passes idempotencyKey prop', () => {
    expect(code).toContain('idempotencyKey');
  });

  it('passes evidenceRequired prop', () => {
    expect(code).toContain('evidenceRequired');
  });

  it('has idempotency check (_existed)', () => {
    expect(code).toContain('_existed');
  });
});

// ============================================================
// E. Integration wiring
// ============================================================
describe('E · Integration wiring', () => {
  it('AppShell imports ActionDrawerProvider', () => {
    const code = readSrc('layout', 'AppShell.jsx');
    expect(code).toContain('ActionDrawerProvider');
  });

  it('at least 10 pages use useActionDrawer', () => {
    const migratedPages = [
      'ConformitePage.jsx',
      'AnomaliesPage.jsx',
      'ActionsPage.jsx',
      'Patrimoine.jsx',
      'CompliancePipelinePage.jsx',
      'SiteCompliancePage.jsx',
      'BillIntelPage.jsx',
      'BillingPage.jsx',
      'ConsumptionDiagPage.jsx',
      'MonitoringPage.jsx',
    ];
    let count = 0;
    for (const page of migratedPages) {
      try {
        const src = readSrc('pages', page);
        if (src.includes('useActionDrawer')) count++;
      } catch {
        /* file may not exist */
      }
    }
    expect(count).toBeGreaterThanOrEqual(10);
  });

  it('AnomaliesPage does not import AnomalyActionModal directly', () => {
    const code = readSrc('pages', 'AnomaliesPage.jsx');
    expect(code).not.toMatch(/import.*AnomalyActionModal/);
    expect(code).toContain('useActionDrawer');
  });

  it('SiteAnomalyPanel does not import AnomalyActionModal directly', () => {
    const code = readSrc('components', 'SiteAnomalyPanel.jsx');
    expect(code).not.toMatch(/import.*AnomalyActionModal/);
    expect(code).toContain('useActionDrawer');
  });
});

// ============================================================
// F. a11y guards
// ============================================================
describe('F · a11y guards', () => {
  it('CreateActionDrawer has accessible form labels', () => {
    const code = readSrc('components', 'CreateActionDrawer.jsx');
    expect(code).toMatch(/aria-|role=|<label|label=/);
  });

  it('ActionDetailDrawer has testable landmarks', () => {
    const code = readSrc('components', 'ActionDetailDrawer.jsx');
    expect(code).toMatch(/aria-|role=|data-testid=/);
  });

  it('form inputs have associated labels', () => {
    const code = readSrc('components', 'CreateActionDrawer.jsx');
    // Check that the form has label elements
    expect(code).toMatch(/<label/);
  });
});
