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

  it('getCoverageSummary and getMissingPeriods are NOT in Promise.all', () => {
    // Promise.all should not exist, or if it does, no coverage/missing inside
    const promiseAllBlock = code.match(/Promise\.all\(\[[\s\S]*?\]\)/)?.[0] || '';
    expect(promiseAllBlock).not.toMatch(/getMissingPeriods/);
    expect(promiseAllBlock).not.toMatch(/getCoverageSummary/);
  });

  it('getCoverageSummary has its own try/catch (non-bloquant)', () => {
    expect(code).toMatch(/getCoverageSummary[\s\S]{0,200}catch/);
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

  it('CSV button uses ref-based file picker (csvInputRef)', () => {
    expect(code).toMatch(/csvInputRef/);
    expect(code).toMatch(/handleCsvClick/);
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
    // Extract handlePdfImport function body specifically
    const fnBody = code.match(/async function handlePdfImport[\s\S]{0,1500}/)?.[0] || '';
    expect(fnBody).toMatch(/toast\(/);
  });

  it('handlePdfImport calls toast on error', () => {
    const fnBody = code.match(/async function handlePdfImport[\s\S]{0,1500}/)?.[0] || '';
    expect(fnBody).toMatch(/catch[\s\S]{0,300}toast\(/);
  });

  it('pre-fills pdfSiteId from first site when no siteFilter', () => {
    expect(code).toMatch(/sites\.length\s*>\s*0[\s\S]{0,100}sites\[0\]/);
  });

  it('PDF button label has tooltip when no site', () => {
    expect(code).toMatch(/Importer PDF[\s\S]{0,500}S.lectionnez un site|S.lectionnez un site[\s\S]{0,500}Importer PDF/);
  });

  it('Expert logs on CSV button click', () => {
    expect(code).toMatch(/isExpert[\s\S]{0,100}CSV button clicked/);
  });

  it('Expert logs on CSV file selected', () => {
    expect(code).toMatch(/isExpert[\s\S]{0,100}CSV file selected/);
  });

  it('Expert logs on PDF button click', () => {
    expect(code).toMatch(/isExpert[\s\S]{0,100}PDF button clicked/);
  });

  it('Expert logs on PDF file selected', () => {
    expect(code).toMatch(/isExpert[\s\S]{0,100}PDF file selected/);
  });
});

// ============================================================
// P. api.js — content-type guard (non-JSON response detection)
// ============================================================
describe('api.js — content-type guard', () => {
  const code = readSrc('services', 'api.js');

  it('checks response content-type in interceptor', () => {
    expect(code).toMatch(/content-type/);
  });

  it('rejects non-JSON responses with explicit proxy/prefix error', () => {
    expect(code).toMatch(/application\/json/);
    expect(code).toMatch(/proxy|pr.fixe|prefix/i);
  });

  it('allows text/plain responses (health-check etc.)', () => {
    expect(code).toMatch(/text\/plain/);
  });

  it('skips guard for blob responseType', () => {
    expect(code).toMatch(/responseType.*blob|blob.*responseType/);
  });
});

// ============================================================
// Q. api.js — billing API routes use /billing/ prefix
// ============================================================
describe('api.js — billing routes use /billing/ prefix', () => {
  const code = readSrc('services', 'api.js');

  it('getBillingPeriods uses /billing/periods', () => {
    expect(code).toMatch(/getBillingPeriods[\s\S]{0,200}\/billing\/periods/);
  });

  it('getCoverageSummary uses /billing/coverage-summary', () => {
    expect(code).toMatch(/getCoverageSummary[\s\S]{0,200}\/billing\/coverage-summary/);
  });

  it('getNormalizedInvoices uses /billing/invoices/normalized', () => {
    expect(code).toMatch(/getNormalizedInvoices[\s\S]{0,200}\/billing\/invoices\/normalized/);
  });

  it('importInvoicesCsv uses /billing/import-csv', () => {
    expect(code).toMatch(/importInvoicesCsv[\s\S]{0,200}\/billing\/import-csv/);
  });

  it('importInvoicesPdf uses /billing/import-pdf', () => {
    expect(code).toMatch(/importInvoicesPdf[\s\S]{0,200}\/billing\/import-pdf/);
  });
});

// ============================================================
// R. BillingPage.jsx — Expert debug payload on getBillingPeriods error
// ============================================================
describe('BillingPage.jsx — Expert debug payload', () => {
  const code = readSrc('pages', 'BillingPage.jsx');

  it('builds debugPayload object with endpoint, params, status, contentType, bodySnippet, orgHeader', () => {
    expect(code).toMatch(/debugPayload/);
    expect(code).toMatch(/debugPayload[\s\S]{0,300}endpoint/);
    expect(code).toMatch(/debugPayload[\s\S]{0,300}status/);
    expect(code).toMatch(/debugPayload[\s\S]{0,300}contentType/);
    expect(code).toMatch(/debugPayload[\s\S]{0,300}bodySnippet/);
    expect(code).toMatch(/debugPayload[\s\S]{0,300}orgHeader/);
  });

  it('console.error logs debugPayload when isExpert', () => {
    expect(code).toMatch(/isExpert[\s\S]{0,100}getBillingPeriods FAILED[\s\S]{0,50}debugPayload/);
  });

  it('displays debug info in error banner for non-404 errors in Expert mode', () => {
    expect(code).toMatch(/debugPayload\.endpoint[\s\S]{0,200}debugPayload\.status/);
    expect(code).toMatch(/org=.*debugPayload\.orgHeader/);
    expect(code).toMatch(/ct=.*debugPayload\.contentType/);
    expect(code).toMatch(/body=.*debugPayload\.bodySnippet/);
  });
});

// ============================================================
// S. BillIntelPage.jsx — ref-based file picker pattern
// ============================================================
describe('BillIntelPage.jsx — ref-based file picker', () => {
  const code = readSrc('pages', 'BillIntelPage.jsx');

  it('imports useRef', () => {
    expect(code).toMatch(/useRef/);
  });

  it('declares csvInputRef and pdfInputRef', () => {
    expect(code).toMatch(/csvInputRef\s*=\s*useRef/);
    expect(code).toMatch(/pdfInputRef\s*=\s*useRef/);
  });

  it('handleCsvClick triggers csvInputRef.current.click()', () => {
    expect(code).toMatch(/handleCsvClick[\s\S]{0,200}csvInputRef\.current[\s\S]{0,20}click/);
  });

  it('handlePdfClick triggers pdfInputRef.current.click()', () => {
    expect(code).toMatch(/handlePdfClick[\s\S]{0,200}pdfInputRef\.current[\s\S]{0,20}click/);
  });

  it('CSV button uses type="button" and onClick={handleCsvClick}', () => {
    expect(code).toMatch(/handleCsvClick[\s\S]{0,300}Importer CSV|Importer CSV[\s\S]{0,300}handleCsvClick/);
  });

  it('PDF button uses type="button" and onClick={handlePdfClick}', () => {
    expect(code).toMatch(/handlePdfClick[\s\S]{0,300}Importer PDF|Importer PDF[\s\S]{0,300}handlePdfClick/);
  });

  it('hidden input refs have correct accept attributes', () => {
    expect(code).toMatch(/ref=\{csvInputRef\}[\s\S]{0,100}accept=["'].csv["']/);
    expect(code).toMatch(/ref=\{pdfInputRef\}[\s\S]{0,100}accept=["'].pdf["']/);
  });
});


// ============================================================
// T. BillingPage — Scope Unifié (V70)
// ============================================================
describe('BillingPage — Scope Unifié (V70)', () => {
  const code = readSrc('pages', 'BillingPage.jsx');

  it('imports useScope from ScopeContext', () => {
    expect(code).toMatch(/import\s*\{[^}]*useScope[^}]*\}\s*from\s*['"]\.\.\/contexts\/ScopeContext['"]/);
  });

  it('imports useToast from ToastProvider', () => {
    expect(code).toMatch(/import\s*\{[^}]*useToast[^}]*\}\s*from\s*['"]\.\.\/ui\/ToastProvider['"]/);
  });

  it('destructures selectedSiteId from useScope', () => {
    expect(code).toMatch(/selectedSiteId\s*:\s*scopeSiteId/);
  });

  it('destructures orgSites from useScope', () => {
    expect(code).toMatch(/orgSites\s*\}\s*=\s*useScope/);
  });

  it('derives scopeHasSite', () => {
    expect(code).toMatch(/const\s+scopeHasSite\s*=\s*!!scopeSiteId/);
  });

  it('derives localFilterActive', () => {
    expect(code).toMatch(/const\s+localFilterActive\s*=/);
  });

  it('syncs scopeSiteId via useEffect', () => {
    expect(code).toMatch(/useEffect[\s\S]{0,200}setSiteFilter[\s\S]{0,100}scopeSiteId/);
  });

  it('renders Hérité chip in JSX', () => {
    expect(code).toMatch(/Hérité\s*:/);
  });

  it('renders Vue filtrée indicator in JSX', () => {
    expect(code).toMatch(/Vue filtrée/);
  });

  it('does NOT import getSites (replaced by orgSites)', () => {
    expect(code).not.toMatch(/import\s*\{[^}]*getSites[^}]*\}/);
  });
});


// ============================================================
// U. BillingPage — Filtres Timeline (V70)
// ============================================================
describe('BillingPage — Filtres Timeline (V70)', () => {
  const code = readSrc('pages', 'BillingPage.jsx');

  it('has statusFilter state', () => {
    expect(code).toMatch(/useState\s*\(\s*['"]all['"]\s*\)/);
    expect(code).toMatch(/statusFilter/);
  });

  it('has periodPreset state', () => {
    expect(code).toMatch(/periodPreset/);
    expect(code).toMatch(/setPeriodPreset/);
  });

  it('has timelineSearch state', () => {
    expect(code).toMatch(/timelineSearch/);
    expect(code).toMatch(/setTimelineSearch/);
  });

  it('has sortMode state', () => {
    expect(code).toMatch(/sortMode/);
    expect(code).toMatch(/setSortMode/);
  });

  it('defines filteredPeriods with useMemo', () => {
    expect(code).toMatch(/const\s+filteredPeriods\s*=\s*useMemo/);
  });

  it('defines statusCounts with useMemo', () => {
    expect(code).toMatch(/const\s+statusCounts\s*=\s*useMemo/);
  });

  it('renders status chips with statusCounts', () => {
    expect(code).toMatch(/statusCounts\[/);
  });

  it('passes filteredPeriods to BillingTimeline', () => {
    expect(code).toMatch(/periods=\{filteredPeriods\}/);
  });

  it('supports last3, last6, last12 presets', () => {
    expect(code).toMatch(/last3/);
    expect(code).toMatch(/last6/);
    expect(code).toMatch(/last12/);
  });

  it('supports priority_missing sort mode', () => {
    expect(code).toMatch(/priority_missing/);
  });

  it('imports Search from lucide-react', () => {
    expect(code).toMatch(/import\s*\{[^}]*Search[^}]*\}\s*from\s*['"]lucide-react['"]/);
  });
});


// ============================================================
// V. BillingPage — Import Contextuel (V70)
// ============================================================
describe('BillingPage — Import Contextuel (V70)', () => {
  const code = readSrc('pages', 'BillingPage.jsx');

  it('imports importInvoicesCsv from api', () => {
    expect(code).toMatch(/import\s*\{[^}]*importInvoicesCsv[^}]*\}\s*from\s*['"]\.\.\/services\/api['"]/);
  });

  it('imports importInvoicesPdf from api', () => {
    expect(code).toMatch(/import\s*\{[^}]*importInvoicesPdf[^}]*\}\s*from\s*['"]\.\.\/services\/api['"]/);
  });

  it('creates csvInputRef with useRef', () => {
    expect(code).toMatch(/csvInputRef\s*=\s*useRef/);
  });

  it('creates pdfInputRef with useRef', () => {
    expect(code).toMatch(/pdfInputRef\s*=\s*useRef/);
  });

  it('has importContext state', () => {
    expect(code).toMatch(/importContext/);
    expect(code).toMatch(/setImportContext/);
  });

  it('defines handleContextualCsvImport function', () => {
    expect(code).toMatch(/handleContextualCsvImport/);
  });

  it('defines handleContextualPdfImport function', () => {
    expect(code).toMatch(/handleContextualPdfImport/);
  });

  it('calls toast in CSV import handler', () => {
    const fn = code.match(/async function handleContextualCsvImport[\s\S]{0,800}/)?.[0] || '';
    expect(fn).toMatch(/toast\(/);
  });

  it('calls toast in PDF import handler', () => {
    const fn = code.match(/async function handleContextualPdfImport[\s\S]{0,800}/)?.[0] || '';
    expect(fn).toMatch(/toast\(/);
  });

  it('resets importContext after import', () => {
    expect(code).toMatch(/setImportContext\(\s*null\s*\)/);
  });
});


// ============================================================
// W. BillingTimeline — CTA Voir avec deepLink (V70)
// ============================================================
describe('BillingTimeline — CTA Voir + deepLink (V70)', () => {
  const code = readSrc('components', 'BillingTimeline.jsx');

  it('imports deepLinkWithContext from services/deepLink', () => {
    expect(code).toMatch(/import\s*\{[^}]*deepLinkWithContext[^}]*\}\s*from\s*['"]\.\.\/services\/deepLink['"]/);
  });

  it('uses deepLinkWithContext in handleView', () => {
    expect(code).toMatch(/deepLinkWithContext\s*\(/);
  });

  it('passes invoice_ids to deepLinkWithContext (single invoice → detail)', () => {
    expect(code).toMatch(/invoice_ids/);
    expect(code).toMatch(/ids\.length\s*===\s*1/);
  });

  it('renders Eye icon in Voir button', () => {
    expect(code).toMatch(/Eye/);
    expect(code).toMatch(/Voir/);
  });

  it('accepts onImport prop and calls it for CSV/PDF', () => {
    expect(code).toMatch(/onImport\s*\(/);
    expect(code).toMatch(/handleImportCsv/);
    expect(code).toMatch(/handleImportPdf/);
  });

  it('renders separate CSV and PDF import buttons for non-covered periods', () => {
    expect(code).toMatch(/CSV/);
    expect(code).toMatch(/PDF/);
  });
});


// ============================================================
// X. deepLink helper — deepLinkWithContext (V70)
// ============================================================
describe('deepLink.js — deepLinkWithContext (V70)', () => {
  const code = readSrc('services', 'deepLink.js');

  it('exports deepLinkWithContext function', () => {
    expect(code).toMatch(/export\s+function\s+deepLinkWithContext/);
  });

  it('builds URL with invoice_id param when invoiceId provided', () => {
    expect(code).toMatch(/invoice_id/);
  });

  it('builds URL with site_id and month params', () => {
    expect(code).toMatch(/site_id/);
    expect(code).toMatch(/month/);
  });

  it('returns path to /bill-intel', () => {
    expect(code).toMatch(/\/bill-intel/);
  });
});


// ============================================================
// Y. NavRegistry — Timeline sous Facturation (V70)
// ============================================================
describe('NavRegistry — Timeline sous Facturation (V70)', () => {
  const code = readSrc('layout', 'NavRegistry.js');

  it('Factures & anomalies appears before Timeline & couverture', () => {
    const idxFactures = code.indexOf('Factures & anomalies');
    const idxTimeline = code.indexOf('Timeline & couverture');
    expect(idxFactures).toBeGreaterThan(-1);
    expect(idxTimeline).toBeGreaterThan(-1);
    expect(idxFactures).toBeLessThan(idxTimeline);
  });

  it('Timeline has indent: true', () => {
    expect(code).toMatch(/\/billing[\s\S]{0,200}indent:\s*true/);
  });

  it('bill-intel label is Factures & anomalies', () => {
    expect(code).toMatch(/\/bill-intel[\s\S]{0,150}Factures & anomalies/);
  });
});
