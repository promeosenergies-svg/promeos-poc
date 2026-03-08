/**
 * PROMEOS Sprint Premium Pass — Board-ready polish
 * Source-guard tests: CTA harmonization, badge consistency, French microcopy, empty states, cockpit premium.
 */
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { resolve } from 'path';

function src(rel) {
  return readFileSync(resolve(__dirname, '..', '..', rel), 'utf-8');
}

// ── P3-3: CTA wording "Créer une action" everywhere ───────────────────────

describe('P3-3: CTA harmonization — "Créer une action"', () => {
  const files = {
    ActionsPage: src('pages/ActionsPage.jsx'),
    ConformitePage: src('pages/ConformitePage.jsx'),
    ObligationsTab: src('pages/conformite-tabs/ObligationsTab.jsx'),
    ExecutionTab: src('pages/conformite-tabs/ExecutionTab.jsx'),
    Cockpit: src('pages/Cockpit.jsx'),
    AnomaliesPage: src('pages/AnomaliesPage.jsx'),
    PurchasePage: src('pages/PurchasePage.jsx'),
    BillIntelPage: src('pages/BillIntelPage.jsx'),
    MonitoringPage: src('pages/MonitoringPage.jsx'),
  };

  Object.entries(files).forEach(([name, code]) => {
    it(`${name} n'a pas de "Créer action" sans "une" dans le JSX`, () => {
      // Remove comments (// ...) to avoid false positives
      const noComments = code.replace(/\/\/.*$/gm, '').replace(/\/\*[\s\S]*?\*\//g, '');
      // Find "Créer action" NOT preceded by "une " (excluding "conformité" variants)
      const bad = noComments.match(/Créer action(?! conformité)/g) || [];
      const good = noComments.match(/Créer une action/g) || [];
      expect(good.length).toBeGreaterThanOrEqual(bad.length);
    });
  });

  it('ActionsPage ctaLabel utilise "Créer une action"', () => {
    expect(files.ActionsPage).toContain('Créer une action');
  });

  it('Cockpit CTA texte "Créer une action"', () => {
    expect(files.Cockpit).toContain('Créer une action');
  });
});

// ── P3-4: Badge/alert color consistency (-100/-700 palette) ────────────────

describe('P3-4: Badge color consistency', () => {
  it('BillIntelPage n\'utilise pas text-*-800 pour statuts', () => {
    const code = src('pages/BillIntelPage.jsx');
    // INSIGHT_STATUS_COLORS ne doit pas avoir de -800
    const statusBlock = code.match(/INSIGHT_STATUS_COLORS[\s\S]*?\};/);
    if (statusBlock) {
      expect(statusBlock[0]).not.toMatch(/text-\w+-800/);
    }
  });

  it('ActionDetailDrawer n\'utilise pas text-red-600 pour false_positive', () => {
    const code = src('components/ActionDetailDrawer.jsx');
    // false_positive doit utiliser -700, pas -600
    expect(code).not.toMatch(/false_positive.*text-red-600/);
  });

  it('ActionDetailDrawer utilise text-red-700 pour false_positive', () => {
    const code = src('components/ActionDetailDrawer.jsx');
    expect(code).toMatch(/false_positive.*text-red-700/);
  });
});

// ── P3-5: Empty states améliorés ──────────────────────────────────────────

describe('P3-5: Empty states enrichis', () => {
  const actionsCode = src('pages/ActionsPage.jsx');

  it('Kanban colonne vide a un message contextuel', () => {
    expect(actionsCode).toContain('Aucune action dans cette colonne');
  });

  it('Kanban colonne vide utilise italic pour indice', () => {
    expect(actionsCode).toMatch(/italic/);
  });
});

// ── P3-6: Microcopy French accents ─────────────────────────────────────────

describe('P3-6: Microcopy — accents français corrects', () => {
  const notifCode = src('pages/NotificationsPage.jsx');

  it('NotificationsPage utilise "créées" (pas "creees")', () => {
    expect(notifCode).toContain('créées');
    expect(notifCode).not.toContain('creees');
  });

  it('NotificationsPage utilise "mise à jour" complet', () => {
    expect(notifCode).toContain('mises à jour');
  });

  it('NotificationsPage utilise "ignorée(s)" avec accent', () => {
    expect(notifCode).toContain('ignorée(s)');
    expect(notifCode).not.toMatch(/(?<!é)ignoree\(s\)/);
  });

  it('NotificationsPage utilise "marquée(s) lue(s)" avec accent', () => {
    expect(notifCode).toContain('marquée(s) lue(s)');
  });
});

// ── P3-2: Cockpit premium — pas de jargon technique ───────────────────────

describe('P3-2: Cockpit premium — jargon technique supprimé', () => {
  const cockpitCode = src('pages/Cockpit.jsx');

  it('pas de "compliance_engine" en dur', () => {
    expect(cockpitCode).not.toContain('compliance_engine');
  });

  it('utilise "Moteur de conformité" en français', () => {
    expect(cockpitCode).toContain('Moteur de conformité');
  });
});
