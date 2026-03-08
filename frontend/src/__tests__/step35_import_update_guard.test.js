/**
 * PROMEOS — Step 35 source-guard : Import incremental (mode update)
 */
import { describe, it, expect } from 'vitest';
import { readFileSync, existsSync } from 'fs';
import { join } from 'path';

const src = join(__dirname, '..');
const apiPath = join(src, 'services', 'api.js');
const glossaryPath = join(src, 'ui', 'glossary.js');

function read(p) {
  return existsSync(p) ? readFileSync(p, 'utf-8') : null;
}

describe('Step 35 — API functions', () => {
  const src = read(apiPath);

  it('has getStagingMatching function', () => {
    expect(src).toMatch(/getStagingMatching/);
  });

  it('calls /staging/.../matching endpoint', () => {
    expect(src).toMatch(/staging\/.*\/matching/);
  });
});

describe('Step 35 — Glossary', () => {
  const src = read(glossaryPath);

  it('has import_incremental entry', () => {
    expect(src).toMatch(/import_incremental/);
  });

  it('mentions SIRET matching', () => {
    expect(src).toMatch(/SIRET/);
  });

  it('mentions PRM matching', () => {
    expect(src).toMatch(/PRM/);
  });
});
