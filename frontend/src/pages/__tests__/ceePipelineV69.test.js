/**
 * PROMEOS — CEE Pipeline V69 — Source-guard + structure tests
 * Tests 100% readFileSync / regex — no DOM mock needed.
 *
 * A. SiteCompliancePage V69 enhancements
 * B. API: V69 endpoint functions exported
 * C. Backend model: cee_models.py structure
 * D. Backend engine: V69 functions
 * E. Backend routes: V69 endpoints
 */
import { readFileSync, existsSync } from 'fs';
import { resolve } from 'path';
import { describe, it, expect } from 'vitest';

const root = resolve(__dirname, '../../../');
const readSrc = (...parts) => readFileSync(resolve(root, 'src', ...parts), 'utf-8');
const backendRoot = resolve(root, '../backend');
const readBackend = (...parts) => readFileSync(resolve(backendRoot, ...parts), 'utf-8');

// ============================================================
// A. SiteCompliancePage V69 enhancements
// ============================================================
describe('A · SiteCompliancePage V69 — Plan tab cockpit', () => {
  const code = readSrc('pages', 'SiteCompliancePage.jsx');

  it('has data-section="work-packages"', () => {
    expect(code).toContain('data-section="work-packages"');
  });

  it('has data-section="kanban-cee"', () => {
    expect(code).toContain('data-section="kanban-cee"');
  });

  it('has data-section="mv-widget"', () => {
    expect(code).toContain('data-section="mv-widget"');
  });

  it('has "Créer dossier CEE" CTA', () => {
    expect(code).toContain('Créer dossier CEE');
  });

  it('has data-testid="cta-add-package"', () => {
    expect(code).toContain('data-testid="cta-add-package"');
  });

  it('has data-testid="pkg-label-input"', () => {
    expect(code).toContain('data-testid="pkg-label-input"');
  });

  it('has data-testid="pkg-size-select"', () => {
    expect(code).toContain('data-testid="pkg-size-select"');
  });

  it('has data-testid="pkg-submit"', () => {
    expect(code).toContain('data-testid="pkg-submit"');
  });

  it('renders S/M/L size badges', () => {
    expect(code).toContain("SIZE_BADGE");
    expect(code).toContain("'S'");
    expect(code).toContain("'M'");
    expect(code).toContain("'L'");
  });

  it('renders CEE status badges (a_qualifier/ok/non)', () => {
    expect(code).toContain('CEE_STATUS_BADGE');
    expect(code).toContain('a_qualifier');
    expect(code).toContain("'CEE OK'");
  });

  it('renders CEE kanban steps array', () => {
    expect(code).toContain("CEE_STEPS");
    expect(code).toContain("'devis'");
    expect(code).toContain("'engagement'");
    expect(code).toContain("'travaux'");
    expect(code).toContain("'pv_photos'");
    expect(code).toContain("'mv'");
    expect(code).toContain("'versement'");
  });

  it('renders kanban step labels', () => {
    expect(code).toContain('CEE_STEP_LABELS');
    expect(code).toContain("Devis");
    expect(code).toContain("Engagement");
    expect(code).toContain("Travaux");
    expect(code).toContain("PV+Photos");
    expect(code).toContain("Versement");
  });

  it('imports KanbanCee component', () => {
    expect(code).toContain('KanbanCee');
  });

  it('imports MvWidget component', () => {
    expect(code).toContain('MvWidget');
  });

  it('imports V69 API functions', () => {
    expect(code).toContain('getSiteWorkPackages');
    expect(code).toContain('createWorkPackage');
    expect(code).toContain('createCeeDossier');
    expect(code).toContain('advanceCeeStep');
    expect(code).toContain('getMvSummary');
  });

  it('shows M&V baseline and delta', () => {
    expect(code).toContain('baseline_kwh_month');
    expect(code).toContain('current_kwh_month');
    expect(code).toContain('delta_pct');
  });

  it('shows M&V alerts', () => {
    expect(code).toContain('a.severity');
    expect(code).toContain('a.message');
  });

  // V68 backward compat
  it('still has data-section="tab-plan"', () => {
    expect(code).toContain('data-section="tab-plan"');
  });

  it('still has data-testid="cta-creer-action-plan" (V68)', () => {
    expect(code).toContain('data-testid="cta-creer-action-plan"');
  });

  it('still has data-testid="cta-creer-action-empty" (V68)', () => {
    expect(code).toContain('data-testid="cta-creer-action-empty"');
  });

  it('still has 3 tabs: obligations, preuves, plan', () => {
    expect(code).toContain("'obligations'");
    expect(code).toContain("'preuves'");
    expect(code).toContain("'plan'");
  });

  it('still uses useActionDrawer with siteId + compliance context', () => {
    expect(code).toContain('useActionDrawer');
    expect(code).toContain('siteId: parseInt(siteId)');
    expect(code).toContain("sourceType: 'compliance'");
  });

  it('still has data-section="site-compliance"', () => {
    expect(code).toContain('data-section="site-compliance"');
  });

  it('still has Data Readiness Gate section', () => {
    expect(code).toContain('Data Readiness Gate');
    expect(code).toContain('gate_status');
  });

  it('still shows scores strip (4 metrics)', () => {
    expect(code).toContain('reg_risk');
    expect(code).toContain('evidence_risk');
    expect(code).toContain('financial_opportunity_eur');
    expect(code).toContain('trust_score');
  });
});

// ============================================================
// B. API: V69 endpoint functions exported
// ============================================================
describe('B · API V69 endpoint functions', () => {
  const code = readSrc('services', 'api.js');

  it('exports getSiteWorkPackages', () => {
    expect(code).toContain('export const getSiteWorkPackages');
  });

  it('exports createWorkPackage', () => {
    expect(code).toContain('export const createWorkPackage');
  });

  it('exports createCeeDossier', () => {
    expect(code).toContain('export const createCeeDossier');
  });

  it('exports advanceCeeStep', () => {
    expect(code).toContain('export const advanceCeeStep');
  });

  it('exports getMvSummary', () => {
    expect(code).toContain('export const getMvSummary');
  });

  it('calls /compliance/sites/{siteId}/packages', () => {
    expect(code).toContain('/compliance/sites/${siteId}/packages');
  });

  it('calls /compliance/sites/{siteId}/cee/dossier', () => {
    expect(code).toContain('/compliance/sites/${siteId}/cee/dossier');
  });

  it('calls /compliance/sites/{siteId}/mv/summary', () => {
    expect(code).toContain('/compliance/sites/${siteId}/mv/summary');
  });

  it('calls /compliance/cee/dossier/{dossierId}/step', () => {
    expect(code).toContain('/compliance/cee/dossier/${dossierId}/step');
  });
});

// ============================================================
// C. Backend model: cee_models.py structure
// ============================================================
describe('C · Backend cee_models.py structure', () => {
  const code = readBackend('models', 'cee_models.py');

  it('defines WorkPackage model', () => {
    expect(code).toContain('class WorkPackage(');
    expect(code).toContain('__tablename__ = "work_packages"');
  });

  it('defines CeeDossier model', () => {
    expect(code).toContain('class CeeDossier(');
    expect(code).toContain('__tablename__ = "cee_dossiers"');
  });

  it('defines CeeDossierEvidence model', () => {
    expect(code).toContain('class CeeDossierEvidence(');
    expect(code).toContain('__tablename__ = "cee_dossier_evidences"');
  });

  it('WorkPackage has capex_eur, savings, payback, size, cee_status', () => {
    expect(code).toContain('capex_eur');
    expect(code).toContain('savings_eur_year');
    expect(code).toContain('payback_years');
    expect(code).toContain('WorkPackageSize');
    expect(code).toContain('CeeStatus');
  });

  it('CeeDossier has current_step and action_ids_json', () => {
    expect(code).toContain('current_step');
    expect(code).toContain('CeeDossierStep');
    expect(code).toContain('action_ids_json');
  });

  it('CeeDossierEvidence links to Evidence coffre', () => {
    expect(code).toContain('evidence_id');
    expect(code).toContain('ForeignKey("evidences.id")');
  });
});

// ============================================================
// D. Backend engine: V69 functions
// ============================================================
describe('D · Backend compliance_engine V69 functions', () => {
  const code = readBackend('services', 'compliance_engine.py');

  it('defines create_cee_dossier function', () => {
    expect(code).toContain('def create_cee_dossier(');
  });

  it('defines advance_cee_step function', () => {
    expect(code).toContain('def advance_cee_step(');
  });

  it('defines compute_mv_summary function', () => {
    expect(code).toContain('def compute_mv_summary(');
  });

  it('defines get_site_work_packages function', () => {
    expect(code).toContain('def get_site_work_packages(');
  });

  it('has _CEE_EVIDENCE_TEMPLATE with 7 items', () => {
    expect(code).toContain('_CEE_EVIDENCE_TEMPLATE');
    expect(code).toContain('"devis"');
    expect(code).toContain('"pv_reception"');
    expect(code).toContain('"photos_chantier"');
    expect(code).toContain('"rapport_mv"');
    expect(code).toContain('"attestation_fin"');
    expect(code).toContain('"facture_travaux"');
    expect(code).toContain('"engagement"');
  });

  it('creates Evidence in site coffre during dossier creation', () => {
    expect(code).toContain('site_evidence = Evidence(');
    expect(code).toContain('evidence_id=site_evidence.id');
  });

  it('creates ActionItem for each kanban step', () => {
    expect(code).toContain('ActionItem(');
    expect(code).toContain('source_type=ActionSourceType.COMPLIANCE');
    expect(code).toContain('cee_dossier:');
    expect(code).toContain('cee_step:');
  });

  it('advance_cee_step marks past actions as DONE', () => {
    expect(code).toContain('ActionStatus.DONE');
    expect(code).toContain('ActionStatus.IN_PROGRESS');
  });

  it('compute_mv_summary uses annual_kwh_total as baseline', () => {
    expect(code).toContain('baseline_kwh_month');
    expect(code).toContain('annual_kwh_total');
  });

  it('compute_mv_summary generates drift alert', () => {
    expect(code).toContain('MVAlertType.BASELINE_DRIFT');
    expect(code).toContain('delta_pct > 10');
  });

  it('compute_mv_summary generates data_missing alert', () => {
    expect(code).toContain('MVAlertType.DATA_MISSING');
  });

  it('compute_mv_summary generates deadline_approaching alert', () => {
    expect(code).toContain('MVAlertType.DEADLINE_APPROACHING');
  });
});

// ============================================================
// E. Backend routes: V69 endpoints
// ============================================================
describe('E · Backend compliance routes V69', () => {
  const code = readBackend('routes', 'compliance.py');

  it('has GET /sites/{site_id}/packages', () => {
    expect(code).toContain('@router.get("/sites/{site_id}/packages")');
  });

  it('has POST /sites/{site_id}/packages', () => {
    expect(code).toContain('@router.post("/sites/{site_id}/packages")');
  });

  it('has POST /sites/{site_id}/cee/dossier', () => {
    expect(code).toContain('@router.post("/sites/{site_id}/cee/dossier")');
  });

  it('has PATCH /cee/dossier/{dossier_id}/step', () => {
    expect(code).toContain('@router.patch("/cee/dossier/{dossier_id}/step")');
  });

  it('has GET /sites/{site_id}/mv/summary', () => {
    expect(code).toContain('@router.get("/sites/{site_id}/mv/summary")');
  });

  it('imports V69 engine functions', () => {
    expect(code).toContain('create_cee_dossier');
    expect(code).toContain('advance_cee_step');
    expect(code).toContain('compute_mv_summary');
    expect(code).toContain('get_site_work_packages');
  });

  it('defines WorkPackageCreate schema', () => {
    expect(code).toContain('class WorkPackageCreate(BaseModel)');
  });

  it('defines CeeStepAdvance schema', () => {
    expect(code).toContain('class CeeStepAdvance(BaseModel)');
  });
});

// ============================================================
// F. V69 file existence checks
// ============================================================
describe('F · V69 files exist', () => {
  it('cee_models.py exists', () => {
    expect(existsSync(resolve(backendRoot, 'models/cee_models.py'))).toBe(true);
  });

  it('test_cee_v69.py exists', () => {
    expect(existsSync(resolve(backendRoot, 'tests/test_cee_v69.py'))).toBe(true);
  });
});

// ============================================================
// G. V68 backward compatibility
// ============================================================
describe('G · V68 backward compatibility preserved', () => {
  const code = readSrc('pages', 'SiteCompliancePage.jsx');

  it('still imports toCompliancePipeline', () => {
    expect(code).toContain('toCompliancePipeline');
  });

  it('still imports getSiteComplianceSummary', () => {
    expect(code).toContain('getSiteComplianceSummary');
  });

  it('still renders ObligationsTab', () => {
    expect(code).toContain('ObligationsTab');
  });

  it('still renders PreuvesTab', () => {
    expect(code).toContain('PreuvesTab');
  });

  it('still has openActionDrawer for action creation', () => {
    expect(code).toContain('openActionDrawer');
  });
});
