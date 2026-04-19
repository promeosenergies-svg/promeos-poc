/**
 * Unit tests — conformite-tertiaire/sol_presenters.js
 *
 * Phase 4.1 Lot 6 · ≥ 15 cases couvrant null / 0 / frameworks manquants
 * / Audit SMÉ absent. Pure functions, empty-state propre.
 */
import { describe, it, expect } from 'vitest';
import {
  hasDashboard,
  formatEfaCount,
  formatIssuesOpen,
  formatCriticalIssues,
  formatDeadlineOperat,
  interpretDeadlineOperat,
  buildKickerText,
  buildNarrative,
  buildSubNarrative,
  interpretEfaCount,
  interpretIssues,
  interpretCritical,
  buildEmptyState,
  resolveTooltipExplain,
} from '../sol_presenters';

const DASHBOARD_FULL = {
  total_efa: 10,
  active: 9,
  draft: 0,
  closed: 1,
  open_issues: 4,
  critical_issues: 2,
};
const DASHBOARD_CLEAN = {
  total_efa: 5,
  active: 5,
  draft: 0,
  closed: 0,
  open_issues: 0,
  critical_issues: 0,
};
const DASHBOARD_EMPTY = {
  total_efa: 0,
  active: 0,
  draft: 0,
  closed: 0,
  open_issues: 0,
  critical_issues: 0,
};

describe('hasDashboard', () => {
  it('false sur null/undefined', () => {
    expect(hasDashboard(null)).toBe(false);
    expect(hasDashboard(undefined)).toBe(false);
  });
  it('false sur objet sans total_efa', () => {
    expect(hasDashboard({})).toBe(false);
    expect(hasDashboard({ foo: 'bar' })).toBe(false);
  });
  it('true sur objet avec total_efa', () => {
    expect(hasDashboard(DASHBOARD_FULL)).toBe(true);
    expect(hasDashboard({ total_efa: 0 })).toBe(true);
  });
});

describe('formatEfaCount', () => {
  it('null si dashboard absent', () => {
    const k = formatEfaCount(null);
    expect(k.value).toBe(null);
    expect(k.label).toBe('—');
  });
  it('tone succes si toutes actives', () => {
    const k = formatEfaCount(DASHBOARD_CLEAN);
    expect(k.value).toBe(5);
    expect(k.tone).toBe('succes');
  });
  it('tone attention si active < total', () => {
    const k = formatEfaCount(DASHBOARD_FULL);
    expect(k.value).toBe(9);
    expect(k.total).toBe(10);
    expect(k.tone).toBe('attention');
  });
  it('tone refuse si zéro active', () => {
    const k = formatEfaCount({ total_efa: 3, active: 0, draft: 3, closed: 0, open_issues: 0, critical_issues: 0 });
    expect(k.tone).toBe('refuse');
  });
});

describe('formatIssuesOpen + formatCriticalIssues', () => {
  it('null si dashboard absent', () => {
    expect(formatIssuesOpen(null).value).toBe(null);
    expect(formatCriticalIssues(null).value).toBe(null);
  });
  it('tone succes si zero issues', () => {
    expect(formatIssuesOpen(DASHBOARD_CLEAN).tone).toBe('succes');
    expect(formatCriticalIssues(DASHBOARD_CLEAN).tone).toBe('succes');
  });
  it('tone refuse si critiques > 0', () => {
    expect(formatIssuesOpen(DASHBOARD_FULL).tone).toBe('refuse');
    expect(formatCriticalIssues(DASHBOARD_FULL).tone).toBe('refuse');
    expect(formatCriticalIssues(DASHBOARD_FULL).urgent).toBe(true);
  });
});

describe('buildKickerText', () => {
  it('fallback si dashboard absent', () => {
    expect(buildKickerText(null)).toBe('CONFORMITÉ · DÉCRET TERTIAIRE');
  });
  it('inclut count EFA si disponible', () => {
    const k = buildKickerText(DASHBOARD_FULL);
    expect(k).toContain('10');
    expect(k).toContain('EFA');
  });
  it('singulier vs pluriel', () => {
    const k = buildKickerText({ total_efa: 1, active: 1, draft: 0, closed: 0, open_issues: 0, critical_issues: 0 });
    expect(k).toContain('1');
    expect(k).toContain('ENREGISTRÉE');
    expect(k).not.toContain('ENREGISTRÉES');
  });
});

describe('buildNarrative + buildSubNarrative', () => {
  it('fallback honnête si dashboard null', () => {
    expect(buildNarrative(null)).toMatch(/Aucune donnée|Décret Tertiaire/i);
  });
  it('empty state si 0 EFA', () => {
    expect(buildNarrative(DASHBOARD_EMPTY)).toMatch(/Aucune EFA|première EFA/i);
  });
  it('narrative compact (≤ 120 car, 1 phrase) avec EFA + problèmes + OPERAT', () => {
    const n = buildNarrative(DASHBOARD_FULL);
    expect(n).toContain('9'); // EFA actives count
    expect(n).toMatch(/problème|ouvert/i);
    expect(n).toMatch(/OPERAT/i);
    expect(n.length).toBeLessThanOrEqual(130); // tolérance 10 car pour NBSP
  });
  it('subNarrative version métier sans endpoints (Phase 4 polish)', () => {
    const s = buildSubNarrative(DASHBOARD_FULL);
    expect(s).toMatch(/clôturée|historique|trajectoire 2030/i);
    // Polish P2 : zéro mention endpoints
    expect(s).not.toMatch(/\/api\/|RegOps|endpoint/i);
  });
});

describe('interpret*', () => {
  it('interpretEfaCount adapte au count', () => {
    expect(interpretEfaCount(null)).toMatch(/indisponible/i);
    expect(interpretEfaCount(DASHBOARD_EMPTY)).toMatch(/Aucune|démarrez/i);
    expect(interpretEfaCount(DASHBOARD_CLEAN)).toMatch(/actives|opérationnel/i);
  });
  it('interpretIssues différencie critique vs normal', () => {
    expect(interpretIssues(DASHBOARD_FULL)).toMatch(/critique|urgente/i);
    expect(interpretIssues(DASHBOARD_CLEAN)).toMatch(/Aucun|contrôle/i);
  });
  it('interpretCritical tone reflète urgence', () => {
    expect(interpretCritical(DASHBOARD_FULL)).toMatch(/priorité absolue|critique/i);
    expect(interpretCritical(DASHBOARD_CLEAN)).toMatch(/serein|Aucun/i);
  });
});

describe('resolveTooltipExplain', () => {
  it('route vers le bon interpret par code KPI', () => {
    expect(resolveTooltipExplain('efa_count', DASHBOARD_FULL)).toMatch(/brouillons|clôturée|Suivi/i);
    expect(resolveTooltipExplain('open_issues', DASHBOARD_FULL)).toMatch(/critique|problème/i);
    expect(resolveTooltipExplain('critical_issues', DASHBOARD_FULL)).toMatch(/priorité|critique/i);
    expect(resolveTooltipExplain('deadline_operat', DASHBOARD_FULL, '2026-09-30')).toMatch(/OPERAT|échéance|préparation|confortable/i);
  });
  it('string vide si code inconnu', () => {
    expect(resolveTooltipExplain('unknown_kpi', DASHBOARD_FULL)).toBe('');
  });
});

describe('formatDeadlineOperat (Phase 4 polish · KPI 3 swap)', () => {
  // Helper : date ISO qui correspond à N jours depuis maintenant
  const daysFromNow = (n) => {
    const d = new Date(Date.now() + n * 86_400_000);
    return d.toISOString();
  };

  it('null si dashboard absent', () => {
    const k = formatDeadlineOperat(null);
    expect(k.days).toBe(null);
    expect(k.tone).toBe('calme');
    expect(k.label).toBe('—');
  });

  it('null si deadlineDate undefined/invalide', () => {
    expect(formatDeadlineOperat(DASHBOARD_FULL, null).days).toBe(null);
    expect(formatDeadlineOperat(DASHBOARD_FULL, 'not-a-date').days).toBe(null);
  });

  it('J-365 (> 180 j) → tone calme', () => {
    const k = formatDeadlineOperat(DASHBOARD_FULL, daysFromNow(365));
    expect(k.tone).toBe('calme');
    expect(k.label).toMatch(/^J-36[45]$/);
    expect(k.overdue).toBe(false);
  });

  it('J-164 (entre 60 et 180) → tone attention (amber)', () => {
    const k = formatDeadlineOperat(DASHBOARD_FULL, daysFromNow(164));
    expect(k.tone).toBe('attention');
    expect(k.days).toBeGreaterThanOrEqual(163);
    expect(k.days).toBeLessThanOrEqual(165);
  });

  it('J-30 (< 60 j) → tone refuse (red urgence)', () => {
    const k = formatDeadlineOperat(DASHBOARD_FULL, daysFromNow(30));
    expect(k.tone).toBe('refuse');
    expect(k.overdue).toBe(false);
  });

  it('J-0 ou échue → tone refuse + label "échue"', () => {
    const k = formatDeadlineOperat(DASHBOARD_FULL, daysFromNow(0));
    expect(k.tone).toBe('refuse');
    expect(k.overdue).toBe(true);
    expect(k.label).toMatch(/échue/i);
  });

  it('J-(-5) dépassée → tone refuse + label échue J+5', () => {
    const k = formatDeadlineOperat(DASHBOARD_FULL, daysFromNow(-5));
    expect(k.tone).toBe('refuse');
    expect(k.overdue).toBe(true);
    expect(k.label).toMatch(/J\+5|J\+4|J\+6/);
  });
});

describe('interpretDeadlineOperat adaptive', () => {
  const daysFromNow = (n) => new Date(Date.now() + n * 86_400_000).toISOString();

  it('overdue → régularisation urgente', () => {
    expect(interpretDeadlineOperat(DASHBOARD_FULL, daysFromNow(-10))).toMatch(/dépassée|urgente/i);
  });
  it('< 60 j → imminente', () => {
    expect(interpretDeadlineOperat(DASHBOARD_FULL, daysFromNow(30))).toMatch(/imminente|tarder/i);
  });
  it('< 180 j → fenêtre préparation', () => {
    expect(interpretDeadlineOperat(DASHBOARD_FULL, daysFromNow(120))).toMatch(/préparation|centralisez/i);
  });
  it('≥ 180 j → délai confortable', () => {
    expect(interpretDeadlineOperat(DASHBOARD_FULL, daysFromNow(300))).toMatch(/confortable|consolidation/i);
  });
});

describe('buildEmptyState', () => {
  it('null si dashboard présent', () => {
    expect(buildEmptyState({ dashboard: DASHBOARD_FULL })).toBe(null);
  });
  it('fallback businessError si dashboard absent', () => {
    const es = buildEmptyState({ dashboard: null });
    expect(es).not.toBe(null);
    expect(es.title).toBeTruthy();
    expect(es.message).toBeTruthy();
  });
});
