/**
 * conformiteS2SimpliciteMetier.test.js — Source-guards Sprint S2 simplicité métier.
 *
 * Verrouille les promesses cardinales du sprint S2 (2026-05-28) :
 *   A. Tabs dynamiques par persona (3 normal / 4 expert)
 *   B. NextBestAction 1-clic via upsert idempotent par external_ref
 *   C. ModulationDrawer rend tri_par_typologie + sources Légifrance
 *   D. Banner unifié 3 états sans doublon (top3 / executive / RiskBadge)
 *
 * 100% lecture source + regex — pas de DOM mock requis. Source-guards :
 * si une refonte ultérieure touche ces invariants, le test casse en CI
 * et oblige à mettre à jour la doctrine S2 explicitement.
 */
import { readFileSync } from 'fs';
import { resolve } from 'path';
import { describe, it, expect } from 'vitest';

const root = resolve(__dirname, '../../../');
const readSrc = (...parts) => readFileSync(resolve(root, 'src', ...parts), 'utf-8');

// ── A. Tabs dynamiques ──────────────────────────────────────────────────

describe('S2 · A — Tabs dynamiques par persona', () => {
  const labels = readSrc('domain', 'compliance', 'complianceLabels.fr.js');
  const page = readSrc('pages', 'ConformitePage.jsx');

  it('expose COCKPIT_TABS_NORMAL avec 3 tabs (obligations/donnees/preuves)', () => {
    expect(labels).toMatch(/export const COCKPIT_TABS_NORMAL\s*=/);
    expect(labels).toMatch(/COCKPIT_TABS_NORMAL[\s\S]*?obligations[\s\S]*?donnees[\s\S]*?preuves/);
  });

  it('expose COCKPIT_TABS_EXPERT avec le 4ᵉ tab execution', () => {
    expect(labels).toMatch(/export const COCKPIT_TABS_EXPERT\s*=/);
    expect(labels).toMatch(/COCKPIT_TABS_EXPERT[\s\S]*?execution/);
  });

  it('ConformitePage bascule la liste de tabs selon isExpert', () => {
    expect(page).toContain('isExpert ? COCKPIT_TABS_EXPERT : COCKPIT_TABS_NORMAL');
  });

  it('un deep-link tab=execution en mode normal redirige vers /action-center-v4', () => {
    expect(page).toContain("navigate('/action-center-v4?domain=conformite')");
  });
});

// ── B. NextBestAction 1-clic idempotent ─────────────────────────────────

describe('S2 · B — NextBestAction 1-clic + idempotence', () => {
  const v4Api = readSrc('services', 'api', 'v4ActionCenter.js');
  const card = readSrc('pages', 'conformite-tabs', 'NextBestActionCard.jsx');
  const page = readSrc('pages', 'ConformitePage.jsx');

  it('client API expose upsertItemByExternalRef', () => {
    expect(v4Api).toContain('export function upsertItemByExternalRef');
    expect(v4Api).toContain('/items/upsert-by-external-ref');
  });

  it('NextBestActionCard accepte actionablePayload + onCreateAction + pending', () => {
    expect(card).toContain('actionablePayload');
    expect(card).toContain('onCreateAction');
    expect(card).toContain('pending');
  });

  it('NextBestActionCard rend un CTA unique « Créer l’action » quand actionable', () => {
    expect(card).toMatch(/Cr.er l['’]action/);
    expect(card).toContain('data-testid="nba-cta-create-action"');
  });

  it('ConformitePage construit un external_ref stable conformite:{rule}:{site}', () => {
    expect(page).toMatch(/external_ref:\s*`conformite:/);
  });

  it('ConformitePage source_url canonique /conformite?regulation=…', () => {
    expect(page).toMatch(/source_url:\s*`\/conformite\?regulation=/);
  });

  it('ConformitePage gère le 409 EXTERNAL_REF_CLOSED (pas de résurrection)', () => {
    expect(page).toContain('EXTERNAL_REF_CLOSED');
  });
});

// ── C. ModulationDrawer TRI par typologie ───────────────────────────────

describe('S2 · C — ModulationDrawer TRI par typologie + sources', () => {
  const drawer = readSrc('components', 'conformite', 'ModulationDrawer.jsx');

  it('expose un select typologie sur chaque action', () => {
    expect(drawer).toContain('data-testid="modulation-action-typologie"');
  });

  it('rend la décomposition par typologie en table dédiée', () => {
    expect(drawer).toContain('data-testid="modulation-tri-par-typologie"');
  });

  it('rend les 3 typologies OPERAT canoniques (Article 11.I)', () => {
    expect(drawer).toContain('STRUCTURAL_ENVELOPE');
    expect(drawer).toContain('ENERGY_EQUIPMENT');
    expect(drawer).toContain('OPTIMIZATION_SYSTEM');
  });

  it('utilise le vocabulaire FR doctrine §6 conformité', () => {
    expect(drawer).toContain('Enveloppe du bâtiment');
    expect(drawer).toContain('Équipements');
    expect(drawer).toContain('Optimisation et exploitation');
    expect(drawer).toContain('systèmes locaux et personnalisés');
  });

  it('rend la durée réglementaire + TRI + décision disproportion par ligne', () => {
    expect(drawer).toContain('seuil_disproportion_ans');
    expect(drawer).toContain('is_disproportionate');
  });

  it('rend la source Légifrance cliquable', () => {
    expect(drawer).toContain('source_url');
    expect(drawer).toMatch(/L.gifrance/);
  });

  it('rend formule + période + confiance (contrat « source/formule/unité/période/confiance »)', () => {
    expect(drawer).toMatch(/Formule/);
    expect(drawer).toMatch(/P.riode/);
    expect(drawer).toMatch(/Confiance/);
  });
});

// ── D. ComplianceSummaryBanner anti-doublon ─────────────────────────────

describe('S2 · D — Banner unifié 3 états, anti-doublon', () => {
  const banner = readSrc('components', 'conformite', 'ComplianceSummaryBanner.jsx');

  it('banner ne re-rend ni RiskBadge, ni top3, ni executive-summary', () => {
    // On cible l'IMPORT et l'USAGE JSX, pas la mention dans le docstring
    // (le header explique justement pourquoi ces blocs ont été retirés).
    expect(banner).not.toMatch(/import\s+\{[^}]*RiskBadge[^}]*\}/);
    expect(banner).not.toMatch(/<RiskBadge\b/);
    expect(banner).not.toContain('top3-urgences');
    expect(banner).not.toContain('executive-summary');
  });

  it('un seul CTA primaire par état (green = null, amber + red = défini)', () => {
    expect(banner).toMatch(/green:[\s\S]*?cta:\s*null/);
    expect(banner).toMatch(/amber:[\s\S]*?cta:\s*\{/);
    expect(banner).toMatch(/red:[\s\S]*?cta:\s*\{/);
  });
});
