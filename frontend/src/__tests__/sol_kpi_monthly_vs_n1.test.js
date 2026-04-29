/**
 * Source-guard Phase 2.1bis — SolKpiMonthlyVsN1 (KPI 2 maquette v1.1).
 *
 * Verrouille les contrats du composant Sol qui matérialise le swap KPI 2
 * du triptyque Pilotage : "Surconso 7j" sort du hero, "Conso mois courant
 * vs N-1 DJU-ajustée" prend sa place (alignement maquette v1.1).
 *
 * Source-guards prompt §3.B Phase 2.1bis :
 *   - test_pilotage_triptyque_temporal_scales (composant exposé)
 *   - test_no_surconso_7d_in_kpi_hero (anti-régression — backend FE)
 *   - test_monthly_kpi_tooltip_complete (fenêtre + méthode + r² + date)
 */

import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { resolve } from 'path';

const COMPONENT_PATH = resolve(__dirname, '..', 'ui', 'sol', 'SolKpiMonthlyVsN1.jsx');
const SRC = readFileSync(COMPONENT_PATH, 'utf-8');

// ── Contrat composant ───────────────────────────────────────────────

describe('SolKpiMonthlyVsN1 — contrat Phase 2.1bis', () => {
  it('exporte un composant React par défaut', () => {
    expect(SRC).toMatch(/export default function SolKpiMonthlyVsN1/);
  });

  it('accepte la prop canonique data (objet monthly_vs_n1)', () => {
    expect(SRC).toMatch(/data,/);
    expect(SRC).toMatch(/\.current_month_mwh/);
  });

  it('retourne null si data absent ou current_month_mwh null (anti-empty state §6.1)', () => {
    expect(SRC).toMatch(/data\.current_month_mwh\s*==\s*null/);
    expect(SRC).toMatch(/return null/);
  });

  it('data-testid stables pour Playwright', () => {
    expect(SRC).toMatch(/data-testid=["']sol-kpi-monthly-vs-n1["']/);
    expect(SRC).toMatch(/data-testid=["']sol-kpi-monthly-value["']/);
    expect(SRC).toMatch(/data-testid=["']sol-kpi-monthly-delta["']/);
    expect(SRC).toMatch(/data-testid=["']sol-kpi-monthly-tooltip["']/);
  });
});

// ── Tooltip canonique (Phase 2.1bis source-guard) ──────────────────

describe('test_monthly_kpi_tooltip_complete — tooltip 4 composantes', () => {
  it('tooltip contient mention current_month_label (fenêtre temporelle)', () => {
    expect(SRC).toMatch(/current_month_label/);
    expect(SRC).toMatch(/tooltipParts\.push\(current_month_label/);
  });

  it('tooltip contient mention de la méthode baseline (B DJU-ajustée)', () => {
    expect(SRC).toMatch(/Baseline B DJU-ajustée/);
    expect(SRC).toMatch(/baseline_method\s*===\s*['"]b_dju_adjusted['"]/);
  });

  it('tooltip contient r² (rounded 2 décimales)', () => {
    expect(SRC).toMatch(/r_squared/);
    expect(SRC).toMatch(/r²/);
    expect(SRC).toMatch(/toFixed\(2\)/);
  });

  it('tooltip contient calibration_date', () => {
    expect(SRC).toMatch(/calibration_date/);
    expect(SRC).toMatch(/calibrée/);
  });

  it('tooltip mentionne fenêtre N-1 normalisée', () => {
    expect(SRC).toMatch(/normalisé/);
  });
});

// ── Couleurs delta (palette tokens Sol) ─────────────────────────────

describe('SolKpiMonthlyVsN1 — palette delta', () => {
  it('seuils canoniques 5% (warning) et 15% (danger)', () => {
    expect(SRC).toMatch(/abs\s*<\s*5/);
    expect(SRC).toMatch(/abs\s*<\s*15/);
  });

  it('utilise les tokens Sol pour les 3 sévérités', () => {
    expect(SRC).toMatch(/sol-ink-500/);
    expect(SRC).toMatch(/sol-attention-fg/);
    expect(SRC).toMatch(/sol-refuse-fg/);
  });

  it('severity attribut data-severity exposé', () => {
    expect(SRC).toMatch(/data-severity/);
  });
});

// ── Typographie Sol distinctive ─────────────────────────────────────

describe('SolKpiMonthlyVsN1 — typographie Sol', () => {
  it('valeur principale en Fraunces (display serif)', () => {
    expect(SRC).toMatch(/font-serif/);
    expect(SRC).toMatch(/Fraunces/);
  });

  it('kicker + footer en JetBrains Mono / IBM Plex Mono', () => {
    expect(SRC).toMatch(/font-mono/);
    expect(SRC).toMatch(/JetBrains Mono/);
  });

  it('aucun hex hardcodé hors var() (tokens Sol obligatoires)', () => {
    const codeOnly = SRC.replace(/\/\*[\s\S]*?\*\//g, '').replace(/\/\/.*$/gm, '');
    const hexOutsideVar = codeOnly.match(/(?<!var\([^)]*)#[0-9a-fA-F]{3,6}(?![^()]*\))/g);
    expect(hexOutsideVar, 'Hex hardcodés hors var() détectés — utiliser tokens Sol').toBeNull();
  });
});

// ── Doctrine §8.1 zero business logic frontend ──────────────────────

describe('SolKpiMonthlyVsN1 — doctrine §8.1', () => {
  it('aucun useEffect / useState / fetch / axios (display only)', () => {
    const codeOnly = SRC.replace(/\/\*[\s\S]*?\*\//g, '').replace(/\/\/.*$/gm, '');
    expect(codeOnly).not.toMatch(/useEffect|useState|fetch\(|axios/);
  });

  it('format MWh consomme le helper canonique utils/format.js (dedup /simplify P0)', () => {
    expect(SRC).toMatch(/import\s*\{\s*fmtMwh\s*\}\s*from\s*['"]\.\.\/\.\.\/utils\/format['"]/);
    // Locale fr-FR + U+202F normalisation déjà couvertes par utils/format.js
    expect(SRC).not.toMatch(/^function fmtMwh\(v\) \{/m);
  });
});

// ── Anti-régression KPI Surconso 7j (Phase 2.1bis swap) ─────────────

describe('test_no_surconso_7d_in_kpi_hero — Surconso 7j sortie du hero', () => {
  it("composant SolKpiMonthlyVsN1 ne mentionne pas 'Surconso 7j' (composant dédié)", () => {
    const codeOnly = SRC.replace(/\/\*[\s\S]*?\*\//g, '').replace(/\/\/.*$/gm, '');
    expect(codeOnly).not.toMatch(/Surconso\s*7\s*j/i);
    expect(codeOnly).not.toMatch(/surconso_7d_mwh/);
  });

  it("le label canonique est 'Conso mois courant' (pas 'Surconso')", () => {
    expect(SRC).toMatch(/Conso mois courant/);
  });
});
