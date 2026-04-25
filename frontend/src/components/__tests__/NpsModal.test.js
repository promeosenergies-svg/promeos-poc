/**
 * PROMEOS — NpsModal source-guard tests (Sprint CX P1 residual)
 * Garantit la structure du composant sans mount React (source string grep).
 */
import { describe, it, expect } from 'vitest';
import fs from 'node:fs';
import path from 'node:path';

const FILE = path.resolve(__dirname, '../NpsModal.jsx');
const SRC = fs.readFileSync(FILE, 'utf8');

describe('NpsModal source guard', () => {
  it('imports submitNps from services/api/nps', () => {
    expect(SRC).toMatch(/from '\.\.\/services\/api\/nps'/);
    expect(SRC).toMatch(/submitNps/);
  });

  it('imports guards from utils/nps', () => {
    expect(SRC).toMatch(/from '\.\.\/utils\/nps'/);
    expect(SRC).toMatch(/markNpsSubmitted/);
    expect(SRC).toMatch(/markNpsDismissed/);
  });

  it('exposes 11 score buttons (0-10)', () => {
    // SCORES array with length 11
    expect(SRC).toMatch(/length:\s*11/);
  });

  it('has the canonical FR question', () => {
    expect(SRC).toContain('Dans quelle mesure recommanderiez-vous PROMEOS');
  });

  it('has 0 / 10 scale label', () => {
    expect(SRC).toMatch(/0\s*=\s*Pas du tout/);
    expect(SRC).toMatch(/10\s*=\s*Absolument/);
  });

  it('includes verbatim textarea with optional wording', () => {
    expect(SRC).toMatch(/textarea/);
    expect(SRC).toMatch(/optionnel/i);
  });

  it('has aria attributes (a11y)', () => {
    expect(SRC).toMatch(/role="dialog"/);
    expect(SRC).toMatch(/aria-modal="true"/);
    expect(SRC).toMatch(/role="radiogroup"/);
    expect(SRC).toMatch(/aria-checked/);
    expect(SRC).toMatch(/aria-label/);
  });

  it('supports keyboard navigation on score buttons', () => {
    expect(SRC).toMatch(/ArrowLeft/);
    expect(SRC).toMatch(/ArrowRight/);
  });

  it('has both CTA Envoyer and Ignorer', () => {
    expect(SRC).toMatch(/Envoyer/);
    expect(SRC).toMatch(/Ignorer/);
  });

  it('classifies scores into promoter/passive/detractor', () => {
    expect(SRC).toMatch(/promoter/);
    expect(SRC).toMatch(/passive/);
    expect(SRC).toMatch(/detractor/);
  });

  it('calls markNpsSubmitted on success to prevent re-trigger', () => {
    expect(SRC).toMatch(/markNpsSubmitted\(\)/);
  });
});
