/**
 * PROMEOS — Step 4: CO2 Emission Factors Source Guards
 * Vérifie que le glossaire contient emissions_co2 et que
 * les facteurs sont centralisés côté backend.
 */
import { describe, it, expect } from 'vitest';
import { readFileSync, existsSync } from 'fs';
import { join, dirname, resolve } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const backendRoot = resolve(__dirname, '..', '..', '..', 'backend');

function readSrc(relPath) {
  return readFileSync(join(__dirname, '..', relPath), 'utf-8');
}

// ── A. Glossary has emissions_co2 entry ─────────────────────────────────────

describe('Step4 — Glossary CO2 entry', () => {
  const src = readSrc('ui/glossary.js');

  it('has emissions_co2 key', () => {
    expect(src).toContain('emissions_co2');
  });

  it('mentions ADEME in the definition', () => {
    expect(src).toMatch(/ADEME/i);
  });

  it('mentions both electricity and gas factors', () => {
    // 0.052 kgCO₂/kWh = ADEME Base Empreinte V23.6 (élec France mix ACV)
    expect(src).toMatch(/0[,.]052/);
    expect(src).toMatch(/0[,.]227/);
  });
});

// ── B. Backend config file exists ───────────────────────────────────────────

describe('Step4 — Backend emission_factors.py config', () => {
  const configPath = join(backendRoot, 'config', 'emission_factors.py');

  it('config/emission_factors.py exists', () => {
    expect(existsSync(configPath)).toBe(true);
  });

  it('contains ELEC and GAZ factors', () => {
    const src = readFileSync(configPath, 'utf-8');
    expect(src).toContain('ELEC');
    expect(src).toContain('GAZ');
    expect(src).toContain('0.052');
    expect(src).toContain('0.227');
  });

  it('exports get_emission_factor function', () => {
    const src = readFileSync(configPath, 'utf-8');
    expect(src).toContain('def get_emission_factor');
  });

  it('exports get_emission_source function', () => {
    const src = readFileSync(configPath, 'utf-8');
    expect(src).toContain('def get_emission_source');
  });
});

// ── C. No hardcoded 0.052 in key backend services ──────────────────────────

describe('Step4 — No hardcoded 0.052 in backend', () => {
  it('routes/portfolio.py does not hardcode 0.052', () => {
    const src = readFileSync(join(backendRoot, 'routes', 'portfolio.py'), 'utf-8');
    const codeLines = src.split('\n').filter((l) => !l.trim().startsWith('#'));
    expect(codeLines.join('\n')).not.toContain('0.052');
  });

  it('services/emissions_service.py does not hardcode 0.052', () => {
    const src = readFileSync(join(backendRoot, 'services', 'emissions_service.py'), 'utf-8');
    const codeLines = src.split('\n').filter((l) => !l.trim().startsWith('#'));
    expect(codeLines.join('\n')).not.toContain('0.052');
  });
});
