/**
 * Guard tests — QW3-5 Accent Sweep
 * Ensures French diacriticals are never regressed across the codebase.
 * Uses source-level string assertions (readFileSync).
 */
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { resolve } from 'path';

const read = (name) => readFileSync(resolve(__dirname, '..', name), 'utf8');

// ── Batch A guards ─────────────────────────────────────────────────────────

describe('Batch A — ConsommationsUsages accents', () => {
  const src = read('ConsommationsUsages.jsx');
  it('données (pas donnees) dans les labels', () => {
    expect(src).not.toMatch(/['"].*donnees.*['"]/);
  });
  it('détecté/détectées avec accents', () => {
    expect(src).not.toMatch(/detectee?s?\b/);
  });
  it('Résultats avec accent', () => {
    expect(src).toContain('Résultats');
  });
});

describe('Batch A — ConsumptionExplorerPage accents', () => {
  const src = read('ConsumptionExplorerPage.jsx');
  it('données (pas donnees)', () => {
    expect(src).not.toMatch(/['"]\s*[^é]*donnees/i);
  });
  it('énergie / énergétique avec accents', () => {
    expect(src).not.toMatch(/energetique/);
    expect(src).not.toMatch(/d'energie['"]/);
  });
});

describe('Batch A — WatchersPage accents', () => {
  const src = read('WatchersPage.jsx');
  it('événements (pas evenements)', () => {
    expect(src).not.toMatch(/evenement/i);
  });
  it('réglementaire avec accent', () => {
    expect(src).not.toMatch(/reglementaire/);
  });
  it('configuré avec accent', () => {
    expect(src).not.toContain('configure"');
    expect(src).not.toContain("configure'");
  });
});

describe('Batch A — Patrimoine accents', () => {
  const src = read('Patrimoine.jsx');
  it('Conformité (pas Conformite) dans labels visibles', () => {
    expect(src).not.toMatch(/>Conformite</);
    expect(src).not.toMatch(/title="Conformite"/);
  });
  it('détectée avec accent', () => {
    expect(src).not.toMatch(/detectee/);
  });
});

describe('Batch A — Site360 accents', () => {
  const src = read('Site360.jsx');
  it('Conformité dans tab label', () => {
    expect(src).not.toMatch(/label:\s*'Conformite'/);
  });
  it('Évaluation réglementaire avec accents', () => {
    expect(src).not.toMatch(/Evaluation reglementaire/);
  });
});

describe('Batch A — ImportPage accents', () => {
  const src = read('ImportPage.jsx');
  it('données démo (pas donnees demo)', () => {
    expect(src).not.toMatch(/donnees demo/);
  });
  it('importées / affectées avec accents', () => {
    expect(src).not.toMatch(/donnees importees/);
    expect(src).not.toMatch(/pas affectees/);
  });
});

describe('Batch A — BillIntelPage accents', () => {
  const src = read('BillIntelPage.jsx');
  it('importée / générez / détectées avec accents', () => {
    expect(src).not.toMatch(/facture importee/);
    expect(src).not.toMatch(/generez des donnees/);
    expect(src).not.toMatch(/Anomalies detectees/);
  });
});

describe('Batch A — SiteDetail accents', () => {
  const src = read('SiteDetail.jsx');
  it('Conformité (pas Conformite) dans tabs et headings', () => {
    expect(src).not.toMatch(/label:\s*'Conformite'/);
    expect(src).not.toMatch(/label:\s*'Donnees'/);
  });
  it('réglementaires avec accent', () => {
    expect(src).not.toMatch(/Obligations reglementaires/);
  });
  it('détectée / identifiée avec accents', () => {
    expect(src).not.toMatch(/facturation detectee/);
    expect(src).not.toMatch(/incoherence a ete identifiee/);
  });
});

// ── Batch B guards ─────────────────────────────────────────────────────────

describe('Batch B — AdminAuditLogPage accents', () => {
  const src = read('AdminAuditLogPage.jsx');
  it('événement (pas evenement)', () => {
    expect(src).not.toMatch(/evenement/);
  });
  it('résultat (pas resultat)', () => {
    expect(src).not.toMatch(/resultat/);
  });
});

describe('Batch B — ConnectorsPage accents', () => {
  const src = read('ConnectorsPage.jsx');
  it('configuré / données avec accents', () => {
    expect(src).not.toMatch(/connecteur configure"/);
    expect(src).not.toMatch(/les donnees depuis/);
  });
});

describe('Batch B — KBExplorerPage accents', () => {
  const src = read('KBExplorerPage.jsx');
  it('Réglementaire dans tab label', () => {
    expect(src).not.toMatch(/label:\s*'Reglementaire'/);
  });
  it('résultat(s) avec accent', () => {
    expect(src).not.toMatch(/Aucun resultat/);
    expect(src).not.toMatch(/\d+ resultats/);
  });
  it('mot-clé / découvrir / règles avec accents', () => {
    expect(src).not.toContain('mot-cle');
    expect(src).not.toContain('decouvrir');
  });
});

describe('Batch B — PurchaseAssistantPage accents', () => {
  const src = read('PurchaseAssistantPage.jsx');
  it('terminée / détectée / résultat(s) avec accents', () => {
    expect(src).not.toMatch(/Analyse terminee/);
    expect(src).not.toMatch(/detectee\(s\)/);
    expect(src).not.toMatch(/Aucun resultat/);
    expect(src).not.toMatch(/>Resultats/);
  });
});

describe('Batch B — PurchasePage accents', () => {
  const src = read('PurchasePage.jsx');
  it('données / résultats avec accents', () => {
    expect(src).not.toMatch(/des donnees du site/);
    expect(src).not.toMatch(/resultats existants/);
  });
});

describe('Batch B — NotificationsPage accents', () => {
  const src = read('NotificationsPage.jsx');
  it('Conformité / Ignoré / Ignorées avec accents', () => {
    expect(src).not.toMatch(/compliance:\s*'Conformite'/);
    expect(src).not.toMatch(/dismissed:\s*'Ignore'/);
    expect(src).not.toMatch(/label:\s*'Ignorees'/);
  });
  it('sélectionnée / détecter / réinitialiser avec accents', () => {
    expect(src).not.toMatch(/selectionnee/);
    expect(src).not.toMatch(/pour detecter/);
    expect(src).not.toMatch(/Reinitialiser/);
  });
});

describe('Batch B — AdminUsersPage accents', () => {
  const src = read('AdminUsersPage.jsx');
  it('Conformité / résultat avec accents', () => {
    expect(src).not.toMatch(/Resp\. Conformite/);
    expect(src).not.toMatch(/Aucun resultat/);
  });
});

describe('Batch B — ConsumptionDiagPage accents', () => {
  const src = read('ConsumptionDiagPage.jsx');
  it('détectés / analysés avec accents', () => {
    expect(src).not.toMatch(/Insights detectes/);
    expect(src).not.toMatch(/Sites analyses'/);
  });
});

// ── Batch C guards ─────────────────────────────────────────────────────────

describe('Batch C — AdminAssignmentsPage accents', () => {
  const src = read('AdminAssignmentsPage.jsx');
  it('Conformité / données avec accents', () => {
    expect(src).not.toMatch(/Resp\. Conformite/);
    expect(src).not.toMatch(/des donnees'/);
  });
});

describe('Batch C — CompliancePage accents', () => {
  const src = read('CompliancePage.jsx');
  it('Conformité réglementaire / Décret avec accents', () => {
    expect(src).not.toMatch(/Conformite reglementaire/);
    expect(src).not.toMatch(/Evaluation multi/);
  });
});

describe('Batch C — Dashboard accents', () => {
  const src = read('Dashboard.jsx');
  it('enregistré / énergétique / conformité avec accents', () => {
    expect(src).not.toMatch(/site enregistre"/);
    expect(src).not.toMatch(/energetique/);
    expect(src).not.toMatch(/conformite reglementaire/);
  });
});

describe('Batch C — Others accents', () => {
  it('StatusPage: Base de données', () => {
    const src = read('StatusPage.jsx');
    expect(src).not.toMatch(/Base de donnees/);
  });
  it('ConsommationsPage: données énergie', () => {
    const src = read('ConsommationsPage.jsx');
    expect(src).not.toMatch(/donnees energie/);
  });
  it('Cockpit2MinPage: estimées / conformité', () => {
    const src = read('Cockpit2MinPage.jsx');
    expect(src).not.toMatch(/estimees liees/);
    expect(src).not.toMatch(/non-conformite reglementaire/);
  });
  it('AdminRolesPage: Conformité / rôles / configuré', () => {
    const src = read('AdminRolesPage.jsx');
    expect(src).not.toMatch(/Resp\. Conformite/);
    expect(src).not.toMatch(/roles systeme sont fixes/);
  });
});
