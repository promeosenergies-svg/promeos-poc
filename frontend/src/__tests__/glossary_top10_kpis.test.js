/**
 * PROMEOS — Sprint CX item #2
 * Contract test : les 10 KPIs cibles du sprint doivent TOUJOURS être dans le glossaire
 * avec term + short. Un `long` est exigé pour les KPIs complexes (formule ou réglementation).
 *
 * Cible : garantir la pédagogie inline sur les termes énergétiques clés de la facture.
 */
import { describe, it, expect } from 'vitest';
import { GLOSSARY } from '../ui/glossary.js';

// Les 10 KPIs cibles définis par la stratégie CX sprint 1 item #2
const TOP10_KPIS = [
  { key: 'turpe', label: 'TURPE', longRequired: true },
  { key: 'cta', label: 'CTA', longRequired: true },
  { key: 'accise_electricite', label: 'Accise électricité', longRequired: true },
  { key: 'car', label: 'CAR', longRequired: true },
  { key: 'tdn', label: 'TDN', longRequired: true },
  { key: 'cee', label: 'CEE', longRequired: true },
  { key: 'vnu', label: 'VNU', longRequired: true },
  { key: 'capacite', label: 'Capacité', longRequired: true },
  { key: 'tva', label: 'TVA', longRequired: true },
  { key: 'compliance_score', label: 'Score conformité', longRequired: true },
];

describe('Sprint CX item #2 — couverture glossary des 10 KPIs cibles', () => {
  for (const { key, label, longRequired } of TOP10_KPIS) {
    describe(`KPI "${label}" (clé: ${key})`, () => {
      it('existe dans GLOSSARY', () => {
        expect(GLOSSARY[key]).toBeDefined();
      });

      it('a un champ `term` non vide', () => {
        const entry = GLOSSARY[key];
        expect(entry.term).toBeTruthy();
        expect(entry.term.length).toBeGreaterThan(0);
      });

      it('a un champ `short` de 20 à 300 caractères', () => {
        const entry = GLOSSARY[key];
        expect(entry.short).toBeTruthy();
        expect(entry.short.length).toBeGreaterThanOrEqual(20);
        expect(entry.short.length).toBeLessThanOrEqual(300);
      });

      if (longRequired) {
        it('a un champ `long` de 100+ caractères (contexte réglementaire)', () => {
          const entry = GLOSSARY[key];
          expect(entry.long).toBeTruthy();
          expect(entry.long.length).toBeGreaterThanOrEqual(100);
        });
      }
    });
  }

  it('les 10 clés sont uniques', () => {
    const keys = TOP10_KPIS.map((k) => k.key);
    expect(new Set(keys).size).toBe(10);
  });

  it('les 10 labels sont uniques', () => {
    const labels = TOP10_KPIS.map((k) => k.label);
    expect(new Set(labels).size).toBe(10);
  });
});
