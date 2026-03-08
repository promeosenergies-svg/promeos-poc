/**
 * PROMEOS — Step 30 source-guard : Seed EFA Tertiaire
 */
import { describe, it, expect } from 'vitest';
import { readFileSync, existsSync } from 'fs';
import { join } from 'path';

const backend = join(__dirname, '..', '..', '..', 'backend');

function readBackend(relPath) {
  const fullPath = join(backend, relPath);
  if (!existsSync(fullPath)) return null;
  return readFileSync(fullPath, 'utf-8');
}

describe('gen_tertiaire_efa.py', () => {
  const src = readBackend('services/demo_seed/gen_tertiaire_efa.py');

  it('file exists', () => {
    expect(src).not.toBeNull();
  });

  it('contains seed_tertiaire_efa function', () => {
    expect(src).toMatch(/seed_tertiaire_efa/);
  });

  it('creates 3 EFA (Paris, Nice, Lyon)', () => {
    expect(src).toMatch(/Paris/);
    expect(src).toMatch(/Nice/);
    expect(src).toMatch(/Lyon/);
  });

  it('handles idempotence (filter_by check)', () => {
    expect(src).toMatch(/filter_by/);
  });

  it('is wired in orchestrator', () => {
    const orch = readBackend('services/demo_seed/orchestrator.py');
    expect(orch).toMatch(/seed_tertiaire_efa/);
  });
});
