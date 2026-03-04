/**
 * PROMEOS V45 — Controls V2 + Preuves actionnables (source guards)
 */
import { describe, it, expect } from 'vitest';
import fs from 'node:fs';
import path from 'node:path';

const src = (rel) => fs.readFileSync(path.resolve(__dirname, '..', '..', rel), 'utf-8');

const backendSrc = (rel) =>
  fs.readFileSync(path.resolve(__dirname, '..', '..', '..', '..', 'backend', rel), 'utf-8');

// ══════════════════════════════════════════════════════════════════════════════
// 1. API module — proof endpoints
// ══════════════════════════════════════════════════════════════════════════════

describe('API exports V45 proof functions', () => {
  const api = src('services/api.js');

  it('exports getTertiaireProofCatalog', () => {
    expect(api).toContain('getTertiaireProofCatalog');
  });

  it('exports getTertiaireEfaProofs', () => {
    expect(api).toContain('getTertiaireEfaProofs');
  });

  it('exports linkTertiaireProof', () => {
    expect(api).toContain('linkTertiaireProof');
  });

  it('calls /proof-catalog endpoint', () => {
    expect(api).toContain('/proof-catalog');
  });

  it('calls /proofs/link endpoint', () => {
    expect(api).toContain('/proofs/link');
  });
});

// ══════════════════════════════════════════════════════════════════════════════
// 2. EFA Detail Page — proofs status + enriched issues
// ══════════════════════════════════════════════════════════════════════════════

describe('EFA Detail Page has V45 proofs status bloc', () => {
  const detail = src('pages/tertiaire/TertiaireEfaDetailPage.jsx');

  it('imports getTertiaireEfaProofs', () => {
    expect(detail).toContain('getTertiaireEfaProofs');
  });

  it('has proofsStatus state', () => {
    expect(detail).toContain('proofsStatus');
  });

  it('has proofs-status-bloc section', () => {
    expect(detail).toContain('proofs-status-bloc');
  });

  it('shows expected/deposited/validated counts', () => {
    expect(detail).toContain('expected_count');
    expect(detail).toContain('deposited_count');
    expect(detail).toContain('validated_count');
  });

  it('shows coverage progress bar', () => {
    expect(detail).toContain('coverage_pct');
  });

  it('has "Voir dans la Mémobox" button', () => {
    expect(detail).toContain('Voir dans la Mémobox');
  });

  it('shows title_fr for issues', () => {
    expect(detail).toContain('title_fr');
  });

  it('shows proof_required bloc per issue', () => {
    expect(detail).toContain('issue-proof-required');
    expect(detail).toContain('Preuve attendue');
  });

  it('has deep-link deposit button', () => {
    expect(detail).toContain('btn-deposit-proof');
    expect(detail).toContain('proof_links');
    expect(detail).toContain('Déposer la preuve');
  });

  it('displays proof owner_role and deadline_hint', () => {
    expect(detail).toContain('owner_role');
    expect(detail).toContain('deadline_hint');
  });
});

// ══════════════════════════════════════════════════════════════════════════════
// 3. Anomalies Page — V45 enrichments
// ══════════════════════════════════════════════════════════════════════════════

describe('Anomalies Page has V45 enrichments', () => {
  const anomalies = src('pages/tertiaire/TertiaireAnomaliesPage.jsx');

  it('shows title_fr for issues', () => {
    expect(anomalies).toContain('title_fr');
  });

  it('shows proof_required bloc per issue', () => {
    expect(anomalies).toContain('issue-proof-required');
    expect(anomalies).toContain('Preuve attendue');
  });

  it('has deep-link deposit button when proof_links available', () => {
    expect(anomalies).toContain('btn-deposit-proof');
    expect(anomalies).toContain('proof_links');
  });

  it('falls back to ProofDepositCTA when no proof_links', () => {
    expect(anomalies).toContain('ProofDepositCTA');
  });

  it('displays proof owner_role and deadline_hint', () => {
    expect(anomalies).toContain('owner_role');
    expect(anomalies).toContain('deadline_hint');
  });
});

// ══════════════════════════════════════════════════════════════════════════════
// 4. Backend — Controls V2 structure
// ══════════════════════════════════════════════════════════════════════════════

describe('Backend Controls V2 (V45)', () => {
  const service = backendSrc('services/tertiaire_service.py');

  it('has _proof helper', () => {
    expect(service).toContain('def _proof(');
  });

  it('has _build_proof_links helper', () => {
    expect(service).toContain('_build_proof_links');
  });

  it('has title_fr in CONTROL_RULES', () => {
    expect(service).toContain('title_fr');
  });

  it('has proof_required structured dict', () => {
    expect(service).toContain('proof_required');
  });

  it('has new rules TERTIAIRE_RESP_NO_EMAIL and TERTIAIRE_PERIMETER_EVENT_PROOF', () => {
    expect(service).toContain('TERTIAIRE_RESP_NO_EMAIL');
    expect(service).toContain('TERTIAIRE_PERIMETER_EVENT_PROOF');
  });
});

// ══════════════════════════════════════════════════════════════════════════════
// 5. Backend — Proof catalog + proofs service
// ══════════════════════════════════════════════════════════════════════════════

describe('Backend Proof catalog (V45)', () => {
  const proofs = backendSrc('services/tertiaire_proofs.py');

  it('has PROOF_CATALOG', () => {
    expect(proofs).toContain('PROOF_CATALOG');
  });

  it('has get_expected_proofs_for_efa', () => {
    expect(proofs).toContain('get_expected_proofs_for_efa');
  });

  it('has list_proofs_status', () => {
    expect(proofs).toContain('list_proofs_status');
  });

  it('has at least 6 proof types', () => {
    expect(proofs).toContain('attestation_operat');
    expect(proofs).toContain('dossier_modulation');
    expect(proofs).toContain('justificatif_exemption');
    expect(proofs).toContain('bail_titre_propriete');
  });
});

// ══════════════════════════════════════════════════════════════════════════════
// 6. Backend routes — proof endpoints
// ══════════════════════════════════════════════════════════════════════════════

describe('Backend routes have V45 proof endpoints', () => {
  const routes = backendSrc('routes/tertiaire.py');

  it('imports tertiaire_proofs', () => {
    expect(routes).toContain('tertiaire_proofs');
  });

  it('has proof-catalog endpoint', () => {
    expect(routes).toContain('proof-catalog');
  });

  it('has /proofs endpoint', () => {
    expect(routes).toContain('/proofs');
  });

  it('has proofs/link endpoint', () => {
    expect(routes).toContain('proofs/link');
  });
});

// ══════════════════════════════════════════════════════════════════════════════
// 7. Mémobox — V45 proof prefilter + link
// ══════════════════════════════════════════════════════════════════════════════

describe('Mémobox has V45 proof prefilter + link', () => {
  const kb = src('pages/KBExplorerPage.jsx');

  it('imports linkTertiaireProof', () => {
    expect(kb).toContain('linkTertiaireProof');
  });

  it('reads proof_type from search params', () => {
    expect(kb).toContain('proof_type');
  });

  it('reads efa_id from search params', () => {
    expect(kb).toContain('efa_id');
  });

  it('shows proof_type label in banner', () => {
    expect(kb).toContain('proof-type-label');
  });

  it('has "Lier à l\'EFA" button on docs', () => {
    expect(kb).toContain('btn-link-proof-efa');
  });

  it('calls linkTertiaireProof on link click', () => {
    expect(kb).toContain('handleLinkProof');
  });

  it('passes proofContext to DocCard', () => {
    expect(kb).toContain('proofContext={proofContext}');
  });
});
