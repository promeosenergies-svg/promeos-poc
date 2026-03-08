/**
 * PROMEOS — evidenceRules tests (Étape 4.1)
 * Tests: computeEvidenceRequirement, EVIDENCE_RULES, SOURCE_LABELS_FR, buildSourceDeepLink.
 */
import { describe, it, expect } from 'vitest';
import {
  computeEvidenceRequirement,
  EVIDENCE_RULES,
  SOURCE_LABELS_FR,
  buildSourceDeepLink,
} from '../evidenceRules';

// ── computeEvidenceRequirement ────────────────────────────────────────────

describe('computeEvidenceRequirement', () => {
  // FORCE rules
  it('compliance + critical → lock=true, required=true, label contains "Requis"', () => {
    const result = computeEvidenceRequirement({ sourceType: 'compliance', severity: 'critical' });
    expect(result.required).toBe(true);
    expect(result.lock).toBe(true);
    expect(result.labelFR).toContain('Requis');
  });

  // RECOMMEND rules
  it('compliance + high → lock=false, required=true, label contains "Recommandé"', () => {
    const result = computeEvidenceRequirement({ sourceType: 'compliance', severity: 'high' });
    expect(result.required).toBe(true);
    expect(result.lock).toBe(false);
    expect(result.labelFR).toContain('Recommandé');
  });

  it('billing + critical → recommend, required=true', () => {
    const result = computeEvidenceRequirement({ sourceType: 'billing', severity: 'critical' });
    expect(result.required).toBe(true);
    expect(result.lock).toBe(false);
    expect(result.labelFR).toContain('Recommandé');
  });

  it('billing + high → recommend, required=true', () => {
    const result = computeEvidenceRequirement({ sourceType: 'billing', severity: 'high' });
    expect(result.required).toBe(true);
    expect(result.lock).toBe(false);
  });

  it('insight + critical → recommend, required=true', () => {
    const result = computeEvidenceRequirement({ sourceType: 'insight', severity: 'critical' });
    expect(result.required).toBe(true);
    expect(result.lock).toBe(false);
  });

  // Severity fallback
  it('manual + critical → required=true (severity fallback), lock=false', () => {
    const result = computeEvidenceRequirement({ sourceType: 'manual', severity: 'critical' });
    expect(result.required).toBe(true);
    expect(result.lock).toBe(false);
    expect(result.labelFR).toContain('critique');
  });

  it('manual + high → required=true (severity fallback)', () => {
    const result = computeEvidenceRequirement({ sourceType: 'manual', severity: 'high' });
    expect(result.required).toBe(true);
    expect(result.lock).toBe(false);
  });

  // No requirement
  it('manual + medium → required=false', () => {
    const result = computeEvidenceRequirement({ sourceType: 'manual', severity: 'medium' });
    expect(result.required).toBe(false);
    expect(result.lock).toBe(false);
  });

  it('manual + low → required=false', () => {
    const result = computeEvidenceRequirement({ sourceType: 'manual', severity: 'low' });
    expect(result.required).toBe(false);
  });

  it('no params → required=false', () => {
    const result = computeEvidenceRequirement();
    expect(result.required).toBe(false);
    expect(result.lock).toBe(false);
    expect(result.labelFR).toBe('');
  });

  // Priority: FORCE > RECOMMEND > fallback
  it('FORCE wins over severity fallback', () => {
    // compliance + critical matches FORCE, not just severity fallback
    const result = computeEvidenceRequirement({ sourceType: 'compliance', severity: 'critical' });
    expect(result.lock).toBe(true); // FORCE has lock=true
  });
});

// ── EVIDENCE_RULES structure ──────────────────────────────────────────────

describe('EVIDENCE_RULES', () => {
  it('force rules have sourceType + severity + labelFR', () => {
    for (const rule of EVIDENCE_RULES.force) {
      expect(rule).toHaveProperty('sourceType');
      expect(rule).toHaveProperty('severity');
      expect(rule).toHaveProperty('labelFR');
      expect(rule.labelFR.length).toBeGreaterThan(0);
    }
  });

  it('recommend rules have sourceType + severity + labelFR', () => {
    for (const rule of EVIDENCE_RULES.recommend) {
      expect(rule).toHaveProperty('sourceType');
      expect(rule).toHaveProperty('severity');
      expect(rule).toHaveProperty('labelFR');
      expect(rule.labelFR.length).toBeGreaterThan(0);
    }
  });

  it('at least 1 force rule and 3+ recommend rules', () => {
    expect(EVIDENCE_RULES.force.length).toBeGreaterThanOrEqual(1);
    expect(EVIDENCE_RULES.recommend.length).toBeGreaterThanOrEqual(3);
  });
});

// ── SOURCE_LABELS_FR ──────────────────────────────────────────────────────

describe('SOURCE_LABELS_FR', () => {
  it('contains all expected source types in French', () => {
    expect(SOURCE_LABELS_FR.compliance).toBe('Conformité');
    expect(SOURCE_LABELS_FR.billing).toBe('Facturation');
    expect(SOURCE_LABELS_FR.consumption).toBe('Consommation');
    expect(SOURCE_LABELS_FR.purchase).toBe('Achats');
    expect(SOURCE_LABELS_FR.manual).toBe('Manuelle');
    expect(SOURCE_LABELS_FR.insight).toBe('Diagnostic');
  });

  it('no English words in labels', () => {
    const englishWords = ['compliance', 'billing', 'consumption', 'purchase', 'manual', 'insight'];
    for (const label of Object.values(SOURCE_LABELS_FR)) {
      for (const eng of englishWords) {
        expect(label.toLowerCase()).not.toBe(eng);
      }
    }
  });
});

// ── buildSourceDeepLink ─────────────────────────────────────────────────

describe('buildSourceDeepLink', () => {
  it('compliance → /conformite?tab=obligations', () => {
    expect(buildSourceDeepLink('compliance', 'BACS')).toBe('/conformite?tab=obligations');
  });

  it('billing → /bill-intel', () => {
    expect(buildSourceDeepLink('billing', '42')).toBe('/bill-intel');
  });

  it('consumption → /consommations/explorer', () => {
    expect(buildSourceDeepLink('consumption', '1')).toBe('/consommations/explorer');
  });

  it('purchase → /achats', () => {
    expect(buildSourceDeepLink('purchase', 'contract-5')).toBe('/achats');
  });

  it('insight readiness:xxx → /activation', () => {
    expect(buildSourceDeepLink('insight', 'readiness:data_ko')).toBe('/activation');
  });

  it('insight operat:xxx → /conformite/tertiaire/efa/{id}', () => {
    expect(buildSourceDeepLink('insight', 'operat:42:2024:dpe')).toBe(
      '/conformite/tertiaire/efa/42'
    );
  });

  it('insight other → /anomalies', () => {
    expect(buildSourceDeepLink('insight', 'diag:123')).toBe('/anomalies');
  });

  it('manual → null (no deep link)', () => {
    expect(buildSourceDeepLink('manual', 'manual_123')).toBeNull();
  });

  it('null/empty → null', () => {
    expect(buildSourceDeepLink(null, null)).toBeNull();
    expect(buildSourceDeepLink('', '')).toBeNull();
  });
});

// ── FR-only invariant ───────────────────────────────────────────────────

describe('FR-only invariant', () => {
  it('all FORCE labelFR are in French (no English)', () => {
    for (const rule of EVIDENCE_RULES.force) {
      expect(rule.labelFR).not.toMatch(/required|recommended|evidence/i);
    }
  });

  it('all RECOMMEND labelFR are in French', () => {
    for (const rule of EVIDENCE_RULES.recommend) {
      expect(rule.labelFR).not.toMatch(/required|recommended|evidence/i);
    }
  });

  it('computeEvidenceRequirement never returns English labelFR', () => {
    const combos = [
      { sourceType: 'compliance', severity: 'critical' },
      { sourceType: 'billing', severity: 'high' },
      { sourceType: 'manual', severity: 'critical' },
      { sourceType: 'manual', severity: 'medium' },
    ];
    for (const combo of combos) {
      const result = computeEvidenceRequirement(combo);
      if (result.labelFR) {
        expect(result.labelFR).not.toMatch(/required|recommended|evidence/i);
      }
    }
  });
});

// ── Idempotency source guards ──────────────────────────────────────────
// Deferred: CreateActionDrawer.jsx, ActionDrawerContext.jsx not yet created.

// ── Source tracing source guards ────────────────────────────────────────
// Deferred: ActionDetailDrawer.jsx, action_close_rules.py, actions.py not yet created.
