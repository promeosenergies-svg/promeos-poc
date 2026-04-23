/**
 * SolPanel + SolRail focus rings — Sprint 1 Vague A phase A9
 *
 * Audit fresh §3 : ni SolPanel ni SolRail n'exposaient de focus-visible
 * ring, les utilisateurs clavier ne voyaient pas leur position. Fix :
 * classes Tailwind focus-visible:ring-2 ring-blue-500 sur les 2 boutons.
 */
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));

describe('SolPanel focus rings (A9)', () => {
  const src = readFileSync(join(__dirname, '..', 'SolPanel.jsx'), 'utf-8');

  it('panel items have focus-visible:outline-none', () => {
    expect(src).toMatch(/focus-visible:outline-none/);
  });

  it('panel items have focus-visible:ring-2', () => {
    expect(src).toMatch(/focus-visible:ring-2/);
  });

  it('panel items have focus-visible:ring-blue-500 (keyboard marker)', () => {
    expect(src).toMatch(/focus-visible:ring-blue-500/);
  });

  it('panel items have ring-offset-1', () => {
    expect(src).toMatch(/focus-visible:ring-offset-1/);
  });
});

describe('SolRail focus rings (A9)', () => {
  const src = readFileSync(join(__dirname, '..', 'SolRail.jsx'), 'utf-8');

  it('rail icons have focus-visible:outline-none', () => {
    expect(src).toMatch(/focus-visible:outline-none/);
  });

  it('rail icons have focus-visible:ring-2', () => {
    expect(src).toMatch(/focus-visible:ring-2/);
  });

  it('rail icons have focus-visible:ring-blue-500', () => {
    expect(src).toMatch(/focus-visible:ring-blue-500/);
  });

  it('rail icons have ring-offset-1', () => {
    expect(src).toMatch(/focus-visible:ring-offset-1/);
  });
});
