/**
 * PROMEOS — Source Guards
 * Empêche toute régression sur les constantes réglementaires canoniques.
 * Chaque valeur est vérifiée contre sa source officielle.
 */
import { describe, it, expect } from 'vitest';
import { readFileSync, readdirSync, statSync } from 'fs';
import { resolve, join } from 'path';

const glossaryPath = resolve(__dirname, '../ui/glossary.js');
const glossary = readFileSync(glossaryPath, 'utf-8');

const emissionPath = resolve(__dirname, '../../../backend/config/emission_factors.py');
const emissionSrc = readFileSync(emissionPath, 'utf-8');

// ── CO₂ : ADEME Base Empreinte V23.6 ────────────────────────────────────────

describe('Source guards — CO₂ (ADEME Base Empreinte V23.6)', () => {
  it('glossary uses 0.052 kgCO₂/kWh for electricity (not 0.057 or 0.0569)', () => {
    expect(glossary).toMatch(/0[.,]052/);
    expect(glossary).not.toMatch(/0[.,]057\s*kgCO/);
    expect(glossary).not.toMatch(/0[.,]0569\s*kgCO/);
  });

  it('glossary uses 0.227 kgCO₂/kWh for gas', () => {
    expect(glossary).toMatch(/0[.,]227/);
  });

  it('backend emission_factors.py uses 0.052 for ELEC', () => {
    expect(emissionSrc).toContain('0.052');
  });

  it('backend emission_factors.py uses 0.227 for GAZ', () => {
    expect(emissionSrc).toContain('0.227');
  });
});

// ── Accise / CSPE : LFI 2026, Code des impositions ──────────────────────────

describe('Source guards — Accise électricité', () => {
  it('glossary mentions taux 2026 (26.58), not 22.50', () => {
    expect(glossary).toMatch(/26[.,]58/);
    expect(glossary).not.toMatch(/22[.,]50/);
  });
});

// ── TURPE : CRE n°2025-78 ───────────────────────────────────────────────────

describe('Source guards — TURPE', () => {
  it('glossary mentions TURPE 7 (since Aug 2025)', () => {
    expect(glossary).toMatch(/TURPE 7/i);
  });
});

// ── ARENH : terminé 31/12/2025 ──────────────────────────────────────────────

describe('Source guards — ARENH', () => {
  it('glossary mentions ARENH termination', () => {
    expect(glossary).toMatch(/termin|fin|supprim/i);
  });
});

// ── Prix fallback 0.18 : ne doit plus exister en production ─────────────────

describe('Source guards — no 0.18 EUR/kWh fallback in production code', () => {
  it('no 0.18 price constant in frontend src (excluding tests)', () => {
    const srcDir = resolve(__dirname, '..');
    const violations = [];

    function scanDir(dir) {
      let entries;
      try {
        entries = readdirSync(dir, { withFileTypes: true });
      } catch {
        return;
      }
      for (const entry of entries) {
        if (entry.name === 'node_modules' || entry.name === '__tests__' || entry.name === 'mocks')
          continue;
        const fullPath = join(dir, entry.name);
        if (entry.isDirectory()) {
          scanDir(fullPath);
          continue;
        }
        if (!entry.name.endsWith('.js') && !entry.name.endsWith('.jsx')) continue;
        const content = readFileSync(fullPath, 'utf-8');
        if (/(?:=\s*0\.18\b|price\s*=\s*0\.18|EUR_FACTOR\s*=\s*0\.18)/.test(content)) {
          violations.push(fullPath);
        }
      }
    }

    scanDir(srcDir);
    expect(violations).toEqual([]);
  });
});
