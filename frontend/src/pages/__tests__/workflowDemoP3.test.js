/**
 * PROMEOS Sprint P3 — Workflow Continuity + Executive Demo Flow
 * Source-guard tests: verify openActionDrawer integration across all modules,
 * inline owner edit, impact EUR prefill, notification CTA.
 */
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { resolve } from 'path';

function src(rel) {
  return readFileSync(resolve(__dirname, '..', '..', rel), 'utf-8');
}

// ── P3-1 / P3-7: PurchasePage — unified drawer pattern ──────────────────────

describe('P3-1: PurchasePage uses openActionDrawer', () => {
  const code = src('pages/PurchasePage.jsx');

  it('importe useActionDrawer', () => {
    expect(code).toContain('useActionDrawer');
  });

  it('appelle openActionDrawer (pas navigate pour creation)', () => {
    expect(code).toContain('openActionDrawer({');
  });

  it('passe sourceType purchase', () => {
    expect(code).toContain("sourceType: 'purchase'");
  });

  it('passe idempotencyKey purchase', () => {
    expect(code).toContain("idempotencyKey: `purchase:");
  });

  it('a le CTA creer-action-purchase', () => {
    expect(code).toContain('cta-creer-action-purchase');
  });

  it('conserve le CTA voir-actions-purchase', () => {
    expect(code).toContain('cta-voir-actions-purchase');
  });
});

// ── P3-1 / P3-5: Cockpit — action drawer from risk panel ────────────────────

describe('P3-1: Cockpit uses openActionDrawer', () => {
  const code = src('pages/Cockpit.jsx');

  it('importe useActionDrawer', () => {
    expect(code).toContain('useActionDrawer');
  });

  it('appelle openActionDrawer', () => {
    expect(code).toContain('openActionDrawer(');
  });

  it('a le CTA cockpit-create-action', () => {
    expect(code).toContain('cta-cockpit-create-action');
  });

  it('conserve Plan d action navigation', () => {
    expect(code).toContain("Plan d'action");
  });

  it('importe Plus icon', () => {
    expect(code).toContain('Plus');
  });
});

// ── P3-1 / P3-6: NotificationsPage — action CTA in drawer ───────────────────

describe('P3-1: NotificationsPage has Creer action CTA', () => {
  const code = src('pages/NotificationsPage.jsx');

  it('importe useActionDrawer', () => {
    expect(code).toContain('useActionDrawer');
  });

  it('appelle openActionDrawer dans le drawer', () => {
    expect(code).toContain('openActionDrawer({');
  });

  it('passe le titre de la notification', () => {
    expect(code).toContain('drawerEvent.title');
  });

  it('passe le source_type de la notification', () => {
    expect(code).toContain('drawerEvent.source_type');
  });

  it('passe impact EUR si disponible', () => {
    expect(code).toContain('estimated_impact_eur');
  });

  it('a le CTA notif-create-action', () => {
    expect(code).toContain('cta-notif-create-action');
  });

  it('conserve le bouton Ouvrir deeplink', () => {
    expect(code).toContain('Ouvrir');
  });
});

// ── P3-2: ActionDetailDrawer — inline owner edit ─────────────────────────────

describe('P3-2: ActionDetailDrawer has inline owner edit', () => {
  const code = src('components/ActionDetailDrawer.jsx');

  it('a le state editingOwner', () => {
    expect(code).toContain('editingOwner');
    expect(code).toContain('setEditingOwner');
  });

  it('a le state ownerDraft', () => {
    expect(code).toContain('ownerDraft');
    expect(code).toContain('setOwnerDraft');
  });

  it('a le data-testid owner-field', () => {
    expect(code).toContain('owner-field');
  });

  it('a le data-testid owner-input', () => {
    expect(code).toContain('owner-input');
  });

  it('appelle patchAction pour sauver le owner', () => {
    expect(code).toContain("patchAction(actionId, { owner: ownerDraft.trim() })");
  });

  it('affiche le Pencil icon pour edition', () => {
    expect(code).toContain('Pencil');
  });

  it('supporte Enter pour valider', () => {
    expect(code).toContain("e.key === 'Enter'");
  });

  it('supporte Escape pour annuler', () => {
    expect(code).toContain("e.key === 'Escape'");
  });
});

// ── P3-5: ConformitePage — impact EUR in finding CTA ─────────────────────────

describe('P3-5: ConformitePage passes impact EUR to drawer', () => {
  const code = src('pages/ConformitePage.jsx');

  it('handleCreateFromObligation passe impact_eur', () => {
    expect(code).toContain('impact_eur: obligation.impact_eur');
  });

  it('handleCreateFromFinding passe impact_eur', () => {
    expect(code).toContain('impact_eur: finding.penalty_exposure || finding.impact_eur');
  });

  it('handleCreateFromFinding passe siteId', () => {
    expect(code).toContain('siteId: finding.site_id');
  });
});

// ── P3-7: All modules use openActionDrawer (unified pattern) ─────────────────

describe('P3-7: Unified openActionDrawer across all key modules', () => {
  const modules = [
    { name: 'PurchasePage', path: 'pages/PurchasePage.jsx' },
    { name: 'Cockpit', path: 'pages/Cockpit.jsx' },
    { name: 'NotificationsPage', path: 'pages/NotificationsPage.jsx' },
    { name: 'ConformitePage', path: 'pages/ConformitePage.jsx' },
    { name: 'AnomaliesPage', path: 'pages/AnomaliesPage.jsx' },
    { name: 'BillIntelPage', path: 'pages/BillIntelPage.jsx' },
    { name: 'MonitoringPage', path: 'pages/MonitoringPage.jsx' },
  ];

  for (const mod of modules) {
    it(`${mod.name} utilise useActionDrawer`, () => {
      const code = src(mod.path);
      expect(code).toContain('useActionDrawer');
    });
  }
});
