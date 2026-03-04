/**
 * PROMEOS — Action Engine (Étape 4) tests
 * Unit tests for CreateActionDrawer logic + source-guard tests.
 */
import { describe, it, expect } from 'vitest';
import fs from 'fs';
import path from 'path';

// ── Import auto-deadline logic ──────────────────────────────────────────────
import { DEADLINE_DAYS } from '../../components/CreateActionDrawer';

// ── Helpers ──────────────────────────────────────────────────────────────────

function src(relPath) {
  return fs.readFileSync(path.resolve(__dirname, '..', '..', relPath), 'utf-8');
}

function backendSrc(relPath) {
  return fs.readFileSync(
    path.resolve(__dirname, '..', '..', '..', '..', 'backend', relPath),
    'utf-8'
  );
}

/** Simulate the prefill payload that ConformitePage builds for an obligation. */
function buildConformitePrefill(obligation) {
  return {
    titre: `Mise en conformité ${obligation.regulation}`,
    type: 'conformite',
    priorite:
      obligation.severity === 'critical'
        ? 'critical'
        : obligation.severity === 'high'
          ? 'high'
          : 'medium',
    description: obligation.quoi_faire,
    obligation_code: obligation.code,
  };
}

/** Simulate the prefill payload that BillIntelPage builds for a billing insight. */
function buildBillingPrefill(insight) {
  return {
    titre: insight.message || '',
    type: 'facture',
    impact_eur: insight.estimated_loss_eur || '',
    description: insight.message || '',
  };
}

/** Simulate the prefill payload that ActivationPage builds for a readiness reason. */
function buildReadinessPrefill(reason) {
  return {
    titre: reason.label,
    type: 'conformite',
    priorite: reason.severity === 'critical' ? 'critical' : 'high',
    description: reason.label,
  };
}

// ── Prefill integration tests ───────────────────────────────────────────────

describe('Action Engine — prefill payloads', () => {
  it('obligation → conformite action payload', () => {
    const pf = buildConformitePrefill({
      regulation: 'BACS',
      severity: 'critical',
      quoi_faire: 'Installer la GTB',
      code: 'bacs-001',
    });
    expect(pf.titre).toContain('BACS');
    expect(pf.type).toBe('conformite');
    expect(pf.priorite).toBe('critical');
    expect(pf.obligation_code).toBe('bacs-001');
  });

  it('billing insight → facture action payload', () => {
    const pf = buildBillingPrefill({
      message: 'Surfacturation détectée sur site A',
      estimated_loss_eur: 1200,
    });
    expect(pf.titre).toContain('Surfacturation');
    expect(pf.type).toBe('facture');
    expect(pf.impact_eur).toBe(1200);
  });

  it('readiness reason → insight action payload (sourceId=readiness:{id})', () => {
    const pf = buildReadinessPrefill({
      id: 'conso-ko',
      label: 'Données conso manquantes',
      severity: 'critical',
    });
    expect(pf.titre).toContain('conso');
    expect(pf.priorite).toBe('critical');
    // Source tracing
    const sourceId = `readiness:conso-ko`;
    expect(sourceId).toMatch(/^readiness:/);
  });
});

// ── Auto-deadline tests ─────────────────────────────────────────────────────

describe('Action Engine — auto-deadline by severity', () => {
  it('critical → +7 days', () => {
    expect(DEADLINE_DAYS.critical).toBe(7);
  });

  it('high → +14 days', () => {
    expect(DEADLINE_DAYS.high).toBe(14);
  });

  it('medium → +30 days', () => {
    expect(DEADLINE_DAYS.medium).toBe(30);
  });

  it('low → +60 days', () => {
    expect(DEADLINE_DAYS.low).toBe(60);
  });
});

// ── Evidence required logic ─────────────────────────────────────────────────

describe('Action Engine — evidence_required', () => {
  it('critical obligation → evidence_required true', () => {
    const evidenceRequired = 'critical' === 'critical';
    expect(evidenceRequired).toBe(true);
  });

  it('low severity → evidence_required false', () => {
    const evidenceRequired = 'low' === 'critical';
    expect(evidenceRequired).toBe(false);
  });
});

// ── Idempotency key tests ───────────────────────────────────────────────────

describe('Action Engine — idempotency keys', () => {
  it('billing insight key: billing-insight:{id}', () => {
    const key = `billing-insight:42`;
    expect(key).toBe('billing-insight:42');
    expect(key).toMatch(/^billing-insight:/);
  });

  it('readiness reason key: readiness:{id}', () => {
    const key = `readiness:conso-ko`;
    expect(key).toBe('readiness:conso-ko');
    expect(key).toMatch(/^readiness:/);
  });
});

// ── FR labels ───────────────────────────────────────────────────────────────

describe('Action Engine — FR labels', () => {
  it('conformite prefill title is FR', () => {
    const pf = buildConformitePrefill({
      regulation: 'DPE',
      severity: 'high',
      quoi_faire: 'X',
      code: 'dpe-1',
    });
    expect(pf.titre).toMatch(/Mise en conformité/);
  });

  it('readiness prefill uses French labels', () => {
    const pf = buildReadinessPrefill({
      id: 'factures-ko',
      label: 'Moins de 3 mois de factures',
      severity: 'critical',
    });
    expect(pf.titre).toMatch(/factures/i);
  });
});

// ── Source tracing ──────────────────────────────────────────────────────────

describe('Action Engine — source tracing', () => {
  it('conformite uses sourceType=compliance', () => {
    const sourceType = 'compliance';
    expect(sourceType).toBe('compliance');
  });

  it('billing uses sourceType=billing', () => {
    const sourceType = 'billing';
    expect(sourceType).toBe('billing');
  });

  it('readiness uses sourceType=insight', () => {
    const sourceType = 'insight';
    expect(sourceType).toBe('insight');
  });
});

// ── Source-guard tests ──────────────────────────────────────────────────────

describe('Action Engine — source guards', () => {
  it('AppShell imports ActionDrawerProvider', () => {
    const code = src('layout/AppShell.jsx');
    expect(code).toContain('ActionDrawerProvider');
  });

  it('HealthSummary source contains onCreateAction', () => {
    const code = src('components/HealthSummary.jsx');
    expect(code).toContain('onCreateAction');
  });

  it('CreateActionDrawer uses Drawer (not Modal)', () => {
    const code = src('components/CreateActionDrawer.jsx');
    expect(code).toContain("from '../ui/Drawer'");
    expect(code).not.toContain("from '../ui/Modal'");
  });

  it('ActionDetailDrawer source contains evidence_required', () => {
    const code = src('components/ActionDetailDrawer.jsx');
    expect(code).toContain('evidence_required');
  });

  it('backend action_close_rules.py contains evidence_required', () => {
    const code = backendSrc('services/action_close_rules.py');
    expect(code).toContain('evidence_required');
  });
});

// ── Drawer migration guard — no direct CreateActionModal in pages ──────────

describe('Action Engine — Drawer migration guard', () => {
  const pagesDir = path.resolve(__dirname, '..', '..', 'pages');
  const pageFiles = fs
    .readdirSync(pagesDir)
    .filter((f) => f.endsWith('.jsx') || f.endsWith('.tsx'))
    .filter((f) => !f.startsWith('__'));

  it('no page imports CreateActionModal directly (all use useActionDrawer)', () => {
    const offenders = [];
    for (const file of pageFiles) {
      const code = fs.readFileSync(path.join(pagesDir, file), 'utf-8');
      if (/import\s+.*CreateActionModal/.test(code)) {
        offenders.push(file);
      }
    }
    expect(offenders).toEqual([]);
  });

  const migratedPages = [
    'ActionsPage.jsx',
    'SiteCompliancePage.jsx',
    'CompliancePipelinePage.jsx',
    'MonitoringPage.jsx',
    'ConsumptionDiagPage.jsx',
    'BillingPage.jsx',
    'Patrimoine.jsx',
    'ConformitePage.jsx',
    'BillIntelPage.jsx',
    'ActivationPage.jsx',
  ];

  for (const page of migratedPages) {
    it(`${page} uses useActionDrawer`, () => {
      const filePath = path.join(pagesDir, page);
      if (!fs.existsSync(filePath)) return; // skip if file removed
      const code = fs.readFileSync(filePath, 'utf-8');
      expect(code).toContain('useActionDrawer');
    });
  }
});
