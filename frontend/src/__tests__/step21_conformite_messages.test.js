/**
 * Step 21 — C6 : Messages actionnables ConformitePage
 * Source-guard tests (vitest).
 *
 * V101 : extraction de ComplianceSummaryBanner vers components/conformite/.
 * S2 (2026-05-28) — simplicité métier : le banner est désormais unifié 3
 * états (vert/orange/rouge) avec UN seul CTA primaire par état. Le top 3
 * urgences, le résumé exécutif et le RiskBadge ont été retirés (déjà
 * rendus par ConformiteSyntheseCompacte + ObligationsTab — anti-doublon
 * §6.2). Les assertions ci-dessous reflètent CE nouveau contrat.
 */
import { describe, it, expect } from 'vitest';
import fs from 'fs';

const readSrc = (...parts) => fs.readFileSync(`src/${parts.join('/')}`, 'utf8');

// ── A. ComplianceSummaryBanner — structure 3 états ───────────────────────

describe('Step 21 — ComplianceSummaryBanner (S2 simplifié)', () => {
  const pageSrc = readSrc('pages', 'ConformitePage.jsx');
  const bannerSrc = readSrc('components', 'conformite', 'ComplianceSummaryBanner.jsx');

  it('ConformitePage embarque le banner', () => {
    expect(pageSrc).toContain('ComplianceSummaryBanner');
  });

  it('banner expose 3 états (green / amber / red)', () => {
    expect(bannerSrc).toContain('green:');
    expect(bannerSrc).toContain('amber:');
    expect(bannerSrc).toContain('red:');
  });

  it('banner expose data-testid stable', () => {
    expect(bannerSrc).toContain('compliance-summary-banner');
  });

  it('banner expose data-state pour assertions Playwright', () => {
    expect(bannerSrc).toContain('data-state={state}');
  });
});

// ── B. Anti-doublon (S2 : éléments retirés) ─────────────────────────────

describe('Step 21 — Anti-doublon S2', () => {
  const bannerSrc = readSrc('components', 'conformite', 'ComplianceSummaryBanner.jsx');

  it('banner n’importe plus getKpiMessage (logique déplacée vers la synthèse)', () => {
    expect(bannerSrc).not.toContain('getKpiMessage');
  });

  it('banner n’importe plus RiskBadge (déjà carte 4 de la synthèse)', () => {
    expect(bannerSrc).not.toContain('RiskBadge');
  });

  it('banner ne rend plus le bloc « Top urgences » (déjà dans ObligationsTab)', () => {
    expect(bannerSrc).not.toContain('top3-urgences');
  });

  it('banner ne rend plus de « executive summary » (déjà dans la synthèse)', () => {
    expect(bannerSrc).not.toContain('executive-summary');
  });
});

// ── C. CTA unique par état ──────────────────────────────────────────────

describe('Step 21 — CTA primaire par état', () => {
  const bannerSrc = readSrc('components', 'conformite', 'ComplianceSummaryBanner.jsx');

  it('état rouge → CTA « Voir le plan d’action »', () => {
    expect(bannerSrc).toContain('Voir le plan d');
  });

  it('état rouge → redirige vers le hub Centre d’Action V4 filtré conformité', () => {
    expect(bannerSrc).toContain('/action-center-v4?domain=conformite');
  });

  it('état orange → CTA « Préparer les échéances »', () => {
    expect(bannerSrc).toMatch(/Pr.parer les .ch.ances/);
  });

  it('état vert → pas de CTA primaire (suivi à jour)', () => {
    // L’objet vert a `cta: null` — vérifié par grep dur.
    expect(bannerSrc).toMatch(/green:[\s\S]*?cta:\s*null/);
  });
});

// ── D. Prochaine échéance ────────────────────────────────────────────────

describe('Step 21 — Prochaine échéance', () => {
  const bannerSrc = readSrc('components', 'conformite', 'ComplianceSummaryBanner.jsx');

  it('banner lit next_deadline depuis timeline (SoT backend)', () => {
    expect(bannerSrc).toContain('next_deadline');
  });

  it('banner expose data-testid next-deadline', () => {
    expect(bannerSrc).toContain('next-deadline');
  });

  it('banner affiche days_remaining (signal urgence)', () => {
    expect(bannerSrc).toContain('days_remaining');
  });
});

// ── E. kpiMessaging reste exporté (consommé ailleurs) ───────────────────

describe('Step 21 — kpiMessaging.js intact', () => {
  const src = readSrc('services', 'kpiMessaging.js');

  it('kpiMessaging garde le handler conformite', () => {
    expect(src).toContain('conformite:');
  });

  it('kpiMessaging garde le handler risque', () => {
    expect(src).toContain('risque:');
  });

  it('kpiMessaging exporte getKpiMessage', () => {
    expect(src).toContain('export function getKpiMessage');
  });
});
