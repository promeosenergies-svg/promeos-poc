/**
 * v98GuidanceLayer.test.js — V98 "Grand Public Guidance Layer" source guards
 *
 * Verifies:
 *   A. Site360 Simple/Expert mode toggle
 *   B. Site360 NBA rendering + CTA
 *   C. Site360 EvidenceSummaryModal + "Résumé 1 page" button
 *   D. api.js V98 functions
 *   E. Backend reconciliation_service V98 (translations, NBA, evidence summary)
 *   F. Backend routes V98 (evidence/summary endpoint)
 */
import { describe, test, expect } from 'vitest';
import { readFileSync } from 'fs';
import path from 'path';

const src = (rel) => readFileSync(path.resolve(__dirname, '..', '..', rel), 'utf8');
const backend = (rel) => readFileSync(path.resolve(__dirname, '..', '..', '..', '..', 'backend', rel), 'utf8');

const SITE360 = src('pages/Site360.jsx');
const API_JS = src('services/api.js');

// ── A. Simple/Expert mode toggle ─────────────────────────────────────

describe('A. Site360 Simple/Expert mode toggle', () => {
  test('has mode state with simple default', () => {
    expect(SITE360).toMatch(/useState\(['"]simple['"]\)/);
  });

  test('has Simple button label', () => {
    expect(SITE360).toMatch(/Simple/);
  });

  test('has Expert button label', () => {
    expect(SITE360).toMatch(/Expert/);
  });

  test('has setMode function', () => {
    expect(SITE360).toMatch(/setMode/);
  });

  test('renders simple mode block conditionally', () => {
    expect(SITE360).toMatch(/mode\s*===\s*['"]simple['"]/);
  });

  test('renders expert mode block conditionally', () => {
    expect(SITE360).toMatch(/mode\s*===\s*['"]expert['"]/);
  });
});

// ── B. NBA rendering + CTA ──────────────────────────────────────────

describe('B. NBA rendering and CTA', () => {
  test('accesses next_best_action from recon data', () => {
    expect(SITE360).toMatch(/next_best_action/);
  });

  test('has handleNbaFix function', () => {
    expect(SITE360).toMatch(/handleNbaFix/);
  });

  test('has scoreGain state', () => {
    expect(SITE360).toMatch(/scoreGain/);
  });

  test('has setScoreGain setter', () => {
    expect(SITE360).toMatch(/setScoreGain/);
  });

  test('renders NBA action label', () => {
    expect(SITE360).toMatch(/nba\.action_label|nba\?.action_label/);
  });

  test('renders Appliquer or similar CTA button', () => {
    expect(SITE360).toMatch(/Appliquer/);
  });

  test('shows score gain animation', () => {
    expect(SITE360).toMatch(/Score \+/);
  });

  test('has Sparkles icon import', () => {
    expect(SITE360).toMatch(/Sparkles/);
  });

  test('renders "Prochaine action" or NBA heading', () => {
    expect(SITE360).toMatch(/Prochaine action|action recommandée/);
  });
});

// ── C. EvidenceSummaryModal + "Résumé 1 page" ───────────────────────

describe('C. EvidenceSummaryModal', () => {
  test('has EvidenceSummaryModal component', () => {
    expect(SITE360).toMatch(/function\s+EvidenceSummaryModal/);
  });

  test('has showSummaryModal state', () => {
    expect(SITE360).toMatch(/showSummaryModal/);
  });

  test('has "Résumé 1 page" button text', () => {
    expect(SITE360).toMatch(/Résumé 1 page/);
  });

  test('imports getReconciliationEvidenceSummary', () => {
    expect(SITE360).toMatch(/getReconciliationEvidenceSummary/);
  });

  test('has print button in modal', () => {
    expect(SITE360).toMatch(/window\.print|Imprimer/);
  });

  test('modal renders site name', () => {
    expect(SITE360).toMatch(/site\.nom/);
  });

  test('renders key_checks section', () => {
    expect(SITE360).toMatch(/key_checks/);
  });

  test('renders remaining_actions section', () => {
    expect(SITE360).toMatch(/remaining_actions/);
  });

  test('has FileText icon import', () => {
    expect(SITE360).toMatch(/FileText/);
  });

  test('has X icon import for modal close', () => {
    expect(SITE360).toMatch(/\bX\b/);
  });
});

// ── D. Simple mode content blocks ───────────────────────────────────

describe('D. Simple mode content', () => {
  test('has "État du site" or score label in Simple mode', () => {
    expect(SITE360).toMatch(/État du site|score/i);
  });

  test('has "Ce qui bloque" heading', () => {
    expect(SITE360).toMatch(/Ce qui bloque/);
  });

  test('renders why_it_matters for checks', () => {
    expect(SITE360).toMatch(/why_it_matters/);
  });

  test('renders title_simple for checks', () => {
    expect(SITE360).toMatch(/title_simple/);
  });

  test('renders impact_label for checks', () => {
    expect(SITE360).toMatch(/impact_label/);
  });

  test('has "Voir détails" link to switch to expert', () => {
    expect(SITE360).toMatch(/Voir détails.*expert|mode expert/i);
  });
});

// ── E. api.js V98 functions ─────────────────────────────────────────

describe('E. api.js V98', () => {
  test('has getReconciliationEvidenceSummary', () => {
    expect(API_JS).toMatch(/getReconciliationEvidenceSummary/);
  });

  test('calls evidence/summary endpoint', () => {
    expect(API_JS).toMatch(/evidence\/summary/);
  });
});

// ── F. Backend reconciliation_service V98 ───────────────────────────

describe('F. Backend reconciliation_service V98', () => {
  const SVC = backend('services/reconciliation_service.py');

  test('has CHECK_TRANSLATION dict', () => {
    expect(SVC).toMatch(/CHECK_TRANSLATION\s*=/);
  });

  test('has ACTION_TRANSLATION dict', () => {
    expect(SVC).toMatch(/ACTION_TRANSLATION\s*=/);
  });

  test('has _CHECK_PRIORITY list', () => {
    expect(SVC).toMatch(/_CHECK_PRIORITY\s*=/);
  });

  test('has _SCORE_GAIN_PER_CHECK constant', () => {
    expect(SVC).toMatch(/_SCORE_GAIN_PER_CHECK\s*=/);
  });

  test('has _compute_next_best_action function', () => {
    expect(SVC).toMatch(/def _compute_next_best_action/);
  });

  test('has get_evidence_summary function', () => {
    expect(SVC).toMatch(/def get_evidence_summary/);
  });

  test('CHECK_TRANSLATION has has_delivery_points', () => {
    expect(SVC).toMatch(/has_delivery_points.*title_simple/s);
  });

  test('CHECK_TRANSLATION has has_active_contract', () => {
    expect(SVC).toMatch(/has_active_contract.*title_simple/s);
  });

  test('ACTION_TRANSLATION has create_delivery_point', () => {
    expect(SVC).toMatch(/create_delivery_point.*label_simple/s);
  });

  test('ACTION_TRANSLATION has extend_contract', () => {
    expect(SVC).toMatch(/extend_contract.*label_simple/s);
  });

  test('ACTION_TRANSLATION has navigate_import', () => {
    expect(SVC).toMatch(/navigate_import.*label_simple/s);
  });

  test('reconcile_site enriches with title_simple', () => {
    expect(SVC).toMatch(/title_simple/);
  });

  test('reconcile_site returns next_best_action', () => {
    expect(SVC).toMatch(/next_best_action/);
  });
});

// ── G. Backend routes V98 ───────────────────────────────────────────

describe('G. Backend routes V98', () => {
  const ROUTES = backend('routes/patrimoine.py');

  test('has evidence/summary endpoint', () => {
    expect(ROUTES).toMatch(/evidence\/summary/);
  });

  test('has get_reconciliation_evidence_summary function', () => {
    expect(ROUTES).toMatch(/get_reconciliation_evidence_summary/);
  });

  test('imports get_evidence_summary from service', () => {
    expect(ROUTES).toMatch(/get_evidence_summary/);
  });
});
