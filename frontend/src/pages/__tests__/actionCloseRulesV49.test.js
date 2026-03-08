/**
 * PROMEOS V49 — Source guards: Action Close Rules + Guided Close UX
 * Checks presence of close rules enforcement, justification textarea,
 * backend error handling, and closeability API.
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

// ── API: closeability endpoint ──────────────────────────────────────────────

describe('API — V49 closeability endpoint', () => {
  const code = src('services/api.js');

  it('exporte checkActionCloseability', () => {
    expect(code).toContain('checkActionCloseability');
  });

  it('appelle /closeability', () => {
    expect(code).toContain('/closeability');
  });
});

// ── ActionDetailDrawer — V49 guided close ───────────────────────────────────

describe('ActionDetailDrawer — V49 guided close flow', () => {
  const code = src('components/ActionDetailDrawer.jsx');

  it('importe checkActionCloseability', () => {
    expect(code).toContain('checkActionCloseability');
  });

  it('declare closureJustification state', () => {
    expect(code).toContain('closureJustification');
    expect(code).toContain('setClosureJustification');
  });

  it('declare closeError state', () => {
    expect(code).toContain('closeError');
    expect(code).toContain('setCloseError');
  });

  it('declare showCloseForm state', () => {
    expect(code).toContain('showCloseForm');
    expect(code).toContain('setShowCloseForm');
  });

  it('appelle checkActionCloseability dans handleStatusChange', () => {
    expect(code).toContain('checkActionCloseability(actionId)');
  });

  it('envoie closure_justification dans le PATCH', () => {
    expect(code).toContain('closure_justification');
    expect(code).toContain('closureJustification.trim()');
  });

  it('gere le HTTP 400 du backend', () => {
    expect(code).toContain('response?.status === 400');
  });

  it('contient le data-testid close-form', () => {
    expect(code).toContain('close-form');
  });

  it('contient le textarea closure-justification', () => {
    expect(code).toContain('closure-justification');
  });

  it('contient le bouton Cloturer avec commentaire', () => {
    expect(code).toContain('avec commentaire');
  });

  it('affiche le compteur de caracteres', () => {
    expect(code).toContain('/10');
  });

  it('affiche la justification de cloture si presente', () => {
    expect(code).toContain('v49-closure-justification-display');
    expect(code).toContain('d.closure_justification');
  });

  it('conserve le bloc operat-proof-bloc', () => {
    expect(code).toContain('operat-proof-bloc');
  });

  it('conserve le CTA Deposer une preuve', () => {
    expect(code).toContain('Déposer une preuve');
  });

  it('conserve le gating operatBlocked', () => {
    expect(code).toContain('operatBlocked');
  });

  it('met a jour aide FR avec V49 rules', () => {
    expect(code).toContain('justification de clôture');
    expect(code).toContain('serveur');
  });
});

// ── KBExplorerPage — V49 close rule hint ────────────────────────────────────

describe('KBExplorerPage — V49 close rule hint', () => {
  const code = src('pages/KBExplorerPage.jsx');

  it('contient le data-testid v49-close-rule-hint', () => {
    expect(code).toContain('v49-close-rule-hint');
  });

  it('affiche le texte preuve validee permet de cloturer', () => {
    expect(code).toContain('preuve valid');
    expect(code).toContain('action');
  });
});

// ── Backend — V49 source guards ─────────────────────────────────────────────

describe('Backend — V49 action_close_rules.py', () => {
  const rules = backendSrc('services/action_close_rules.py');
  const route = backendSrc('routes/actions.py');
  const model = backendSrc('models/action_item.py');

  it('action_close_rules.py a is_operat_action', () => {
    expect(rules).toContain('def is_operat_action');
  });

  it('action_close_rules.py a check_closable', () => {
    expect(rules).toContain('def check_closable');
  });

  it('action_close_rules.py verifie validated + decisional', () => {
    expect(rules).toContain('validated');
    expect(rules).toContain('decisional');
  });

  it('action_close_rules.py verifie longueur >= 10', () => {
    expect(rules).toContain('10');
  });

  it('actions.py importe close rules', () => {
    expect(route).toContain('from services.action_close_rules import');
  });

  it('actions.py enforce close sur PATCH done', () => {
    expect(route).toContain('check_closable');
    expect(route).toContain('is_operat_action');
  });

  it('actions.py a endpoint closeability', () => {
    expect(route).toContain('closeability');
    expect(route).toContain('get_action_closeability');
  });

  it('actions.py serialise closure_justification', () => {
    expect(route).toContain('closure_justification');
  });

  it('model a colonne closure_justification', () => {
    expect(model).toContain('closure_justification');
  });
});
