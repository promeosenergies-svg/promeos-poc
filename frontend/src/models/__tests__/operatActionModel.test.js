/**
 * PROMEOS V46 — operatActionModel tests (logique pure)
 */
import { describe, it, expect } from 'vitest';
import {
  buildOperatActionKey,
  buildOperatActionPayload,
  buildOperatActionDeepLink,
  OPERAT_DUE_DAYS,
} from '../operatActionModel';

// ══════════════════════════════════════════════════════════════════════════════
// 1. buildOperatActionKey
// ══════════════════════════════════════════════════════════════════════════════

describe('buildOperatActionKey', () => {
  it('produces stable key from efa_id, year, issue_code', () => {
    const key = buildOperatActionKey({
      efa_id: 42,
      year: 2026,
      issue_code: 'TERTIAIRE_NO_BUILDING',
    });
    expect(key).toBe('operat:42:2026:TERTIAIRE_NO_BUILDING');
  });

  it('is deterministic (same input → same output)', () => {
    const params = { efa_id: 7, year: 2025, issue_code: 'MISSING_SURFACE' };
    expect(buildOperatActionKey(params)).toBe(buildOperatActionKey(params));
  });

  it('defaults year to current year if missing', () => {
    const key = buildOperatActionKey({ efa_id: 1, issue_code: 'X' });
    expect(key).toContain(`operat:1:${new Date().getFullYear()}:X`);
  });

  it('defaults issue_code to UNKNOWN if missing', () => {
    const key = buildOperatActionKey({ efa_id: 1, year: 2026 });
    expect(key).toContain('UNKNOWN');
  });
});

// ══════════════════════════════════════════════════════════════════════════════
// 2. buildOperatActionPayload
// ══════════════════════════════════════════════════════════════════════════════

describe('buildOperatActionPayload', () => {
  const baseEfa = { id: 42, nom: 'EFA Test', site_id: 10 };
  const baseIssue = {
    code: 'TERTIAIRE_NO_BUILDING',
    title_fr: 'Aucun bâtiment associé',
    message_fr: "L'EFA n'a aucun bâtiment",
    severity: 'critical',
    impact_fr: 'Blocage déclaration OPERAT',
    action_fr: 'Ajouter un bâtiment dans le patrimoine',
    proof_required: {
      type: 'preuve_surface_usage',
      label_fr: 'Preuve de surface',
      owner_role: 'gestionnaire_patrimoine',
      deadline_hint: 'Avant prochaine échéance',
    },
    proof_links: ['/kb?context=proof&proof_type=preuve_surface_usage&efa_id=42'],
  };

  it('returns valid payload with all fields', () => {
    const payload = buildOperatActionPayload({ efa: baseEfa, issue: baseIssue, year: 2026 });

    expect(payload.title).toBe('OPERAT — Aucun bâtiment associé');
    expect(payload.source_type).toBe('insight');
    expect(payload.source_id).toBe('operat:42:2026:TERTIAIRE_NO_BUILDING');
    expect(payload.severity).toBe('critical');
    expect(payload.priority).toBe(1);
    expect(payload.idempotency_key).toBe('operat-42-2026-TERTIAIRE_NO_BUILDING');
    expect(payload.site_id).toBe(10);
  });

  it('title is FR (starts with OPERAT)', () => {
    const payload = buildOperatActionPayload({ efa: baseEfa, issue: baseIssue });
    expect(payload.title).toMatch(/^OPERAT —/);
  });

  it('rationale contains 3 bullets FR (constat, impact, prochaine etape)', () => {
    const payload = buildOperatActionPayload({ efa: baseEfa, issue: baseIssue });
    expect(payload.rationale).toContain('Constat');
    expect(payload.rationale).toContain('Impact');
    expect(payload.rationale).toContain('Prochaine');
  });

  it('includes efa_url and anomalies_url in rationale', () => {
    const payload = buildOperatActionPayload({ efa: baseEfa, issue: baseIssue });
    expect(payload.rationale).toContain('/conformite/tertiaire/efa/42');
    expect(payload.rationale).toContain('/conformite/tertiaire/anomalies');
  });

  it('includes kb_open_url in rationale when provided', () => {
    const payload = buildOperatActionPayload({
      efa: baseEfa,
      issue: baseIssue,
      kb_open_url: '/kb?proof=test',
    });
    expect(payload.rationale).toContain('/kb?proof=test');
  });

  it('due_date is deterministic based on severity', () => {
    const p1 = buildOperatActionPayload({
      efa: baseEfa,
      issue: { ...baseIssue, severity: 'critical' },
    });
    const p2 = buildOperatActionPayload({ efa: baseEfa, issue: { ...baseIssue, severity: 'low' } });

    const d1 = new Date(p1.due_date);
    const d2 = new Date(p2.due_date);
    // critical=14j, low=90j → d2 should be later
    expect(d2.getTime()).toBeGreaterThan(d1.getTime());
  });

  it('OPERAT_DUE_DAYS maps severity correctly', () => {
    expect(OPERAT_DUE_DAYS.critical).toBe(14);
    expect(OPERAT_DUE_DAYS.high).toBe(30);
    expect(OPERAT_DUE_DAYS.medium).toBe(60);
    expect(OPERAT_DUE_DAYS.low).toBe(90);
  });

  it('meta contains all required fields', () => {
    const payload = buildOperatActionPayload({ efa: baseEfa, issue: baseIssue, year: 2026 });
    expect(payload._meta).toEqual({
      domain: 'conformite/tertiaire-operat',
      efa_id: 42,
      year: 2026,
      issue_code: 'TERTIAIRE_NO_BUILDING',
      proof_type: 'preuve_surface_usage',
      proof_required: baseIssue.proof_required,
      kb_open_url: null,
      efa_url: '/conformite/tertiaire/efa/42',
      anomalies_url: '/conformite/tertiaire/anomalies',
    });
  });

  it('notes contain proof info when proof_required', () => {
    const payload = buildOperatActionPayload({ efa: baseEfa, issue: baseIssue });
    expect(payload.notes).toContain('Preuve attendue');
    expect(payload.notes).toContain('Preuve de surface');
    expect(payload.notes).toContain('gestionnaire_patrimoine');
  });

  it('handles missing issue gracefully (degraded payload)', () => {
    const payload = buildOperatActionPayload({ efa: baseEfa, issue: null });
    expect(payload.title).toContain('à clarifier');
    expect(payload.source_type).toBe('insight');
    expect(payload.idempotency_key).toContain('unknown');
  });

  it('handles missing efa gracefully (degraded payload)', () => {
    const payload = buildOperatActionPayload({ efa: null, issue: baseIssue });
    expect(payload.title).toContain('à clarifier');
  });

  it('uses issue.code as title fallback when title_fr absent', () => {
    const issue = { code: 'TERTIAIRE_NO_BUILDING', severity: 'high' };
    const payload = buildOperatActionPayload({ efa: baseEfa, issue });
    expect(payload.title).toBe('OPERAT — TERTIAIRE_NO_BUILDING');
  });

  it('omits site_id when efa has no site_id', () => {
    const payload = buildOperatActionPayload({
      efa: { id: 1, nom: 'EFA' },
      issue: baseIssue,
    });
    expect(payload.site_id).toBeUndefined();
  });
});

// ══════════════════════════════════════════════════════════════════════════════
// 3. buildOperatActionDeepLink
// ══════════════════════════════════════════════════════════════════════════════

describe('buildOperatActionDeepLink', () => {
  it('returns /actions with source=operat', () => {
    const payload = buildOperatActionPayload({
      efa: { id: 5, nom: 'X' },
      issue: { code: 'A', severity: 'high' },
      year: 2026,
    });
    const link = buildOperatActionDeepLink(payload);
    expect(link).toContain('/actions?');
    expect(link).toContain('source=operat');
  });

  it('includes efa_id and issue_code', () => {
    const payload = buildOperatActionPayload({
      efa: { id: 5, nom: 'X' },
      issue: { code: 'TERTIAIRE_NO_BUILDING', severity: 'critical' },
    });
    const link = buildOperatActionDeepLink(payload);
    expect(link).toContain('efa_id=5');
    expect(link).toContain('issue_code=TERTIAIRE_NO_BUILDING');
  });

  it('includes severity', () => {
    const payload = buildOperatActionPayload({
      efa: { id: 1, nom: 'X' },
      issue: { code: 'A', severity: 'critical' },
    });
    const link = buildOperatActionDeepLink(payload);
    expect(link).toContain('severity=critical');
  });

  it('handles null payload gracefully', () => {
    expect(buildOperatActionDeepLink(null)).toBe('/actions');
  });

  it('deep-link is URL-encoded and stable', () => {
    const payload = buildOperatActionPayload({
      efa: { id: 3, nom: 'Y' },
      issue: { code: 'B', severity: 'medium' },
    });
    const l1 = buildOperatActionDeepLink(payload);
    const l2 = buildOperatActionDeepLink(payload);
    expect(l1).toBe(l2);
  });
});

// ══════════════════════════════════════════════════════════════════════════════
// 4. Source guards
// ══════════════════════════════════════════════════════════════════════════════

describe('operatActionModel source guards', () => {
  const fs = require('node:fs');
  const path = require('node:path');
  const src = fs.readFileSync(path.resolve(__dirname, '..', 'operatActionModel.js'), 'utf-8');

  it('exports buildOperatActionKey', () => {
    expect(src).toContain('export function buildOperatActionKey');
  });

  it('exports buildOperatActionPayload', () => {
    expect(src).toContain('export function buildOperatActionPayload');
  });

  it('exports buildOperatActionDeepLink', () => {
    expect(src).toContain('export function buildOperatActionDeepLink');
  });

  it('exports OPERAT_DUE_DAYS', () => {
    expect(src).toContain('export const OPERAT_DUE_DAYS');
  });

  it('uses source_type insight', () => {
    expect(src).toContain("source_type: 'insight'");
  });

  it('uses operat prefix for idempotency_key', () => {
    expect(src).toContain('operat-');
  });

  it('contains FR strings (Constat, Impact, Prochaine)', () => {
    expect(src).toContain('Constat');
    expect(src).toContain('Impact');
    expect(src).toContain('Prochaine');
  });
});
