/**
 * PROMEOS — Sprint P2 "Workflow Continuity & Action Credibility"
 * Source-guard tests — verify structural improvements.
 */
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { resolve } from 'path';

const ROOT = 'c:/Users/amine/promeos-poc/promeos-poc/frontend/src';

function read(relPath) {
  return readFileSync(resolve(ROOT, relPath), 'utf-8');
}

// ── P2-1: Source → Action chain ──────────────────────────────────────────

describe('P2-1: Source → Action chain', () => {
  const drawer = read('components/CreateActionDrawer.jsx');

  it('source context shows colored badge per sourceType', () => {
    expect(drawer).toContain('compliance');
    expect(drawer).toContain('billing');
    expect(drawer).toContain('Facturation');
    expect(drawer).toContain('Anomalie');
    expect(drawer).toContain('Achats');
  });

  it('auto-rationale is generated from source context', () => {
    expect(drawer).toContain('Action créée depuis');
    expect(drawer).toContain('Réf. source');
    expect(drawer).toContain('Impact estimé');
  });

  it('shows impact estimate in source block when available', () => {
    expect(drawer).toContain('Impact estimé');
    expect(drawer).toContain('toLocaleString');
  });
});

// ── P2-2: Action detail credibility ──────────────────────────────────────

describe('P2-2: Action detail credibility', () => {
  const detail = read('components/ActionDetailDrawer.jsx');

  it('resolves site name from ScopeContext', () => {
    expect(detail).toContain('useScope');
    expect(detail).toContain('orgSites');
    expect(detail).toContain('siteName');
  });

  it('displays created_at date', () => {
    expect(detail).toContain('Créée le');
    expect(detail).toContain('created_at');
  });

  it('shows overdue indicator in detail', () => {
    expect(detail).toContain('En retard');
    expect(detail).toContain('new Date(d.due_date)');
  });

  it('shows temporal progress bar', () => {
    expect(detail).toContain('Progression temporelle');
    expect(detail).toContain('Dépassé');
  });
});

// ── P2-3: Evidence / Preuves ─────────────────────────────────────────────

describe('P2-3: Evidence / Preuves', () => {
  const detail = read('components/ActionDetailDrawer.jsx');

  it('has evidence type selector', () => {
    expect(detail).toContain('EVIDENCE_TYPE_OPTIONS');
    expect(detail).toContain('Facture');
    expect(detail).toContain('Rapport');
    expect(detail).toContain('Attestation');
    expect(detail).toContain('Contrat');
  });

  it('has evidence date field', () => {
    expect(detail).toContain('evidenceDate');
    expect(detail).toContain('type="date"');
  });

  it('shows evidence progress bar when required', () => {
    expect(detail).toContain('Preuve requise pour clôturer');
    expect(detail).toContain('evidence_required');
  });

  it('prefixes evidence label with type and date', () => {
    expect(detail).toContain('typePrefix');
    expect(detail).toContain('datePrefix');
  });
});

// ── P2-4: Clôture / Statut / Traçabilité ────────────────────────────────

describe('P2-4: Clôture / Statut / Traçabilité', () => {
  const detail = read('components/ActionDetailDrawer.jsx');

  it('shows close form for ALL actions, not just OPERAT', () => {
    // P2-4 comment in code
    expect(detail).toContain('P2-4');
    expect(detail).toContain('close-form');
  });

  it('has close confirmation with comment field', () => {
    expect(detail).toContain('Confirmer la clôture');
    expect(detail).toContain('Commentaire de clôture');
    expect(detail).toContain('closure-justification');
  });

  it('allows closing with or without comment for regular actions', () => {
    expect(detail).toContain('Clôturer avec commentaire');
    expect(detail).toContain('Clôturer sans commentaire');
  });

  it('still enforces strict close for OPERAT/evidence_required', () => {
    expect(detail).toContain('isOperatAction');
    expect(detail).toContain('evidence_required');
    expect(detail).toContain('closureJustification.trim().length < 10');
  });

  it('displays closure justification when present', () => {
    expect(detail).toContain('Justification de clôture');
    expect(detail).toContain('closure_justification');
  });
});

// ── P2-5: Deeplinks ─────────────────────────────────────────────────────

describe('P2-5: Deeplinks', () => {
  const rules = read('models/evidenceRules.js');

  it('compliance deeplink includes tab parameter', () => {
    expect(rules).toContain('/conformite?tab=obligations');
  });

  it('consumption deeplink goes to explorer', () => {
    expect(rules).toContain('/consommations/explorer');
  });

  it('purchase deeplink goes to /achats', () => {
    expect(rules).toContain('/achats');
  });

  it('operat deeplink includes EFA ID', () => {
    expect(rules).toContain('`/conformite/tertiaire/efa/${efaId}`');
  });

  it('anomaly source has deeplink', () => {
    expect(rules).toContain("case 'anomaly'");
    expect(rules).toContain('/anomalies');
  });
});

// ── P2-6: Kanban / Actions list ──────────────────────────────────────────

describe('P2-6: Kanban credibility', () => {
  const actions = read('pages/ActionsPage.jsx');

  it('kanban cards show due date', () => {
    expect(actions).toContain('CalendarDays');
    expect(actions).toContain('a.due_date');
  });

  it('kanban cards show evidence badge', () => {
    expect(actions).toContain('evidence_required');
    expect(actions).toContain('Preuve');
  });

  it('kanban columns have reduced min-height', () => {
    expect(actions).toContain('min-h-[200px]');
  });

  it('has progress summary bar with completion rate', () => {
    expect(actions).toContain('Avancement global');
    expect(actions).toContain('terminées');
  });

  it('progress bar shows stacked segments (done, in_progress, planned)', () => {
    expect(actions).toContain('bg-green-500');
    expect(actions).toContain('bg-amber-400');
    expect(actions).toContain('bg-blue-300');
  });
});

// ── P2-7: Alignment ─────────────────────────────────────────────────────

describe('P2-7: Unified action system alignment', () => {
  it('all key pages use ActionDrawerContext', () => {
    const pages = [
      'pages/ActionsPage.jsx',
      'pages/ConformitePage.jsx',
      'pages/BillIntelPage.jsx',
      'pages/AnomaliesPage.jsx',
      'pages/MonitoringPage.jsx',
    ];
    for (const p of pages) {
      const src = read(p);
      expect(src).toContain('useActionDrawer');
    }
  });

  it('CreateActionDrawer is the single entry point', () => {
    const ctx = read('contexts/ActionDrawerContext.jsx');
    expect(ctx).toContain('CreateActionDrawer');
    expect(ctx).toContain('openActionDrawer');
  });

  it('backend and frontend deeplinks are aligned', () => {
    const backend = readFileSync(
      resolve('c:/Users/amine/promeos-poc/promeos-poc/backend/routes/actions.py'),
      'utf-8'
    );
    const frontend = read('models/evidenceRules.js');
    // Both should have the same deeplink patterns
    expect(backend).toContain('/conformite?tab=obligations');
    expect(frontend).toContain('/conformite?tab=obligations');
    expect(backend).toContain('/consommations/explorer');
    expect(frontend).toContain('/consommations/explorer');
  });
});
