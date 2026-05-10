/**
 * grammar/hub/HubPage — source-guards Vitest (Sprint Grammaire v1.2 Phase 3.4)
 *
 * Tests pure-grep sur le source JSX : verifient les contrats structurels
 * L11 Hub Page sans DOM (pattern PROMEOS source-guards).
 */
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { resolve } from 'path';

const SRC = resolve(__dirname, '../HubPage.jsx');
const read = () => readFileSync(SRC, 'utf-8');

describe('grammar/hub/HubPage', () => {
  it('data-component HubPage present pour source-guard L11', () => {
    expect(read()).toContain('data-component="HubPage"');
  });

  it('data-pillar present (analytics + CSS targeting)', () => {
    expect(read()).toContain('data-pillar={pillar}');
  });

  it('liste des piliers valides inclut les 6 piliers PROMEOS', () => {
    const src = read();
    expect(src).toContain("'briefing'");
    expect(src).toContain("'energie'");
    expect(src).toContain("'conformite'");
    expect(src).toContain("'factures'");
    expect(src).toContain("'achat'");
    expect(src).toContain("'patrimoine'");
  });

  it('slot KpiTriptych avec validation 3 enfants exactement (DEV)', () => {
    const src = read();
    expect(src).toContain('KpiTriptych');
    expect(src).toContain('hub-kpi-triptych');
    expect(src).toMatch(/count !== 3/);
  });

  it('slot ChartPair avec validation 2 enfants exactement (DEV)', () => {
    const src = read();
    expect(src).toContain('ChartPair');
    expect(src).toContain('hub-chart-pair');
    expect(src).toMatch(/count !== 2/);
  });

  it('slot Highlights avec validation 3-5 enfants (DEV)', () => {
    const src = read();
    expect(src).toContain('Highlights');
    expect(src).toContain('hub-highlights');
    expect(src).toMatch(/count < 3 \|\| count > 5/);
  });

  it('validation console.error (jamais throw) — doctrine PROMEOS resilience', () => {
    const src = read();
    expect(src).toContain('console.error');
    expect(src).not.toContain('throw new Error');
    expect(src).not.toContain('throw Error');
  });

  it('conteneur max-w-[1180px] mx-auto px-7 py-6 (spec grammaire L11)', () => {
    expect(read()).toContain('max-w-[1180px] mx-auto px-7 py-6');
  });

  it('compound components attaches sur HubPage (HubPage.KpiTriptych etc.)', () => {
    const src = read();
    expect(src).toContain('HubPage.KpiTriptych = KpiTriptych');
    expect(src).toContain('HubPage.ChartPair = ChartPair');
    expect(src).toContain('HubPage.Highlights = Highlights');
  });
});
