/**
 * PROMEOS — Source guards FE Billing (Vague 4 EPIC #274).
 *
 * Surveille BillingPage.jsx et BillIntelPage.jsx.
 * Doctrine §8.1 : zéro calcul TURPE/accise/CTA inline FE.
 *
 * SG_BILLING_FE_01 — pas de calcul TURPE/accise/CTA inline
 * SG_BILLING_FE_02 — fetch via services/api/billing.js uniquement (whitelist)
 * SG_BILLING_FE_03 — pas de constantes tarifs hardcodées (0.02658, 0.068, etc.)
 *
 * Pattern repo : readFileSync + regex (env=node).
 */

import { describe, it, expect } from 'vitest';
import { readFileSync, existsSync } from 'fs';
import { dirname, join } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const SRC_ROOT = join(__dirname, '..', '..');

const BILLING_PAGES = [
  join(SRC_ROOT, 'pages', 'BillingPage.jsx'),
  join(SRC_ROOT, 'pages', 'BillIntelPage.jsx'),
].filter(existsSync);

// Service billing canonique (seul point d'entrée autorisé)
const BILLING_API_SERVICE = join(SRC_ROOT, 'services', 'api', 'billing.js');

function stripComments(src) {
  return src.replace(/\/\*[\s\S]*?\*\//g, '').replace(/\/\/.*$/gm, '');
}

// ── SG_BILLING_FE_01 — pas de calcul TURPE/accise/CTA inline ─────────────

describe('SG_BILLING_FE_01 — pas de calcul TURPE/accise/CTA inline FE', () => {
  it('aucune page billing ne calcule TURPE avec des coefficients inline', () => {
    const violations = [];
    // Patterns de calcul TURPE inline (ex: * 0.0569, * 0.0492…)
    const TURPE_INLINE = /\*\s*0\.0[3-9]\d{2,}/;
    for (const file of BILLING_PAGES) {
      const cleaned = stripComments(readFileSync(file, 'utf-8'));
      if (TURPE_INLINE.test(cleaned)) {
        violations.push(file);
      }
    }
    expect(violations).toEqual([]);
  });

  it('aucune page billing ne calcule la CTA par multiplication inline', () => {
    const violations = [];
    // CTA = 15% ou 21.93% → multiplicateur 0.15 ou 0.2193 dans un calcul direct
    const CTA_INLINE = /\*\s*(0\.15\b|0\.2193\b|15\s*\/\s*100|21\.93\s*\/\s*100)/;
    for (const file of BILLING_PAGES) {
      const cleaned = stripComments(readFileSync(file, 'utf-8'));
      if (CTA_INLINE.test(cleaned)) {
        violations.push(file);
      }
    }
    expect(violations).toEqual([]);
  });
});

// ── SG_BILLING_FE_02 — fetch via billing.js whitelist ─────────────────────

describe('SG_BILLING_FE_02 — appels API billing via services/api/billing.js uniquement', () => {
  it('le service billing API est importable', () => {
    expect(existsSync(BILLING_API_SERVICE)).toBe(true);
  });

  it('aucune page billing ne fait de fetch() natif vers /billing', () => {
    const violations = [];
    for (const file of BILLING_PAGES) {
      const cleaned = stripComments(readFileSync(file, 'utf-8'));
      if (/\bfetch\s*\(\s*['"].*billing/.test(cleaned)) {
        violations.push(file);
      }
    }
    expect(violations).toEqual([]);
  });
});

// ── SG_BILLING_FE_03 — pas de constantes tarifs hardcodées ────────────────

describe('SG_BILLING_FE_03 — pas de constantes tarifs hardcodées dans les pages billing', () => {
  const FORBIDDEN_TARIFS = [
    { value: '0.02658', label: 'accise legacy hardcodée' },
    { value: '0.068', label: 'PRICE_FALLBACK hardcodé' },
    { value: '0.052', label: 'CO₂ élec hardcodé' },
    { value: '0.227', label: 'CO₂ gaz hardcodé' },
  ];

  for (const { value, label } of FORBIDDEN_TARIFS) {
    it(`pas de ${label} (${value}) dans pages billing`, () => {
      const violations = [];
      const pattern = new RegExp(`\\b${value.replace('.', '\\.')}\\b`);
      for (const file of BILLING_PAGES) {
        const cleaned = stripComments(readFileSync(file, 'utf-8'));
        if (pattern.test(cleaned)) {
          violations.push(file);
        }
      }
      expect(violations).toEqual([]);
    });
  }
});
