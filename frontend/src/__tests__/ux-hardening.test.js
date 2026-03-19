/**
 * PROMEOS — UX Enterprise Hardening Tests
 * Vérifie la cohérence des composants UI de base.
 */
import { describe, test, expect } from 'vitest';
import {
  normalizeRisk,
  formatRiskEur,
  getSiteRisk,
  RISK_LEVELS,
} from '../lib/risk/normalizeRisk.jsx';

describe('normalizeRisk', () => {
  test('null/undefined returns inconnu', () => {
    expect(normalizeRisk(null).level).toBe('inconnu');
    expect(normalizeRisk(undefined).level).toBe('inconnu');
  });

  test('0 EUR = faible', () => {
    expect(normalizeRisk(0).level).toBe('faible');
  });

  test('5000 EUR = modere', () => {
    expect(normalizeRisk(5000).level).toBe('modere');
  });

  test('15000 EUR = eleve', () => {
    expect(normalizeRisk(15000).level).toBe('eleve');
  });

  test('30000 EUR = critique', () => {
    expect(normalizeRisk(30000).level).toBe('critique');
  });

  test('all levels have label and color', () => {
    for (const [key, level] of Object.entries(RISK_LEVELS)) {
      expect(level.label).toBeTruthy();
      expect(level.color).toBeTruthy();
      expect(level.bg).toBeTruthy();
    }
  });
});

describe('formatRiskEur', () => {
  test('null returns dash', () => {
    expect(formatRiskEur(null)).toBe('—');
  });

  test('500 returns "500 €"', () => {
    expect(formatRiskEur(500)).toBe('500 €');
  });

  test('26000 returns "26 k€"', () => {
    expect(formatRiskEur(26000)).toBe('26 k€');
  });

  test('1500000 returns "1.5 M€"', () => {
    expect(formatRiskEur(1500000)).toBe('1.5 M€');
  });
});

describe('getSiteRisk', () => {
  test('prefers risque_eur', () => {
    expect(getSiteRisk({ risque_eur: 100, risque_financier_euro: 200 })).toBe(100);
  });

  test('falls back to risque_financier_euro', () => {
    expect(getSiteRisk({ risque_financier_euro: 200 })).toBe(200);
  });

  test('falls back to total_risk_eur', () => {
    expect(getSiteRisk({ total_risk_eur: 300 })).toBe(300);
  });

  test('returns 0 for empty site', () => {
    expect(getSiteRisk({})).toBe(0);
  });
});

describe('UnifiedKpiCard component', () => {
  test('module exports exist', async () => {
    const mod = await import('../ui/UnifiedKpiCard');
    expect(mod.default).toBeDefined();
    expect(mod.UnifiedKpiCardGrid).toBeDefined();
  });
});

describe('EmptyState component', () => {
  test('module exports exist', async () => {
    const mod = await import('../ui/EmptyState');
    expect(mod.default).toBeDefined();
  });
});

describe('Sidebar labels', () => {
  test('NavRail has label text elements', async () => {
    // Verify the NavRail component file contains label rendering
    const fs = await import('fs');
    const content = fs.readFileSync('src/layout/NavRail.jsx', 'utf-8');
    expect(content).toContain('text-[10px]');
    expect(content).toContain('mod.label');
  });
});

describe('Renamed labels', () => {
  test('EssentialsRow uses new labels', async () => {
    const fs = await import('fs');
    const content = fs.readFileSync('src/pages/cockpit/EssentialsRow.jsx', 'utf-8');
    expect(content).toContain('Données exploitables');
    expect(content).toContain('Couverture opérationnelle');
    expect(content).not.toContain('Complétude données');
  });
});

describe('Deep links', () => {
  test('Patrimoine has conformite CTA', async () => {
    const fs = await import('fs');
    const content = fs.readFileSync('src/pages/Patrimoine.jsx', 'utf-8');
    expect(content).toContain('Conformité');
    expect(content).toContain('/conformite');
  });

  test('BillIntelPage has achat CTA', async () => {
    const fs = await import('fs');
    const content = fs.readFileSync('src/pages/BillIntelPage.jsx', 'utf-8');
    expect(content).toContain('/achat');
    expect(content).toContain('achat');
  });
});

describe('Migration verification', () => {
  test('Cockpit imports RiskBadge', async () => {
    const fs = await import('fs');
    const content = fs.readFileSync('src/pages/Cockpit.jsx', 'utf-8');
    expect(content).toContain('RiskBadge');
  });

  test('Patrimoine imports RiskBadge', async () => {
    const fs = await import('fs');
    const content = fs.readFileSync('src/pages/Patrimoine.jsx', 'utf-8');
    expect(content).toContain('RiskBadge');
  });

  test('Patrimoine imports EmptyState', async () => {
    const fs = await import('fs');
    const content = fs.readFileSync('src/pages/Patrimoine.jsx', 'utf-8');
    expect(content).toContain('EmptyState');
  });

  test('Risk taxonomy has exactly 4 levels + inconnu', async () => {
    const { RISK_LEVELS } = await import('../lib/risk/normalizeRisk');
    const keys = Object.keys(RISK_LEVELS);
    expect(keys).toContain('faible');
    expect(keys).toContain('modere');
    expect(keys).toContain('eleve');
    expect(keys).toContain('critique');
    expect(keys).toContain('inconnu');
    expect(keys.length).toBe(5);
  });
});
