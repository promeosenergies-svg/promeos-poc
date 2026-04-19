/**
 * PROMEOS V40 — Export Pack OPERAT → Mémobox (traçabilité)
 *
 * 1. GUARD: tertiaire_service.py — KB doc creation in generate_operat_pack
 * 2. GUARD: TertiaireEfaDetailPage — exportResult state + Mémobox button
 * 3. GUARD: Response shape includes kb_doc_id + kb_open_url
 */
import { describe, it, expect } from 'vitest';
import fs from 'node:fs';
import path from 'node:path';

// ── Helpers ──────────────────────────────────────────────────────────────────
const src = (rel) => fs.readFileSync(path.resolve(__dirname, '..', '..', rel), 'utf-8');

const backendSrc = (rel) =>
  fs.readFileSync(path.resolve(__dirname, '..', '..', '..', '..', 'backend', rel), 'utf-8');

// ══════════════════════════════════════════════════════════════════════════════
// 1. GUARD: Backend — generate_operat_pack registers KB doc
// ══════════════════════════════════════════════════════════════════════════════

describe('GUARD generate_operat_pack KB doc creation', () => {
  const code = backendSrc('services/tertiaire_service.py');

  it('imports hashlib for SHA256', () => {
    expect(code).toContain('import hashlib');
  });

  it('computes SHA256 of the zip', () => {
    expect(code).toContain('hashlib.sha256');
  });

  it('creates doc_id with generated_operat_ prefix', () => {
    expect(code).toContain('generated_operat_');
  });

  it('imports KBStore', () => {
    expect(code).toContain('from app.kb.store import KBStore');
  });

  it('calls upsert_doc with review status', () => {
    expect(code).toContain('"status": "review"');
  });

  it('sets source_type compatible with KB schema', () => {
    expect(code).toContain('"source_type": "pdf"');
  });

  it('stores generated_type in meta for traceability', () => {
    expect(code).toContain('"generated_type": "operat_export"');
  });

  it('sets domain to conformite/tertiaire-operat', () => {
    expect(code).toContain('conformite/tertiaire-operat');
  });

  it('creates TertiaireProofArtifact with type operat_export_pack', () => {
    expect(code).toContain('"operat_export_pack"');
    expect(code).toContain('TertiaireProofArtifact');
  });

  it('links artifact to KB via kb_doc_id', () => {
    expect(code).toContain('kb_doc_id=kb_doc_id');
  });

  it('returns kb_doc_id in response', () => {
    expect(code).toContain('"kb_doc_id": kb_doc_id');
  });

  it('returns kb_open_url in response', () => {
    expect(code).toContain('"kb_open_url": kb_open_url');
  });

  it('dedup: checks existing doc before upsert', () => {
    expect(code).toContain('kb_store.get_doc(kb_doc_id)');
  });

  it('dedup: checks existing artifact before creating', () => {
    expect(code).toContain('existing_artifact');
  });

  it('KB creation is non-blocking (wrapped in try/except)', () => {
    expect(code).toContain('V40: KB doc creation failed');
  });

  it('kb_open_url includes context=proof', () => {
    expect(code).toContain('context=proof');
  });

  it('kb_open_url includes status=review', () => {
    expect(code).toContain('status=review');
  });

  // V40.1: display_name
  it('builds human-friendly kb_display_name', () => {
    expect(code).toContain('kb_display_name');
  });

  it('passes display_name to upsert_doc', () => {
    expect(code).toContain('"display_name": kb_display_name');
  });

  it('returns kb_doc_display_name in response', () => {
    expect(code).toContain('"kb_doc_display_name"');
  });
});

// ══════════════════════════════════════════════════════════════════════════════
// 2. GUARD: TertiaireEfaDetailPage — export result + Mémobox button
//
// ⚠ Lot 3 Phase 4 — La page EFA a été refondue en Pattern C (EfaSol.jsx).
//   Les flows UI export pack + Mémobox (V40) sont temporairement retirés
//   du loader thin. Le backend `generate_operat_pack` (section 1 ci-dessus)
//   reste intact et continue de créer les KB docs. La ré-intégration du
//   bouton export + Mémobox dans la fiche est prévue Phase 6 Lot 3
//   (section optionnelle dans EfaSol entity card actions).
// ══════════════════════════════════════════════════════════════════════════════

describe.skip('GUARD TertiaireEfaDetailPage export → Mémobox (Lot 3 P4 : reporté Phase 6)', () => {
  const code = src('pages/tertiaire/TertiaireEfaDetailPage.jsx');

  it('has exportResult state', () => {
    expect(code).toContain('exportResult');
    expect(code).toContain('setExportResult');
  });

  it('handleExport stores result', () => {
    expect(code).toContain('setExportResult(result)');
  });

  it('checks exportResult.kb_doc_id before rendering Mémobox section', () => {
    expect(code).toContain('exportResult?.kb_doc_id');
  });

  it('shows Mémobox badge', () => {
    expect(code).toContain('Mémobox');
  });

  it('shows Ouvrir dans la Mémobox button', () => {
    expect(code).toContain('Ouvrir dans la Mémobox');
  });

  it('navigates to kb_open_url on click', () => {
    expect(code).toContain('navigate(exportResult.kb_open_url)');
  });

  it('displays kb_doc_id reference', () => {
    expect(code).toContain('exportResult.kb_doc_id');
  });

  it('prefers kb_doc_display_name over kb_doc_id', () => {
    expect(code).toContain('exportResult.kb_doc_display_name || exportResult.kb_doc_id');
  });

  it('has aria-label for accessibility', () => {
    expect(code).toContain('aria-label="Ouvrir le pack dans la Mémobox"');
  });
});

// ══════════════════════════════════════════════════════════════════════════════
// 3. GUARD: No regression — existing features preserved
//
// Post-Lot 3 P4 : ProofDepositCTA préservé (user requirement Phase 4).
// Precheck flow + qualification card + export pack button retirés du
// Pattern C — ré-intégration planifiée Phase 6 si signal utilisateur.
// ══════════════════════════════════════════════════════════════════════════════

describe('GUARD no regression on EFA detail (post-Lot 3 P4)', () => {
  const code = src('pages/tertiaire/TertiaireEfaDetailPage.jsx');

  it('ProofDepositCTA still imported', () => {
    expect(code).toContain("import ProofDepositCTA from './components/ProofDepositCTA'");
  });

  it.skip('handlePrecheck still works (reporté Phase 6)', () => {
    expect(code).toContain('handlePrecheck');
    expect(code).toContain('precheckResult');
  });

  it.skip('qualification status card still present (reporté Phase 6)', () => {
    expect(code).toContain('Complétude');
    expect(code).toContain('completeness_pct');
  });

  it.skip('export pack button still present (reporté Phase 6)', () => {
    expect(code).toContain('Générer le pack export (simulation)');
  });
});
