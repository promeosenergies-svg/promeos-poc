/**
 * PROMEOS V39.1 — Proof Bridge : OPERAT → Memobox
 *
 * 1. ProofDepositCTA unit tests (link generation, domain override, props)
 * 2. Source guards: Wizard step 7, EFA detail, Anomalies page
 */
import { describe, it, expect } from 'vitest';
import fs from 'node:fs';
import path from 'node:path';

import { buildProofLink } from '../../models/proofLinkModel.js';

// ── Helper: read source file ────────────────────────────────────────────────
const src = (rel) =>
  fs.readFileSync(path.resolve(__dirname, '..', '..', rel), 'utf-8');

// ══════════════════════════════════════════════════════════════════════════════
// 1. ProofDepositCTA component
// ══════════════════════════════════════════════════════════════════════════════

describe('ProofDepositCTA component source', () => {
  const code = src('pages/tertiaire/components/ProofDepositCTA.jsx');

  it('imports buildProofLink from proofLinkModel', () => {
    expect(code).toContain("from '../../../models/proofLinkModel'");
  });

  it('imports Upload icon from lucide-react', () => {
    expect(code).toContain("Upload");
    expect(code).toContain("lucide-react");
  });

  it('uses useNavigate for routing', () => {
    expect(code).toContain('useNavigate');
  });

  it('has default domain conformite/tertiaire-operat', () => {
    expect(code).toContain('conformite/tertiaire-operat');
  });

  it('calls buildProofLink with type conformite', () => {
    expect(code).toContain("type: 'conformite'");
  });

  it('calls buildProofLink with actionKey lev-tertiaire-efa', () => {
    expect(code).toContain("actionKey: 'lev-tertiaire-efa'");
  });

  it('overrides domain in generated link when custom domain provided', () => {
    expect(code).toContain('domain=');
    expect(code).toContain('encodeURIComponent(domain)');
  });

  it('has aria-label mentioning Mémobox', () => {
    expect(code).toMatch(/aria-label.*Mémobox/);
  });

  it('default label is Déposer une preuve', () => {
    expect(code).toContain("Déposer une preuve");
  });
});

// ══════════════════════════════════════════════════════════════════════════════
// 2. buildProofLink generates correct OPERAT links
// ══════════════════════════════════════════════════════════════════════════════

describe('buildProofLink for OPERAT context', () => {
  it('generates link with conformite domain', () => {
    const link = buildProofLink({
      type: 'conformite',
      actionKey: 'lev-tertiaire-efa',
      proofHint: 'EFA:Test | Surface:2000 m²',
    });
    expect(link).toContain('context=proof');
    expect(link).toContain('domain=reglementaire');
    expect(link).toContain('lever=lev-tertiaire-efa');
    expect(link).toContain('hint=');
  });

  it('encodes proofHint correctly', () => {
    const link = buildProofLink({
      type: 'conformite',
      actionKey: 'lev-tertiaire-efa',
      proofHint: 'EFA:Tour Bureaux | efa_id:42',
    });
    expect(link).toContain('hint=EFA');
  });

  it('truncates long hints to 100 chars', () => {
    const longHint = 'A'.repeat(200);
    const link = buildProofLink({
      type: 'conformite',
      proofHint: longHint,
    });
    // The hint param should not contain 200 chars
    const hintParam = new URLSearchParams(link.split('?')[1]).get('hint');
    expect(hintParam.length).toBeLessThanOrEqual(100);
  });
});

// ══════════════════════════════════════════════════════════════════════════════
// 3. GUARD: Wizard step 7 — proof section
// ══════════════════════════════════════════════════════════════════════════════

describe('GUARD TertiaireWizardPage proof section', () => {
  const code = src('pages/tertiaire/TertiaireWizardPage.jsx');

  it('imports ProofDepositCTA component', () => {
    expect(code).toContain("import ProofDepositCTA from './components/ProofDepositCTA'");
  });

  it('contains proof section label Preuves (optionnel)', () => {
    expect(code).toContain('Preuves (optionnel)');
  });

  it('mentions Mémobox in proof section text', () => {
    expect(code).toContain('Mémobox');
  });

  it('provides contextual hint with EFA name', () => {
    expect(code).toContain('EFA:${form.nom');
  });

  it('includes Étape:Confirmation in hint', () => {
    expect(code).toMatch(/Étape:Confirmation/);
  });

  it('includes role in hint', () => {
    expect(code).toContain('Rôle:');
  });

  it('includes surface in hint', () => {
    expect(code).toContain('Surface:');
  });

  it('proof section does not affect canNext validation', () => {
    // canNext for step 6 should always return true
    expect(code).toContain('case 6: return true;');
  });
});

// ══════════════════════════════════════════════════════════════════════════════
// 4. GUARD: EFA Detail — enriched proof block
// ══════════════════════════════════════════════════════════════════════════════

describe('GUARD TertiaireEfaDetailPage proof block', () => {
  const code = src('pages/tertiaire/TertiaireEfaDetailPage.jsx');

  it('imports ProofDepositCTA (not raw buildProofLink)', () => {
    expect(code).toContain("import ProofDepositCTA from './components/ProofDepositCTA'");
    expect(code).not.toContain("import { buildProofLink }");
  });

  it('ProofDepositCTA is always visible (not gated by proofs.length === 0)', () => {
    // The CTA should be in the header, not inside the empty state
    const headerSection = code.split('Preuves documentaires')[1]?.split('</Card>')[0] || '';
    expect(headerSection).toContain('ProofDepositCTA');
  });

  it('enriched hint includes EFA name', () => {
    expect(code).toContain('EFA:${efa.nom}');
  });

  it('enriched hint includes efa_id', () => {
    expect(code).toContain('efa_id:${efa.id}');
  });

  it('enriched hint includes Responsable when available', () => {
    expect(code).toContain('Responsable:');
  });

  it('enriched hint includes Surface', () => {
    expect(code).toContain('Surface:${Math.round(totalSurface)}');
  });
});

// ══════════════════════════════════════════════════════════════════════════════
// 5. GUARD: Anomalies page — proof button per issue
// ══════════════════════════════════════════════════════════════════════════════

describe('GUARD TertiaireAnomaliesPage proof buttons', () => {
  const code = src('pages/tertiaire/TertiaireAnomaliesPage.jsx');

  it('imports ProofDepositCTA component', () => {
    expect(code).toContain("import ProofDepositCTA from './components/ProofDepositCTA'");
  });

  it('ProofDepositCTA appears inside issue cards', () => {
    // CTA should be near the action buttons area
    const issueSection = code.split('issues.map')[1] || '';
    expect(issueSection).toContain('ProofDepositCTA');
  });

  it('hint includes EFA reference', () => {
    expect(code).toContain('EFA:${issue.efa_nom');
  });

  it('hint includes efa_id', () => {
    expect(code).toContain('efa_id:${issue.efa_id}');
  });

  it('hint includes Issue code', () => {
    expect(code).toContain('Issue:${issue.code}');
  });

  it('hint includes severity label', () => {
    expect(code).toContain('Sévérité:${SEVERITY_LABELS[issue.severity]');
  });

  it('button label is Déposer la preuve', () => {
    expect(code).toContain("Déposer la preuve");
  });
});

// ══════════════════════════════════════════════════════════════════════════════
// 6. GUARD: No new backend API (pure frontend bridge)
// ══════════════════════════════════════════════════════════════════════════════

describe('GUARD no new backend API', () => {
  it('ProofDepositCTA has no fetch/axios/api import', () => {
    const code = src('pages/tertiaire/components/ProofDepositCTA.jsx');
    expect(code).not.toContain('axios');
    expect(code).not.toContain('fetch(');
    expect(code).not.toContain("from '../../services/api'");
    expect(code).not.toContain("from '../../../services/api'");
  });

  it('ProofDepositCTA uses only navigate (client-side routing)', () => {
    const code = src('pages/tertiaire/components/ProofDepositCTA.jsx');
    expect(code).toContain('navigate(finalLink)');
  });
});
