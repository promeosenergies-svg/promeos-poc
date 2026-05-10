/**
 * grammar/hub/ChartFrame — source-guards Vitest (Sprint Grammaire v1.2)
 *
 * Tests pure-grep : contrat question/reponse/chart/footer-SCM.
 */
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { resolve } from 'path';

const SRC = resolve(__dirname, '../ChartFrame.jsx');
const read = () => readFileSync(SRC, 'utf-8');

describe('grammar/hub/ChartFrame', () => {
  it('data-component ChartFrame (source-guard L11.4)', () => {
    expect(read()).toContain('data-component="ChartFrame"');
  });

  it('question rendue en Fraunces via sol-font-display', () => {
    const src = read();
    expect(src).toContain('question');
    expect(src).toContain('var(--sol-font-display)');
  });

  it('reponse narrative avec support ReactNode (answer prop)', () => {
    const src = read();
    expect(src).toContain('answer');
    expect(src).toContain('sol-ink-500');
  });

  it('zone chart enfant avec min-height 165px (spec grammaire)', () => {
    expect(read()).toContain('minHeight');
    expect(read()).toContain('165px');
  });

  it('footer SCM : source + confidence + updatedAt', () => {
    const src = read();
    expect(src).toContain('sourceName');
    expect(src).toContain('confidence');
    expect(src).toContain('updatedAt');
    expect(src).toContain('MAJ');
  });

  it('footer SCM separe par borderTop (sol-rule) — style React camelCase', () => {
    const src = read();
    // React JSX utilise borderTop (camelCase) pour border-top en style inline
    expect(src).toMatch(/borderTop|border-top/);
    expect(src).toContain('sol-rule');
  });

  it('zero calcul metier — pas de logique import ou computed values', () => {
    const src = read();
    expect(src).not.toContain('import axios');
    expect(src).not.toContain('useEffect');
    expect(src).not.toContain('useState');
  });
});
