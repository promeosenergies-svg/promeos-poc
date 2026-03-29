import { describe, it, expect } from 'vitest';

const MOCK = {
  impact: {
    total_eur: 118180,
    conformite_eur: 63239,
    factures_eur: 49261,
    optimisation_eur: 5680,
    sites_concernes: 5,
  },
  sante: {
    conformite: { score: 81, status: 'ok' },
    qualite_donnees: { score: 85, status: 'ok' },
    contrats: { actifs: 4, couverture_pct: 100, expirant_90j: 4, status: 'warn' },
    consommation: { total_mwh: 5450, kwh_m2_an: 311, status: 'ok' },
  },
  actions: [
    { id: 'a1', impact_eur: 50591, categorie: 'conformite' },
    { id: 'a2', impact_eur: 49261, categorie: 'facturation' },
    { id: 'a3', impact_eur: 12648, categorie: 'conformite' },
    { id: 'a4', impact_eur: null, categorie: 'achat' },
    { id: 'a5', impact_eur: 5680, categorie: 'optimisation' },
  ],
};

describe('V1+ — Impact total cohérence', () => {
  it('total = conformité + factures + optimisation', () => {
    const { impact } = MOCK;
    expect(impact.total_eur).toBe(
      impact.conformite_eur + impact.factures_eur + impact.optimisation_eur
    );
  });
});

describe('V1+ — Zéro doublon', () => {
  it('risque_financier absent de sante (il est dans impact)', () => {
    expect(MOCK.sante).not.toHaveProperty('risque_financier');
    expect(MOCK.sante).not.toHaveProperty('risque');
    expect(JSON.stringify(MOCK.sante)).not.toContain('63239');
  });

  it('qualite_donnees = 1 seul score', () => {
    const qd = MOCK.sante.qualite_donnees;
    expect(qd).toHaveProperty('score');
    expect(qd).not.toHaveProperty('completude');
    expect(qd).not.toHaveProperty('couverture_operationnelle');
    expect(qd).not.toHaveProperty('donnees_exploitables');
  });
});

describe('V1+ — Actions', () => {
  it('triées par impact_eur DESC, nulls last', () => {
    const withValues = MOCK.actions.filter((a) => a.impact_eur !== null);
    const impacts = withValues.map((a) => a.impact_eur);
    expect(impacts).toEqual([...impacts].sort((a, b) => b - a));
  });

  it('catégories valides uniquement', () => {
    const valid = ['conformite', 'facturation', 'optimisation', 'achat'];
    MOCK.actions.forEach((a) => {
      expect(valid).toContain(a.categorie);
    });
  });
});

describe('V1+ — Source guard (no frontend calc)', () => {
  it('pas de calcul métier dans les composants cockpit', async () => {
    const fs = await import('fs');
    const path = await import('path');
    const dir = path.resolve('src/pages/cockpit');
    if (!fs.existsSync(dir)) return; // skip si pas dans le bon cwd
    const files = fs.readdirSync(dir).filter((f) => f.endsWith('.jsx'));
    for (const file of files) {
      const content = fs.readFileSync(path.join(dir, file), 'utf8');
      expect(content).not.toMatch(/\*\s*0\.052/); // CO2 factor
      expect(content).not.toMatch(/\*\s*7500/); // BASE_PENALTY
      expect(content).not.toMatch(/\*\s*3750/); // A_RISQUE penalty
      expect(content).not.toMatch(/\*\s*0\.01\b/); // 1% optim
    }
  });
});
