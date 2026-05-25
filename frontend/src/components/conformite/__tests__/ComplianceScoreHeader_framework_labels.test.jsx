// @vitest-environment jsdom
/**
 * Hotfix 2026-05-24 — ComplianceScoreHeader rend les labels FR depuis
 * `fw.label_fr` (backend) sans aucun mapping métier côté FE.
 *
 * Bug pré-hotfix : fallback ternaire `: 'APER'` étiquetait audit_sme,
 * iso_50001, solar_toiture, beges comme APER → 3 lignes APER côté DAF.
 *
 * Tests render (jsdom) — vérifient le DOM réel produit.
 */
import '@testing-library/jest-dom/vitest';
import { describe, it, expect, afterEach } from 'vitest';
import { render, screen, within, cleanup } from '@testing-library/react';

import ComplianceScoreHeader from '../ComplianceScoreHeader';

afterEach(() => cleanup());

describe('ComplianceScoreHeader — labels FR canoniques depuis backend', () => {
  const baseScore = {
    score: 36,
    confidence: 'medium',
    frameworks_evaluated: 5,
    frameworks_total: 5,
  };

  describe('Site scope (breakdown[])', () => {
    it('rend "Décret Tertiaire" pour tertiaire_operat', () => {
      render(
        <ComplianceScoreHeader
          complianceScore={{
            ...baseScore,
            breakdown: [
              {
                framework: 'tertiaire_operat',
                label_fr: 'Décret Tertiaire',
                score: 70,
                weight: 0.45,
                available: true,
                source: 'v2_adaptive',
              },
            ],
          }}
        />
      );
      expect(screen.getByTestId('framework-label-tertiaire_operat')).toHaveTextContent(
        'Décret Tertiaire'
      );
    });

    it('rend "Audit SMÉ" pour audit_sme (régression cardinale pré-hotfix)', () => {
      render(
        <ComplianceScoreHeader
          complianceScore={{
            ...baseScore,
            breakdown: [
              {
                framework: 'audit_sme',
                label_fr: 'Audit SMÉ',
                score: 0,
                weight: 0.15,
                available: true,
                source: 'v2_adaptive',
              },
            ],
          }}
        />
      );
      const cell = screen.getByTestId('framework-label-audit_sme');
      expect(cell).toHaveTextContent('Audit SMÉ');
      expect(cell).not.toHaveTextContent(/^APER$/);
    });

    it('rend "Solarisation toiture" pour solar_toiture', () => {
      render(
        <ComplianceScoreHeader
          complianceScore={{
            ...baseScore,
            breakdown: [
              {
                framework: 'solar_toiture',
                label_fr: 'Solarisation toiture',
                score: 0,
                weight: 0.1,
                available: true,
                source: 'v2_adaptive',
              },
            ],
          }}
        />
      );
      const cell = screen.getByTestId('framework-label-solar_toiture');
      expect(cell).toHaveTextContent('Solarisation toiture');
      expect(cell).not.toHaveTextContent(/^APER$/);
    });

    it('rend "ISO 50001" pour iso_50001', () => {
      render(
        <ComplianceScoreHeader
          complianceScore={{
            ...baseScore,
            breakdown: [
              {
                framework: 'iso_50001',
                label_fr: 'ISO 50001',
                score: 50,
                weight: 0.2,
                available: true,
                source: 'v2_adaptive',
              },
            ],
          }}
        />
      );
      expect(screen.getByTestId('framework-label-iso_50001')).toHaveTextContent('ISO 50001');
    });

    it('rend "BEGES" pour beges (futur)', () => {
      render(
        <ComplianceScoreHeader
          complianceScore={{
            ...baseScore,
            breakdown: [
              {
                framework: 'beges',
                label_fr: 'BEGES',
                score: 80,
                weight: 0.1,
                available: true,
                source: 'v2_adaptive',
              },
            ],
          }}
        />
      );
      expect(screen.getByTestId('framework-label-beges')).toHaveTextContent('BEGES');
    });

    it('rend formatFrameworkCode (humanisé neutre) si label_fr absent', () => {
      // Cas hypothétique : un nouveau framework backend pas encore mappé.
      // Le FE ne doit JAMAIS fallback sur "APER".
      render(
        <ComplianceScoreHeader
          complianceScore={{
            ...baseScore,
            breakdown: [
              {
                framework: 'new_obligation_2027',
                score: 42,
                weight: 0.1,
                available: true,
                source: 'v2_adaptive',
              },
              // label_fr omis volontairement
            ],
          }}
        />
      );
      const cell = screen.getByTestId('framework-label-new_obligation_2027');
      expect(cell).toHaveTextContent('New Obligation 2027');
      expect(cell).not.toHaveTextContent(/APER/);
    });

    it('APER apparaît UNE SEULE fois quand un seul framework aper est présent (anti-régression bug 3 lignes)', () => {
      render(
        <ComplianceScoreHeader
          complianceScore={{
            ...baseScore,
            breakdown: [
              {
                framework: 'tertiaire_operat',
                label_fr: 'Décret Tertiaire',
                score: 70,
                weight: 0.45,
                available: true,
                source: 'v2_adaptive',
              },
              {
                framework: 'bacs',
                label_fr: 'BACS',
                score: 70,
                weight: 0.3,
                available: true,
                source: 'v2_adaptive',
              },
              {
                framework: 'aper',
                label_fr: 'APER',
                score: 50,
                weight: 0.25,
                available: true,
                source: 'v2_adaptive',
              },
              {
                framework: 'audit_sme',
                label_fr: 'Audit SMÉ',
                score: 0,
                weight: 0.1,
                available: true,
                source: 'v2_adaptive',
              },
              {
                framework: 'solar_toiture',
                label_fr: 'Solarisation toiture',
                score: 0,
                weight: 0.1,
                available: true,
                source: 'v2_adaptive',
              },
            ],
          }}
        />
      );
      // 5 lignes, 5 labels distincts, et "APER" seulement 1 fois.
      expect(screen.getByTestId('framework-label-tertiaire_operat')).toBeInTheDocument();
      expect(screen.getByTestId('framework-label-bacs')).toBeInTheDocument();
      expect(screen.getByTestId('framework-label-aper')).toHaveTextContent(/^APER\b/);
      expect(screen.getByTestId('framework-label-audit_sme')).toHaveTextContent('Audit SMÉ');
      expect(screen.getByTestId('framework-label-solar_toiture')).toHaveTextContent(
        'Solarisation toiture'
      );

      // Comptage APER : strict — chercher TOUS les éléments dont le texte
      // contient exactement "APER" comme mot isolé dans la colonne label.
      const allLabelCells = document.querySelectorAll('[data-testid^="framework-label-"]');
      let aperCount = 0;
      allLabelCells.forEach((el) => {
        if (
          /\bAPER\b/.test(el.textContent) &&
          !/Décret|BACS|Audit|Solarisation|ISO/.test(el.textContent)
        ) {
          aperCount += 1;
        }
      });
      expect(aperCount).toBe(1);
    });
  });

  describe('Portfolio scope (breakdown_avg_labeled[])', () => {
    it('itère sur breakdown_avg_labeled si breakdown absent', () => {
      render(
        <ComplianceScoreHeader
          complianceScore={{
            ...baseScore,
            // pas de breakdown[] (portfolio scope)
            breakdown_avg_labeled: [
              { framework: 'tertiaire_operat', label_fr: 'Décret Tertiaire', score: 70 },
              { framework: 'bacs', label_fr: 'BACS', score: 70 },
              { framework: 'aper', label_fr: 'APER', score: 50 },
              { framework: 'audit_sme', label_fr: 'Audit SMÉ', score: 0 },
              { framework: 'solar_toiture', label_fr: 'Solarisation toiture', score: 0 },
            ],
          }}
        />
      );
      // Tous les labels portfolios doivent être rendus distinctement.
      expect(screen.getByTestId('framework-label-audit_sme')).toHaveTextContent('Audit SMÉ');
      expect(screen.getByTestId('framework-label-solar_toiture')).toHaveTextContent(
        'Solarisation toiture'
      );
      // L'ancien bug visible : 3 lignes APER. Ici on doit en avoir 1 max.
      const aperOnly = screen
        .getAllByTestId(/^framework-label-/)
        .filter(
          (el) => /\bAPER\b/.test(el.textContent) && !/Audit|Solarisation/.test(el.textContent)
        );
      expect(aperOnly.length).toBe(1);
    });

    it('fallback sur breakdown_avg legacy (dict) avec formatFrameworkCode si pas de label_fr', () => {
      // Rétro-compat : un payload BE legacy (pré-hotfix) avec breakdown_avg
      // sans label_fr — le FE ne doit JAMAIS rendre "APER" pour audit_sme.
      render(
        <ComplianceScoreHeader
          complianceScore={{
            ...baseScore,
            breakdown_avg: {
              tertiaire_operat: 70,
              bacs: 70,
              aper: 50,
              audit_sme: 0,
              solar_toiture: 0,
            },
          }}
        />
      );
      const auditSme = screen.getByTestId('framework-label-audit_sme');
      expect(auditSme).toHaveTextContent('Audit Sme'); // formatFrameworkCode neutre
      expect(auditSme).not.toHaveTextContent(/^APER$/);
      const solar = screen.getByTestId('framework-label-solar_toiture');
      expect(solar).toHaveTextContent('Solar Toiture');
      expect(solar).not.toHaveTextContent(/^APER$/);
    });
  });
});
