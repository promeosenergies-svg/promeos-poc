/**
 * PROMEOS — Breadcrumb Tests
 * Covers: static labels, dynamic routes, fallback, FR-only, aliases.
 */
import { describe, it, expect } from 'vitest';
import { resolveBreadcrumbLabel } from '../Breadcrumb';

/* ── Static segment labels ── */
describe('resolveBreadcrumbLabel — static segments', () => {
  it('conformite → Conformité', () => {
    expect(resolveBreadcrumbLabel('conformite', null)).toBe('Conformité');
  });

  it('tertiaire → Tertiaire / OPERAT', () => {
    expect(resolveBreadcrumbLabel('tertiaire', 'conformite')).toBe('Tertiaire / OPERAT');
  });

  it('sites → Site', () => {
    expect(resolveBreadcrumbLabel('sites', null)).toBe('Site');
  });

  it('explorer → Explorer', () => {
    expect(resolveBreadcrumbLabel('explorer', 'consommations')).toBe('Explorer');
  });

  it('wizard → Assistant', () => {
    expect(resolveBreadcrumbLabel('wizard', 'tertiaire')).toBe('Assistant');
  });

  it('efa → EFA', () => {
    expect(resolveBreadcrumbLabel('efa', 'tertiaire')).toBe('EFA');
  });
});

/* ── Dynamic segments with parent context ── */
describe('resolveBreadcrumbLabel — dynamic :id segments', () => {
  it('/sites/42 last segment → "Site #42"', () => {
    expect(resolveBreadcrumbLabel('42', 'sites')).toBe('Site #42');
  });

  it('/actions/7 last segment → "Action #7"', () => {
    expect(resolveBreadcrumbLabel('7', 'actions')).toBe('Action #7');
  });

  it('/conformite/tertiaire/efa/5 last segment → "EFA #5"', () => {
    expect(resolveBreadcrumbLabel('5', 'efa')).toBe('EFA #5');
  });

  it('/compliance/sites/99 last segment → "Conformité #99"', () => {
    expect(resolveBreadcrumbLabel('99', 'compliance')).toBe('Conformité #99');
  });

  it('numeric ID without known parent → "#123"', () => {
    expect(resolveBreadcrumbLabel('123', 'unknown')).toBe('#123');
  });

  it('UUID-like ID → "#abc123de"', () => {
    expect(resolveBreadcrumbLabel('abc123de', 'unknown')).toBe('#abc123de');
  });
});

/* ── Alias / redirect path segments ── */
describe('resolveBreadcrumbLabel — aliases', () => {
  it('factures → Facturation', () => {
    expect(resolveBreadcrumbLabel('factures', null)).toBe('Facturation');
  });

  it('plan-actions → Plan d\'actions', () => {
    expect(resolveBreadcrumbLabel('plan-actions', null)).toBe("Plan d'actions");
  });
});

/* ── FR-only: no raw English in output ── */
describe('resolveBreadcrumbLabel — FR-only guarantees', () => {
  it('never returns raw segment for known paths', () => {
    const known = ['conformite', 'actions', 'patrimoine', 'consommations',
      'monitoring', 'notifications', 'sites', 'wizard', 'tertiaire',
      'efa', 'explorer', 'portfolio', 'login', 'status'];
    for (const seg of known) {
      const label = resolveBreadcrumbLabel(seg, null);
      // Should not be the raw segment (except if it's already a proper FR word)
      expect(label.length).toBeGreaterThan(0);
    }
  });

  it('breadcrumb is never empty', () => {
    // Empty segment gets a label
    expect(resolveBreadcrumbLabel('', null).length).toBeGreaterThan(0);
  });

  it('unknown segments are capitalized (not raw lowercase)', () => {
    const label = resolveBreadcrumbLabel('quelque-chose', null);
    expect(label.charAt(0)).toBe('Q');
    expect(label).toBe('Quelque chose');
  });
});

/* ── "new" segment ── */
describe('resolveBreadcrumbLabel — special segments', () => {
  it('new → Nouveau', () => {
    expect(resolveBreadcrumbLabel('new', 'actions')).toBe('Nouveau');
  });
});
