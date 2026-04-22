/**
 * PROMEOS — Sol interpreters tests (pages/cockpit/sol_interpreters.js).
 *
 * Fonctions pures de présentation — testées via rendu JSX en string
 * pour vérifier le wording et les conditions.
 */
import { describe, expect, it } from 'vitest';
import { Children, isValidElement } from 'react';
import {
  buildCockpitNarrative,
  buildCockpitSubNarrative,
  buildWeekCards,
  interpretCompliance,
  interpretConsumption,
  interpretCost,
} from '../sol_interpreters';

// Helper : extract flat text from a JSX element (ignores tags, joins leafs)
function jsxToText(node) {
  if (node == null || typeof node === 'boolean') return '';
  if (typeof node === 'string' || typeof node === 'number') return String(node);
  if (Array.isArray(node)) return node.map(jsxToText).join('');
  if (isValidElement(node)) {
    return Children.toArray(node.props?.children || [])
      .map(jsxToText)
      .join('');
  }
  return '';
}

describe('interpretCost', () => {
  it('stable delta returns "stable" phrase', () => {
    const text = jsxToText(interpretCost({ costDelta: 0 }, { orgName: 'Test' }));
    expect(text).toMatch(/stable/i);
  });

  it('high positive delta mentions driver sites', () => {
    const text = jsxToText(
      interpretCost(
        { costDelta: 0.08, topDriverSites: [{ name: 'Lyon' }, { name: 'Nice' }] },
        { orgName: 'X' }
      )
    );
    expect(text).toMatch(/Lyon/);
    expect(text).toMatch(/Nice/);
    expect(text).toMatch(/Hausse/i);
  });

  it('negative delta mentions baisse', () => {
    const text = jsxToText(interpretCost({ costDelta: -0.04 }, { orgName: 'Patrimoine HELIOS' }));
    expect(text).toMatch(/Baisse/i);
    expect(text).toMatch(/HELIOS/i);
  });
});

describe('interpretCompliance', () => {
  it('score >=80 returns positive phrasing', () => {
    const text = jsxToText(interpretCompliance({ score: 85 }));
    expect(text).toMatch(/solide|trajectoire/i);
  });

  it('score 60-79 mentions zone à risque + lead site', () => {
    const text = jsxToText(
      interpretCompliance({
        score: 62,
        sitesAtRisk: 3,
        leadRiskSite: { name: 'Marseille école' },
      })
    );
    expect(text).toMatch(/zone à risque|trois sites/i);
    expect(text).toMatch(/Marseille école/);
  });

  it('score <60 returns critical phrasing', () => {
    const text = jsxToText(interpretCompliance({ score: 50 }));
    expect(text).toMatch(/critique|rapide/i);
  });
});

describe('interpretConsumption', () => {
  it('negative delta mentions baisse + sites', () => {
    const text = jsxToText(
      interpretConsumption(
        { consoDelta: -0.04, topBaisseSites: [{ name: 'Paris' }, { name: 'Toulouse' }] },
        { orgName: 'X' }
      )
    );
    expect(text).toMatch(/moins/i);
    expect(text).toMatch(/Paris/);
    expect(text).toMatch(/Toulouse/);
  });

  it('high positive delta flags hausse', () => {
    const text = jsxToText(interpretConsumption({ consoDelta: 0.08 }, { orgName: 'X' }));
    expect(text).toMatch(/hausse/i);
  });
});

describe('buildCockpitNarrative', () => {
  it('zero alerts → "Rien d\'urgent"', () => {
    const text = jsxToText(buildCockpitNarrative({ alertsCount: 0 }));
    expect(text).toMatch(/Rien d'urgent/);
  });

  it('3 alerts with top title → mentions number + title', () => {
    const text = jsxToText(
      buildCockpitNarrative({ alertsCount: 3, topAlertTitle: 'la facture Lyon' })
    );
    expect(text).toMatch(/3 points méritent/);
    expect(text).toMatch(/la facture Lyon/);
  });

  it('1 alert uses singular', () => {
    const text = jsxToText(buildCockpitNarrative({ alertsCount: 1 }));
    expect(text).toMatch(/1 point mérite/);
  });
});

describe('buildCockpitSubNarrative', () => {
  it('includes site count + comex days', () => {
    const text = jsxToText(buildCockpitSubNarrative({ sitesCount: 5, nextComexDays: 11 }));
    expect(text).toMatch(/5 sites/);
    expect(text).toMatch(/11 jours/);
  });
});

describe('buildWeekCards', () => {
  it('transforms alerts into week card props', () => {
    const cards = buildWeekCards([
      { id: 'a1', severity: 'attention', title: 'Test 1', summary: 'body' },
      { id: 'a2', severity: 'bonne_nouvelle', title: 'Test 2', summary: 'body' },
      { id: 'a3', severity: 'à_faire', title: 'Test 3', summary: 'body' },
    ]);
    expect(cards).toHaveLength(3);
    expect(cards[0].tagKind).toBe('attention');
    expect(cards[0].tagLabel).toBe('À regarder');
    expect(cards[1].tagKind).toBe('succes');
    expect(cards[1].tagLabel).toBe('Bonne nouvelle');
    expect(cards[2].tagKind).toBe('afaire');
    expect(cards[2].tagLabel).toBe('À faire');
  });

  it('caps at 3 alerts max', () => {
    const many = Array.from({ length: 10 }, (_, i) => ({
      id: `a${i}`,
      severity: 'attention',
      title: `Alert ${i}`,
    }));
    const cards = buildWeekCards(many);
    expect(cards).toHaveLength(3);
  });

  it('empty array returns empty array', () => {
    expect(buildWeekCards([])).toEqual([]);
  });
});
