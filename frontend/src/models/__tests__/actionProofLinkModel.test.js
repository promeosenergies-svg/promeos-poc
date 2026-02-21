/**
 * PROMEOS V47 — Tests actionProofLinkModel (logique pure)
 */
import { describe, it, expect } from 'vitest';
import {
  parseOperatSourceId,
  isOperatAction,
  buildActionProofLink,
  buildActionProofContext,
  isActionClosable,
  resolveProofStatus,
  PROOF_STATUS_LABELS,
  PROOF_STATUS_BADGE,
} from '../actionProofLinkModel';

// ── parseOperatSourceId ──────────────────────────────────────────────────────

describe('parseOperatSourceId', () => {
  it('parse un source_id valide', () => {
    const r = parseOperatSourceId('operat:42:2026:TERTIAIRE_NO_BUILDING');
    expect(r).toEqual({ efa_id: '42', year: '2026', issue_code: 'TERTIAIRE_NO_BUILDING' });
  });

  it('gère les issue_code avec ":" (rejoint les segments)', () => {
    const r = parseOperatSourceId('operat:1:2025:CODE:SUB');
    expect(r).toEqual({ efa_id: '1', year: '2025', issue_code: 'CODE:SUB' });
  });

  it('retourne null pour un source_id non-OPERAT', () => {
    expect(parseOperatSourceId('compliance:123')).toBeNull();
  });

  it('retourne null pour null/undefined/vide', () => {
    expect(parseOperatSourceId(null)).toBeNull();
    expect(parseOperatSourceId(undefined)).toBeNull();
    expect(parseOperatSourceId('')).toBeNull();
  });

  it('retourne null si moins de 4 segments', () => {
    expect(parseOperatSourceId('operat:42:2026')).toBeNull();
  });
});

// ── isOperatAction ───────────────────────────────────────────────────────────

describe('isOperatAction', () => {
  it('détecte une action OPERAT', () => {
    expect(isOperatAction({ source_type: 'insight', source_id: 'operat:1:2026:X' })).toBe(true);
  });

  it('rejette une action insight non-OPERAT', () => {
    expect(isOperatAction({ source_type: 'insight', source_id: 'conso:abc' })).toBe(false);
  });

  it('rejette une action compliance', () => {
    expect(isOperatAction({ source_type: 'compliance', source_id: 'operat:1:2026:X' })).toBe(false);
  });

  it('gère null/undefined', () => {
    expect(isOperatAction(null)).toBe(false);
    expect(isOperatAction(undefined)).toBe(false);
  });
});

// ── buildActionProofLink ─────────────────────────────────────────────────────

describe('buildActionProofLink', () => {
  const action = {
    id: 99,
    source_type: 'insight',
    source_id: 'operat:42:2026:NO_CONSO_DATA',
    title: 'OPERAT — Données conso manquantes',
  };

  it('construit une URL /kb?context=proof avec efa_id et action_id', () => {
    const url = buildActionProofLink(action);
    expect(url).toContain('context=proof');
    expect(url).toContain('efa_id=42');
    expect(url).toContain('action_id=99');
    expect(url).toContain('domain=reglementaire');
  });

  it('contient un hint FR', () => {
    const url = buildActionProofLink(action);
    expect(url).toContain('hint=');
    expect(url).toContain('EFA');
    expect(url).toContain('42');
  });

  it('retourne /kb pour action null', () => {
    expect(buildActionProofLink(null)).toBe('/kb');
  });

  it('retourne /kb?context=proof pour action non-OPERAT', () => {
    expect(buildActionProofLink({ source_id: 'conso:abc' })).toBe('/kb?context=proof');
  });
});

// ── buildActionProofContext ──────────────────────────────────────────────────

describe('buildActionProofContext', () => {
  const action = {
    id: 77,
    source_type: 'insight',
    source_id: 'operat:10:2025:PROOF_MISSING',
    title: 'OPERAT — Preuve manquante',
  };

  it('extrait efa_id, year, issue_code depuis source_id', () => {
    const ctx = buildActionProofContext(action);
    expect(ctx.efa_id).toBe('10');
    expect(ctx.year).toBe('2025');
    expect(ctx.issue_code).toBe('PROOF_MISSING');
    expect(ctx.action_id).toBe(77);
    expect(ctx.domain).toBe('reglementaire');
  });

  it('construit un hint FR contenant les tags', () => {
    const ctx = buildActionProofContext(action);
    expect(ctx.hint).toContain('EFA #10');
    expect(ctx.hint).toContain('PROOF_MISSING');
  });

  it('gère action null', () => {
    const ctx = buildActionProofContext(null);
    expect(ctx.efa_id).toBeNull();
    expect(ctx.action_id).toBeNull();
    expect(ctx.domain).toBe('reglementaire');
  });
});

// ── isActionClosable ─────────────────────────────────────────────────────────

describe('isActionClosable', () => {
  const action = { id: 1, status: 'in_progress', notes: '' };

  it('closable si preuve validée côté EFA', () => {
    const r = isActionClosable(action, { validated_count: 1, deposited_count: 1, expected_count: 2 });
    expect(r.closable).toBe(true);
    expect(r.raisons).toHaveLength(0);
  });

  it('closable si pièce jointe présente', () => {
    const r = isActionClosable(action, { validated_count: 0 }, 1);
    expect(r.closable).toBe(true);
  });

  it('closable si notes contiennent [justifié]', () => {
    const r = isActionClosable({ ...action, notes: 'Raison [justifié] ok' }, null, 0);
    expect(r.closable).toBe(true);
  });

  it('non closable sans preuve ni justification', () => {
    const r = isActionClosable(action, { validated_count: 0, deposited_count: 0 }, 0);
    expect(r.closable).toBe(false);
    expect(r.raisons.length).toBeGreaterThan(0);
    expect(r.raisons.some(r => r.includes('preuve'))).toBe(true);
  });

  it('raisons FR contiennent le conseil [justifié]', () => {
    const r = isActionClosable(action, null, 0);
    expect(r.raisons.some(r => r.includes('[justifié]'))).toBe(true);
  });

  it('déjà terminée = closable', () => {
    const r = isActionClosable({ ...action, status: 'done' }, null, 0);
    expect(r.closable).toBe(true);
    expect(r.raisons[0]).toContain('clôturée');
  });

  it('action null = non closable', () => {
    const r = isActionClosable(null);
    expect(r.closable).toBe(false);
  });
});

// ── resolveProofStatus ───────────────────────────────────────────────────────

describe('resolveProofStatus', () => {
  it('validated si validated_count > 0', () => {
    expect(resolveProofStatus({ validated_count: 2, deposited_count: 3 })).toBe('validated');
  });

  it('draft si deposited mais pas validated', () => {
    expect(resolveProofStatus({ validated_count: 0, deposited_count: 1 })).toBe('draft');
  });

  it('none si aucune preuve', () => {
    expect(resolveProofStatus({ validated_count: 0, deposited_count: 0 })).toBe('none');
  });

  it('none pour null/undefined', () => {
    expect(resolveProofStatus(null)).toBe('none');
    expect(resolveProofStatus(undefined)).toBe('none');
  });
});

// ── Constantes FR ────────────────────────────────────────────────────────────

describe('constantes FR', () => {
  it('PROOF_STATUS_LABELS a 4 entrées FR', () => {
    expect(Object.keys(PROOF_STATUS_LABELS)).toHaveLength(4);
    expect(PROOF_STATUS_LABELS.none).toContain('Aucune');
    expect(PROOF_STATUS_LABELS.validated).toContain('validée');
  });

  it('PROOF_STATUS_BADGE a 4 entrées', () => {
    expect(Object.keys(PROOF_STATUS_BADGE)).toHaveLength(4);
    expect(PROOF_STATUS_BADGE.validated).toBe('ok');
    expect(PROOF_STATUS_BADGE.none).toBe('neutral');
  });
});
