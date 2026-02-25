/**
 * PROMEOS — V68 Billing Unified — Source-guard tests
 * Vérifie la présence des constructs V68 dans les fichiers sources.
 * Tests 100% readFileSync / regex — aucun mock DOM requis.
 */
import { readFileSync } from 'fs';
import { resolve } from 'path';
import { describe, it, expect } from 'vitest';

const root = resolve(__dirname, '../../../');  // → frontend/

const readSrc = (...parts) => readFileSync(resolve(root, 'src', ...parts), 'utf-8');
const readBackend = (...parts) => readFileSync(resolve(root, '..', 'backend', ...parts), 'utf-8');

// ============================================================
// A. api.js — getNormalizedInvoices
// ============================================================
describe('api.js — getNormalizedInvoices (V68)', () => {
  const code = readSrc('services', 'api.js');

  it('exports getNormalizedInvoices', () => {
    expect(code).toMatch(/export const getNormalizedInvoices/);
  });

  it('calls /billing/invoices/normalized', () => {
    expect(code).toMatch(/billing\/invoices\/normalized/);
  });

  it('accepts params object', () => {
    expect(code).toMatch(/getNormalizedInvoices\s*=\s*\(params\s*=/);
  });
});

// ============================================================
// B. BillingPage.jsx — ?month= param + activeMonth + null-safe
// ============================================================
describe('BillingPage.jsx — V68 enhancements', () => {
  const code = readSrc('pages', 'BillingPage.jsx');

  it('reads ?month from searchParams', () => {
    expect(code).toMatch(/searchParams\.get\(['"]month['"]\)/);
  });

  it('defines activeMonth state', () => {
    expect(code).toMatch(/activeMonth/);
  });

  it('passes activeMonth to BillingTimeline', () => {
    expect(code).toMatch(/activeMonth=\{activeMonth\}/);
  });

  it('optional chaining on summary.range', () => {
    expect(code).toMatch(/summary\?\.range\?/);
  });

  it('uses useSearchParams', () => {
    expect(code).toMatch(/useSearchParams/);
  });

  it('imports BillingTimeline', () => {
    expect(code).toMatch(/import BillingTimeline/);
  });
});

// ============================================================
// C. BillIntelPage.jsx — deep-links V68
// ============================================================
describe('BillIntelPage.jsx — deep-links V68', () => {
  const code = readSrc('pages', 'BillIntelPage.jsx');

  it('imports useSearchParams', () => {
    expect(code).toMatch(/useSearchParams/);
  });

  it('imports useNavigate', () => {
    expect(code).toMatch(/useNavigate/);
  });

  it('reads ?site_id from searchParams', () => {
    expect(code).toMatch(/searchParams\.get\(['"]site_id['"]\)/);
  });

  it('reads ?month from searchParams', () => {
    expect(code).toMatch(/searchParams\.get\(['"]month['"]\)/);
  });

  it('defines siteFilter state', () => {
    expect(code).toMatch(/siteFilter/);
  });

  it('defines monthFilter state', () => {
    expect(code).toMatch(/monthFilter/);
  });

  it('has "Voir timeline" CTA navigating to /billing', () => {
    expect(code).toMatch(/\/billing\?site_id=/);
  });

  it('filters invoices by monthFilter', () => {
    expect(code).toMatch(/filteredInvoices/);
  });

  it('passes site_id to getBillingInsights', () => {
    expect(code).toMatch(/site_id.*siteFilter|siteFilter.*site_id/);
  });

  it('imports CalendarRange for Voir timeline button', () => {
    expect(code).toMatch(/CalendarRange/);
  });
});

// ============================================================
// D. BillingTimeline.jsx — activeMonth prop
// ============================================================
describe('BillingTimeline.jsx — activeMonth V68', () => {
  const code = readSrc('components', 'BillingTimeline.jsx');

  it('accepts activeMonth prop in MonthRow', () => {
    expect(code).toMatch(/activeMonth/);
  });

  it('applies ring/highlight class when active', () => {
    expect(code).toMatch(/ring-2|ring-amber/);
  });

  it('exports BillingTimeline with activeMonth in signature', () => {
    expect(code).toMatch(/BillingTimeline\s*\(\s*\{[^}]*activeMonth/);
  });
});

// ============================================================
// E. Backend — billing_normalization.py
// ============================================================
describe('billing_normalization.py — V68 schema', () => {
  const code = readBackend('services', 'billing_normalization.py');

  it('defines InvoiceNormalized Pydantic model', () => {
    expect(code).toMatch(/class InvoiceNormalized\(BaseModel\)/);
  });

  it('has org_id field', () => {
    expect(code).toMatch(/org_id:\s*int/);
  });

  it('has ht_fourniture field', () => {
    expect(code).toMatch(/ht_fourniture/);
  });

  it('has ht_reseau field', () => {
    expect(code).toMatch(/ht_reseau/);
  });

  it('exports normalize_invoice function', () => {
    expect(code).toMatch(/def normalize_invoice/);
  });

  it('computes month_key from period_start', () => {
    expect(code).toMatch(/strftime.*%Y-%m/);
  });
});

// ============================================================
// F. Backend — billing_shadow_v2.py
// ============================================================
describe('billing_shadow_v2.py — V68 shadow engine', () => {
  const code = readBackend('services', 'billing_shadow_v2.py');

  it('defines TURPE constant', () => {
    expect(code).toMatch(/TURPE_EUR_KWH_ELEC/);
  });

  it('defines CSPE constant', () => {
    expect(code).toMatch(/CSPE_EUR_KWH_ELEC/);
  });

  it('defines TICGN constant', () => {
    expect(code).toMatch(/TICGN_EUR_KWH_GAZ/);
  });

  it('exports shadow_billing_v2 function', () => {
    expect(code).toMatch(/def shadow_billing_v2/);
  });

  it('returns expected_reseau_ht key', () => {
    expect(code).toMatch(/expected_reseau_ht/);
  });

  it('returns delta_reseau key', () => {
    expect(code).toMatch(/delta_reseau/);
  });

  it('method is shadow_v2_simplified', () => {
    expect(code).toMatch(/shadow_v2_simplified/);
  });
});

// ============================================================
// G. Backend — billing_service.py — R13/R14
// ============================================================
describe('billing_service.py — R13/R14 rules V68', () => {
  const code = readBackend('services', 'billing_service.py');

  it('defines _rule_reseau_mismatch (R13)', () => {
    expect(code).toMatch(/def _rule_reseau_mismatch/);
  });

  it('defines _rule_taxes_mismatch (R14)', () => {
    expect(code).toMatch(/def _rule_taxes_mismatch/);
  });

  it('R13 in BILLING_RULES', () => {
    expect(code).toMatch(/["']R13["']/);
  });

  it('R14 in BILLING_RULES', () => {
    expect(code).toMatch(/["']R14["']/);
  });

  it('BILLING_RULES has 14 entries', () => {
    const matches = code.match(/\("R\d+"/g);
    expect(matches).not.toBeNull();
    expect(matches.length).toBe(14);
  });
});

// ============================================================
// H. Backend — billing_seed.py — 36 mois
// ============================================================
describe('billing_seed.py — 36 mois V68', () => {
  const code = readBackend('services', 'billing_seed.py');

  it('has MONTHS_COUNT = 36', () => {
    expect(code).toMatch(/MONTHS_COUNT\s*=\s*36/);
  });

  it('has SOURCE_TAG seed_36m', () => {
    expect(code).toMatch(/seed_36m/);
  });

  it('has idempotency check', () => {
    expect(code).toMatch(/skipped/);
  });

  it('has controlled gap 2023-03', () => {
    expect(code).toMatch(/2023.*3|GAPS_SITE_A/);
  });

  it('defines ANOMALY_SHADOW_GAP', () => {
    expect(code).toMatch(/ANOMALY_SHADOW_GAP/);
  });

  it('defines ANOMALY_RESEAU_MISMATCH', () => {
    expect(code).toMatch(/ANOMALY_RESEAU_MISMATCH/);
  });
});

// ============================================================
// I. Deep-links bidirectionnels — intégration
// ============================================================
describe('Deep-links bidirectionnels V68', () => {
  it('BillingTimeline.jsx generates /bill-intel?site_id links', () => {
    const code = readSrc('components', 'BillingTimeline.jsx');
    expect(code).toMatch(/\/bill-intel/);
  });

  it('BillIntelPage.jsx generates /billing?site_id link (retour timeline)', () => {
    const code = readSrc('pages', 'BillIntelPage.jsx');
    expect(code).toMatch(/\/billing\?site_id/);
  });

  it('BillingPage.jsx generates /bill-intel link (navigation directe)', () => {
    const code = readSrc('pages', 'BillingPage.jsx');
    expect(code).toMatch(/bill-intel/);
  });
});

// ============================================================
// J. BillingPage.jsx — P0 fix : getMissingPeriods non-bloquant
// ============================================================
describe('BillingPage.jsx — P0 fix getMissingPeriods non-bloquant', () => {
  const code = readSrc('pages', 'BillingPage.jsx');

  it('imports useExpertMode from ExpertModeContext', () => {
    expect(code).toMatch(/useExpertMode.*ExpertModeContext/);
  });

  it('uses isExpert hook', () => {
    expect(code).toMatch(/const\s+\{[^}]*isExpert[^}]*\}\s*=\s*useExpertMode/);
  });

  it('getMissingPeriods is NOT in the main Promise.all', () => {
    // Promise.all should only contain getCoverageSummary and getBillingPeriods
    const promiseAllBlock = code.match(/Promise\.all\(\[[\s\S]*?\]\)/)?.[0] || '';
    expect(promiseAllBlock).not.toMatch(/getMissingPeriods/);
  });

  it('getMissingPeriods has its own try/catch block', () => {
    // After the main try/catch, getMissingPeriods should appear in another try block
    expect(code).toMatch(/getMissingPeriods[\s\S]{0,200}catch/);
  });

  it('handles 404 with siteFilter reset', () => {
    expect(code).toMatch(/status.*404|404.*status/);
    expect(code).toMatch(/setSiteFilter\(['"]{0,2}\)/);
  });

  it('logs errors with isExpert guard', () => {
    expect(code).toMatch(/isExpert.*console\.error|console\.error.*isExpert/);
  });
});

// ============================================================
// K. BillIntelPage.jsx — P1 : filter bar sur la liste factures
// ============================================================
describe('BillIntelPage.jsx — P1 invoice filter bar', () => {
  const code = readSrc('pages', 'BillIntelPage.jsx');

  it('imports useMemo', () => {
    expect(code).toMatch(/useMemo/);
  });

  it('defines invoiceSearch state', () => {
    expect(code).toMatch(/invoiceSearch/);
  });

  it('defines invoiceStatusFilter state', () => {
    expect(code).toMatch(/invoiceStatusFilter/);
  });

  it('filteredInvoices uses useMemo', () => {
    expect(code).toMatch(/filteredInvoices\s*=\s*useMemo/);
  });

  it('filteredInvoices filters by invoiceStatusFilter', () => {
    expect(code).toMatch(/invoiceStatusFilter/);
  });

  it('filteredInvoices filters by invoiceSearch (invoice_number or pdl_prm)', () => {
    expect(code).toMatch(/invoice_number[\s\S]{0,100}pdl_prm|pdl_prm[\s\S]{0,100}invoice_number/);
  });

  it('has a text input for invoice search', () => {
    expect(code).toMatch(/invoiceSearch[\s\S]{0,200}placeholder|placeholder[\s\S]{0,200}invoiceSearch/);
  });

  it('has status filter chips rendered via map (array.map + invoiceStatusFilter)', () => {
    // array of statuses rendered via .map(), invoiceStatusFilter used inside for active state
    expect(code).toMatch(/\[''.*\]\.map|\['',/);
    expect(code).toMatch(/invoiceStatusFilter/);
  });
});

// ============================================================
// L. BillIntelPage.jsx — ÉTAPE 3 : Import PDF site select
// ============================================================
describe('BillIntelPage.jsx — PDF import site select (ÉTAPE 3)', () => {
  const code = readSrc('pages', 'BillIntelPage.jsx');

  it('imports getSites from api', () => {
    expect(code).toMatch(/getSites/);
  });

  it('has sites state', () => {
    expect(code).toMatch(/sites.*useState|useState.*sites/);
  });

  it('renders a <select> for pdfSiteId (no more number input for pdf)', () => {
    expect(code).not.toMatch(/type=["']number["'][\s\S]{0,100}pdfSiteId|pdfSiteId[\s\S]{0,100}type=["']number["']/);
    expect(code).toMatch(/pdfSiteId[\s\S]{0,300}select|select[\s\S]{0,300}pdfSiteId/);
  });

  it('pre-fills pdfSiteId from siteFilter', () => {
    expect(code).toMatch(/siteFilter[\s\S]{0,100}pdfSiteId|pdfSiteId[\s\S]{0,100}siteFilter/);
  });
});

// ============================================================
// M. BillIntelPage.jsx — ÉTAPE 4 : Filtre période presets
// ============================================================
describe('BillIntelPage.jsx — period filter presets (ÉTAPE 4)', () => {
  const code = readSrc('pages', 'BillIntelPage.jsx');

  it('has periodPreset state', () => {
    expect(code).toMatch(/periodPreset/);
  });

  it('filteredInvoices handles last3/last6/last12 cutoff', () => {
    expect(code).toMatch(/last3|last6|last12/);
  });

  it('filteredInvoices uses useMemo with periodPreset dependency', () => {
    expect(code).toMatch(/filteredInvoices\s*=\s*useMemo/);
    expect(code).toMatch(/periodPreset[\s\S]{0,200}monthFilter|monthFilter[\s\S]{0,200}periodPreset/);
  });

  it('has period select UI with Toutes périodes option', () => {
    expect(code).toMatch(/Toutes p.riodes/);
  });

  it('shows month input only when specific preset', () => {
    expect(code).toMatch(/specific[\s\S]{0,200}month|month[\s\S]{0,200}specific/);
  });
});

// ============================================================
// N. BillingPage.jsx — P0 : 404 purge localStorage + expert debug payload
// ============================================================
describe('BillingPage.jsx — P0 404 purge + expert debug', () => {
  const code = readSrc('pages', 'BillingPage.jsx');

  it('reads promeos_scope from localStorage on 404', () => {
    expect(code).toMatch(/promeos_scope/);
  });

  it('sets siteId to null in localStorage scope', () => {
    expect(code).toMatch(/scope\.siteId\s*=\s*null/);
  });

  it('writes updated scope back to localStorage', () => {
    expect(code).toMatch(/localStorage\.setItem\(\s*['"]promeos_scope['"]/);
  });

  it('includes debug payload with endpoint, status, and site_id in expert mode', () => {
    expect(code).toMatch(/endpoint=/);
    expect(code).toMatch(/status=404/);
    expect(code).toMatch(/site_id=/);
  });

  it('expert debug payload is gated by isExpert', () => {
    expect(code).toMatch(/isExpert[\s\S]{0,200}endpoint=/);
  });
});

// ============================================================
// O. BillIntelPage.jsx — P0 : imports UX (disabled + tooltip + toast)
// ============================================================
describe('BillIntelPage.jsx — P0 imports UX', () => {
  const code = readSrc('pages', 'BillIntelPage.jsx');

  it('CSV button has disabled prop gated on pdfSiteId', () => {
    expect(code).toMatch(/Importer CSV[\s\S]{0,300}disabled=\{!pdfSiteId\}|disabled=\{!pdfSiteId\}[\s\S]{0,300}Importer CSV/);
  });

  it('CSV file input has disabled prop', () => {
    expect(code).toMatch(/accept=["'].csv["'][\s\S]{0,200}disabled/);
  });

  it('shows tooltip Sélectionnez un site when no site selected', () => {
    expect(code).toMatch(/S.lectionnez un site/);
  });

  it('handleCsvImport calls toast on success', () => {
    expect(code).toMatch(/handleCsvImport[\s\S]{0,500}toast\(/);
  });

  it('handleCsvImport calls toast on error', () => {
    expect(code).toMatch(/handleCsvImport[\s\S]{0,800}catch[\s\S]{0,200}toast\(/);
  });

  it('handlePdfImport calls toast on success', () => {
    expect(code).toMatch(/handlePdfImport[\s\S]{0,500}toast\(/);
  });

  it('handlePdfImport calls toast on error', () => {
    expect(code).toMatch(/handlePdfImport[\s\S]{0,800}catch[\s\S]{0,200}toast\(/);
  });

  it('pre-fills pdfSiteId from first site when no siteFilter', () => {
    expect(code).toMatch(/sites\.length\s*>\s*0[\s\S]{0,100}sites\[0\]/);
  });

  it('PDF button label has tooltip when no site', () => {
    expect(code).toMatch(/Importer PDF[\s\S]{0,500}S.lectionnez un site|S.lectionnez un site[\s\S]{0,500}Importer PDF/);
  });
});
