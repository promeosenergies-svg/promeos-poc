/**
 * PROMEOS — dossierRunbook tests (Étape 5)
 * Tests: buildDossier, groupActionsByWeek, computeCloseabilityBadge,
 *        export view content, source tracing links.
 */
import { describe, it, expect } from 'vitest';
import {
  buildDossier,
  groupActionsByWeek,
  computeCloseabilityBadge,
  DOSSIER_SECTION_LABELS,
  STATUS_LABELS_FR,
  PRIORITY_LABELS_FR,
} from '../dossierModel';
import { buildSourceDeepLink } from '../evidenceRules';

// ── Helper: mock actions ──────────────────────────────────────────────────

function mockAction(overrides = {}) {
  return {
    id: 1,
    title: 'Action test',
    source_type: 'compliance',
    source_id: 'BACS',
    source_key: 'rule:0',
    status: 'open',
    priority: 2,
    severity: 'high',
    owner: 'Jean',
    due_date: '2026-03-10',
    evidence_required: false,
    source_label: 'Conformité',
    ...overrides,
  };
}

function mockFEAction(overrides = {}) {
  return {
    id: 1,
    titre: 'Action FE',
    type: 'conformite',
    statut: 'backlog',
    priorite: 'high',
    owner: 'Jean',
    due_date: '2026-03-10',
    impact_eur: 5000,
    _backend: { evidence_required: false, evidence_count: 0 },
    ...overrides,
  };
}

// ── buildDossier ────────────────────────────────────────────────────────

describe('buildDossier', () => {
  it('returns empty structure for null source', () => {
    const dossier = buildDossier(null, [], new Map());
    expect(dossier.header).toBeNull();
    expect(dossier.actions).toHaveLength(0);
    expect(dossier.stats.total).toBe(0);
  });

  it('includes linked actions and preuves', () => {
    const actions = [
      mockAction({ id: 1, source_type: 'compliance', source_id: 'BACS' }),
      mockAction({ id: 2, source_type: 'compliance', source_id: 'BACS', evidence_required: true }),
      mockAction({ id: 3, source_type: 'billing', source_id: '99' }), // not linked
    ];
    const evidenceMap = new Map([
      [1, [{ label: 'Attestation', file_url: '/files/att.pdf' }]],
      [2, []], // no evidence but required
    ]);
    const dossier = buildDossier(
      { sourceType: 'compliance', sourceId: 'BACS', label: 'BACS Conformité' },
      actions,
      evidenceMap
    );

    expect(dossier.header.sourceLabel).toBe('BACS Conformité');
    expect(dossier.header.sourceType).toBe('compliance');
    expect(dossier.actions).toHaveLength(2); // only linked
    expect(dossier.evidence).toHaveLength(1); // one proof from action 1
    expect(dossier.evidence[0].label).toBe('Attestation');
    expect(dossier.stats.total).toBe(2);
    expect(dossier.stats.evidenceCount).toBe(1);
  });

  it('identifies missing evidence items', () => {
    const actions = [mockAction({ id: 10, evidence_required: true, owner: null })];
    const dossier = buildDossier(
      { sourceType: 'compliance', sourceId: 'BACS' },
      actions,
      new Map([[10, []]])
    );
    expect(dossier.missing.length).toBeGreaterThanOrEqual(1);
    const evidenceMissing = dossier.missing.find((m) => m.type === 'evidence_missing');
    expect(evidenceMissing).toBeDefined();
    expect(evidenceMissing.labelFR).toContain('Preuve requise');
  });

  it('identifies missing owner', () => {
    const actions = [mockAction({ id: 11, owner: null })];
    const dossier = buildDossier(
      { sourceType: 'compliance', sourceId: 'BACS' },
      actions,
      new Map()
    );
    const ownerMissing = dossier.missing.find((m) => m.type === 'owner_missing');
    expect(ownerMissing).toBeDefined();
    expect(ownerMissing.labelFR).toContain('Responsable');
  });

  it('header has deepLink for compliance source', () => {
    const dossier = buildDossier({ sourceType: 'compliance', sourceId: 'RT2012' }, [], new Map());
    expect(dossier.header.deepLink).toBe('/conformite?tab=obligations');
  });

  it('counts done vs open correctly', () => {
    const actions = [
      mockAction({ id: 1, status: 'done' }),
      mockAction({ id: 2, status: 'open' }),
      mockAction({ id: 3, status: 'in_progress' }),
    ];
    const dossier = buildDossier(
      { sourceType: 'compliance', sourceId: 'BACS' },
      actions,
      new Map()
    );
    expect(dossier.stats.done).toBe(1);
    expect(dossier.stats.open).toBe(2);
  });
});

// ── groupActionsByWeek ──────────────────────────────────────────────────

describe('groupActionsByWeek', () => {
  it('groups actions into overdue/today/week/later buckets', () => {
    const today = new Date().toISOString().slice(0, 10);
    const yesterday = new Date(Date.now() - 86400000).toISOString().slice(0, 10);
    const in3days = new Date(Date.now() + 3 * 86400000).toISOString().slice(0, 10);
    const in30days = new Date(Date.now() + 30 * 86400000).toISOString().slice(0, 10);

    const actions = [
      mockFEAction({ id: 1, due_date: yesterday }),
      mockFEAction({ id: 2, due_date: today }),
      mockFEAction({ id: 3, due_date: in3days }),
      mockFEAction({ id: 4, due_date: in30days }),
      mockFEAction({ id: 5, due_date: null }), // no due date → later
    ];

    const groups = groupActionsByWeek(actions);
    expect(groups.overdue).toHaveLength(1);
    expect(groups.overdue[0].id).toBe(1);
    expect(groups.today).toHaveLength(1);
    expect(groups.today[0].id).toBe(2);
    expect(groups.week).toHaveLength(1);
    expect(groups.week[0].id).toBe(3);
    expect(groups.later).toHaveLength(2); // 30 days + no date
  });

  it('excludes done actions', () => {
    const yesterday = new Date(Date.now() - 86400000).toISOString().slice(0, 10);
    const actions = [mockFEAction({ id: 1, due_date: yesterday, statut: 'done' })];
    const groups = groupActionsByWeek(actions);
    expect(groups.overdue).toHaveLength(0);
  });
});

// ── computeCloseabilityBadge ──────────────────────────────────────────

describe('computeCloseabilityBadge', () => {
  it('done → "Clôturée" ok', () => {
    const badge = computeCloseabilityBadge(mockFEAction({ statut: 'done' }));
    expect(badge.label).toBe('Clôturée');
    expect(badge.status).toBe('ok');
  });

  it('evidence_required + no evidence → "Bloqué" crit', () => {
    const badge = computeCloseabilityBadge(
      mockFEAction({ _backend: { evidence_required: true, evidence_count: 0 } })
    );
    expect(badge.label).toContain('Bloqué');
    expect(badge.status).toBe('crit');
  });

  it('evidence_required + has evidence → "Preuve requise ✓" ok', () => {
    const badge = computeCloseabilityBadge(
      mockFEAction({
        due_date: new Date(Date.now() + 86400000).toISOString().slice(0, 10),
        _backend: { evidence_required: true, evidence_count: 2 },
      })
    );
    expect(badge.label).toContain('✓');
    expect(badge.status).toBe('ok');
  });

  it('overdue → "En retard" warn', () => {
    const badge = computeCloseabilityBadge(
      mockFEAction({
        due_date: '2020-01-01',
        _backend: { evidence_required: false },
      })
    );
    expect(badge.label).toBe('En retard');
    expect(badge.status).toBe('warn');
  });

  it('normal action → neutral (no badge)', () => {
    const badge = computeCloseabilityBadge(
      mockFEAction({
        due_date: new Date(Date.now() + 86400000).toISOString().slice(0, 10),
        _backend: { evidence_required: false },
      })
    );
    expect(badge.label).toBe('');
    expect(badge.status).toBe('neutral');
  });
});

// ── DOSSIER_SECTION_LABELS ──────────────────────────────────────────────

describe('DOSSIER_SECTION_LABELS', () => {
  it('all labels are in French', () => {
    const englishWords = ['header', 'actions', 'evidence', 'missing', 'summary'];
    for (const label of Object.values(DOSSIER_SECTION_LABELS)) {
      for (const eng of englishWords) {
        expect(label.toLowerCase()).not.toBe(eng);
      }
    }
  });
});

// ── Source tracing (retour à la source) ─────────────────────────────────

describe('Source tracing links', () => {
  it('compliance → /conformite?tab=obligations deep link', () => {
    expect(buildSourceDeepLink('compliance', 'BACS')).toBe('/conformite?tab=obligations');
  });

  it('billing → /bill-intel deep link', () => {
    expect(buildSourceDeepLink('billing', '42')).toBe('/bill-intel');
  });

  it('insight operat → /conformite/tertiaire/efa/{id}', () => {
    expect(buildSourceDeepLink('insight', 'operat:1:2024:dpe')).toBe('/conformite/tertiaire/efa/1');
  });
});

// ── Source guards (Étape 5 integration) ─────────────────────────────────

describe('Source guards — Étape 5 integration', () => {
  it('ActionsPage imports groupActionsByWeek', async () => {
    const fs = await import('fs');
    const src = fs.readFileSync(
      'c:/Users/amine/promeos-poc/promeos-poc/frontend/src/pages/ActionsPage.jsx',
      'utf-8'
    );
    expect(src).toContain('groupActionsByWeek');
    expect(src).toContain('computeCloseabilityBadge');
    expect(src).toContain('WeekView');
    expect(src).toContain("'week'");
  });

  it('ConformitePage has DossierPrintView (V92: tab wiring via setDossierSource)', async () => {
    const fs = await import('fs');
    const src = fs.readFileSync(
      'c:/Users/amine/promeos-poc/promeos-poc/frontend/src/pages/ConformitePage.jsx',
      'utf-8'
    );
    expect(src).toContain('DossierPrintView');
    expect(src).toContain('dossierSource');
    expect(src).toContain('setDossierSource');
    // onExportDossier now lives in ObligationsTab (V92 split)
    const tabSrc = fs.readFileSync(
      'c:/Users/amine/promeos-poc/promeos-poc/frontend/src/pages/conformite-tabs/ObligationsTab.jsx',
      'utf-8'
    );
    expect(tabSrc).toContain('onExportDossier');
  });

  it('BillIntelPage has DossierPrintView', async () => {
    const fs = await import('fs');
    const src = fs.readFileSync(
      'c:/Users/amine/promeos-poc/promeos-poc/frontend/src/pages/BillIntelPage.jsx',
      'utf-8'
    );
    expect(src).toContain('DossierPrintView');
    expect(src).toContain('dossierSource');
    expect(src).toContain("sourceType: 'billing'");
  });

  it('TertiaireEfaDetailPage has DossierPrintView', async () => {
    const fs = await import('fs');
    const src = fs.readFileSync(
      'c:/Users/amine/promeos-poc/promeos-poc/frontend/src/pages/tertiaire/TertiaireEfaDetailPage.jsx',
      'utf-8'
    );
    expect(src).toContain('DossierPrintView');
    expect(src).toContain('showDossier');
    expect(src).toContain('btn-dossier-efa');
  });
});

// ── FR-only invariant ───────────────────────────────────────────────────

describe('FR-only invariant — dossier labels', () => {
  it('STATUS_LABELS_FR has no English', () => {
    for (const label of Object.values(STATUS_LABELS_FR)) {
      expect(label).not.toMatch(/open|closed|blocked|done|progress/i);
    }
  });

  it('PRIORITY_LABELS_FR has no English', () => {
    for (const label of Object.values(PRIORITY_LABELS_FR)) {
      expect(label).not.toMatch(/critical|high|medium|low/i);
    }
  });
});
