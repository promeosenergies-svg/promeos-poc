/**
 * PROMEOS V47 — Source guards: Action ↔ Preuve loop
 * Vérifie la présence des imports, fonctions et blocs UI
 * dans les fichiers modifiés par V47.
 */
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { resolve } from 'path';

function src(rel) {
  return readFileSync(resolve(__dirname, '..', '..', rel), 'utf-8');
}

// ── actionProofLinkModel ─────────────────────────────────────────────────────

describe('actionProofLinkModel exports', () => {
  const code = src('models/actionProofLinkModel.js');

  it('exporte parseOperatSourceId', () => {
    expect(code).toContain('export function parseOperatSourceId');
  });

  it('exporte isOperatAction', () => {
    expect(code).toContain('export function isOperatAction');
  });

  it('exporte buildActionProofLink', () => {
    expect(code).toContain('export function buildActionProofLink');
  });

  it('exporte buildActionProofContext', () => {
    expect(code).toContain('export function buildActionProofContext');
  });

  it('exporte isActionClosable', () => {
    expect(code).toContain('export function isActionClosable');
  });

  it('exporte resolveProofStatus', () => {
    expect(code).toContain('export function resolveProofStatus');
  });

  it('exporte PROOF_STATUS_LABELS avec 4 clés FR', () => {
    expect(code).toContain('PROOF_STATUS_LABELS');
    expect(code).toContain('Aucune preuve');
    expect(code).toContain('Preuve validée');
  });

  it('exporte PROOF_STATUS_BADGE', () => {
    expect(code).toContain('PROOF_STATUS_BADGE');
  });

  it('parse le format operat:{efa}:{year}:{code}', () => {
    expect(code).toContain("parts[0] !== 'operat'");
  });

  it('détecte insight + operat: dans isOperatAction', () => {
    expect(code).toContain("source_type === 'insight'");
    expect(code).toContain("startsWith('operat:')");
  });
});

// ── ActionDetailDrawer — Bloc Preuves OPERAT ─────────────────────────────────

describe('ActionDetailDrawer — Preuves OPERAT (V47)', () => {
  const code = src('components/ActionDetailDrawer.jsx');

  it('importe isOperatAction depuis actionProofLinkModel', () => {
    expect(code).toContain('isOperatAction');
    expect(code).toContain('actionProofLinkModel');
  });

  it('importe parseOperatSourceId', () => {
    expect(code).toContain('parseOperatSourceId');
  });

  it('importe buildActionProofLink', () => {
    expect(code).toContain('buildActionProofLink');
  });

  it('importe isActionClosable', () => {
    expect(code).toContain('isActionClosable');
  });

  it('importe resolveProofStatus', () => {
    expect(code).toContain('resolveProofStatus');
  });

  it('importe PROOF_STATUS_LABELS et PROOF_STATUS_BADGE', () => {
    expect(code).toContain('PROOF_STATUS_LABELS');
    expect(code).toContain('PROOF_STATUS_BADGE');
  });

  it('importe getTertiaireEfaProofs', () => {
    expect(code).toContain('getTertiaireEfaProofs');
  });

  it('déclare proofsSummary state', () => {
    expect(code).toContain('proofsSummary');
    expect(code).toContain('setProofsSummary');
  });

  it('fetch preuves EFA pour action OPERAT', () => {
    expect(code).toContain('getTertiaireEfaProofs(parsed.efa_id)');
  });

  it('contient le data-testid operat-proof-bloc', () => {
    expect(code).toContain('operat-proof-bloc');
  });

  it('contient le CTA Déposer une preuve', () => {
    expect(code).toContain('Déposer une preuve');
    expect(code).toContain('operat-proof-deposit-cta');
  });

  it('contient le lien Fiche EFA', () => {
    expect(code).toContain('Fiche EFA');
  });

  it("contient la bannière d'aide FR sur clôturabilité", () => {
    expect(code).toContain('considérée clôturable');
    expect(code).toContain('justification');
  });

  it('contient le warning de clôture bloquée', () => {
    expect(code).toContain('operat-closability-warning');
    expect(code).toContain('Clôture bloquée');
  });

  it('bloque le bouton Terminée si OPERAT non clôturable', () => {
    expect(code).toContain('operatBlocked');
    expect(code).toContain('Preuve requise pour clôturer');
  });

  it('importe useNavigate', () => {
    expect(code).toContain('useNavigate');
  });

  it('utilise les icônes Shield, FileCheck, ExternalLink', () => {
    expect(code).toContain('Shield');
    expect(code).toContain('FileCheck');
    expect(code).toContain('ExternalLink');
  });

  it('affiche les compteurs Attendues/Déposées/Validées', () => {
    expect(code).toContain('Attendues');
    expect(code).toContain('Déposées');
    expect(code).toContain('Validées');
  });
});

// ── KBExplorerPage — Retour Action (V47) ─────────────────────────────────────

describe('KBExplorerPage — Retour Action (V47)', () => {
  const code = src('pages/KBExplorerPage.jsx');

  it('importe useNavigate', () => {
    expect(code).toContain('useNavigate');
  });

  it('importe ArrowLeft', () => {
    expect(code).toContain('ArrowLeft');
  });

  it('parse action_id depuis les searchParams', () => {
    expect(code).toContain("searchParams.get('action_id')");
  });

  it('stocke action_id dans proofContext', () => {
    expect(code).toContain('action_id:');
  });

  it("affiche le bouton Retour à l'action", () => {
    expect(code).toContain("Retour à l'action");
    expect(code).toContain('btn-return-action');
  });

  it('navigue vers /actions?detail= au clic retour', () => {
    expect(code).toContain('/actions?detail=${proofContext.action_id}');
  });

  it('conditionne le bouton à proofContext.action_id', () => {
    expect(code).toContain('proofContext.action_id &&');
  });
});

// ── API — imports requis ─────────────────────────────────────────────────────

describe('API — services requis V47', () => {
  const code = src('services/api.js');

  it('exporte getTertiaireEfaProofs', () => {
    expect(code).toContain('getTertiaireEfaProofs');
  });

  it('exporte getActionDetail', () => {
    expect(code).toContain('getActionDetail');
  });

  it('exporte patchAction', () => {
    expect(code).toContain('patchAction');
  });
});
