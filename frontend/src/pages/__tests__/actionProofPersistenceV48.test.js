/**
 * PROMEOS V48 — Source guards: Action ↔ Proof persistence
 * Vérifie la présence des imports, fonctions et API
 * pour la persistance des liens action ↔ preuve.
 */
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { resolve } from 'path';

function src(rel) {
  return readFileSync(resolve(__dirname, '..', '..', rel), 'utf-8');
}

function backendSrc(rel) {
  return readFileSync(resolve(__dirname, '..', '..', '..', '..', 'backend', rel), 'utf-8');
}

// ── API: persistent proof endpoints ──────────────────────────────────────────

describe('API — V48 persistent proof endpoints', () => {
  const code = src('services/api.js');

  it('exporte getActionProofs', () => {
    expect(code).toContain('getActionProofs');
  });

  it('exporte linkProofToAction', () => {
    expect(code).toContain('linkProofToAction');
  });

  it('getActionProofs appelle /actions/{id}/proofs', () => {
    expect(code).toContain('/proofs');
    expect(code).toContain('getActionProofs');
  });

  it('uploadKBDoc accepte actionId en paramètre', () => {
    expect(code).toContain('actionId');
    expect(code).toContain('action_id');
  });
});

// ── ActionDetailDrawer — V48 persistent fetch ───────────────────────────────

describe('ActionDetailDrawer — V48 persistent proof fetch', () => {
  const code = src('components/ActionDetailDrawer.jsx');

  it('importe getActionProofs', () => {
    expect(code).toContain('getActionProofs');
  });

  it('appelle getActionProofs dans le useEffect', () => {
    expect(code).toContain('getActionProofs(actionId)');
  });

  it('conserve le fallback getTertiaireEfaProofs', () => {
    expect(code).toContain('getTertiaireEfaProofs');
  });

  it('fusionne persistent et EFA dans proofsSummary', () => {
    expect(code).toContain('persistent');
    expect(code).toContain('pSummary');
  });

  it('conserve le bloc operat-proof-bloc', () => {
    expect(code).toContain('operat-proof-bloc');
  });

  it('conserve le CTA Déposer une preuve', () => {
    expect(code).toContain('Déposer une preuve');
  });

  it('conserve le gating operatBlocked', () => {
    expect(code).toContain('operatBlocked');
  });
});

// ── KBExplorerPage — V48 upload + link ──────────────────────────────────────

describe('KBExplorerPage — V48 action link on upload', () => {
  const code = src('pages/KBExplorerPage.jsx');

  it('importe linkProofToAction', () => {
    expect(code).toContain('linkProofToAction');
  });

  it('passe action_id au uploadKBDoc', () => {
    expect(code).toContain('proofContext?.action_id');
    expect(code).toContain('uploadKBDoc(f, f.name, domain');
  });

  it('contient le bouton btn-link-proof-action', () => {
    expect(code).toContain('btn-link-proof-action');
  });

  it("affiche le texte Lier à l'action", () => {
    expect(code).toContain('Lier à l');
    expect(code).toContain('action');
  });

  it('appelle linkProofToAction dans handleLinkAction', () => {
    expect(code).toContain('handleLinkAction');
    expect(code).toContain('linkProofToAction(proofContext.action_id');
  });

  it("conserve le bouton Lier à l'EFA", () => {
    expect(code).toContain('btn-link-proof-efa');
  });

  it("conserve le bouton Retour à l'action", () => {
    expect(code).toContain('btn-return-action');
  });
});

// ── Backend — V48 source guards ─────────────────────────────────────────────

describe('Backend — V48 action_proof_link table + endpoints', () => {
  const models = backendSrc('app/kb/models.py');
  const store = backendSrc('app/kb/store.py');
  const router = backendSrc('app/kb/router.py');
  const actions = backendSrc('routes/actions.py');

  it('models.py crée la table action_proof_link', () => {
    expect(models).toContain('action_proof_link');
    expect(models).toContain('CREATE TABLE IF NOT EXISTS');
  });

  it('store.py a link_doc_to_action', () => {
    expect(store).toContain('def link_doc_to_action');
  });

  it('store.py a list_action_proofs', () => {
    expect(store).toContain('def list_action_proofs');
  });

  it('store.py a unlink_doc_from_action', () => {
    expect(store).toContain('def unlink_doc_from_action');
  });

  it('router.py accepte action_id sur upload', () => {
    expect(router).toContain('action_id');
  });

  it('actions.py a endpoint GET proofs', () => {
    expect(actions).toContain('/proofs');
    expect(actions).toContain('get_action_proofs');
  });

  it('actions.py a endpoint POST proofs link', () => {
    expect(actions).toContain('link_proof_to_action');
  });
});
