/**
 * PROMEOS — Tests scopeLabel (Hotfix Énergie 2026-05-31).
 *
 * Vérifie l'absence totale de fallback technique `Site #${id}` dans les
 * vues Énergie.
 */
import { describe, expect, it } from 'vitest';
import { formatSiteLabel, FALLBACK_SITE_SELECTED, FALLBACK_NO_SITE } from '../ui/energy/scopeLabel';

describe('formatSiteLabel — priorités canoniques', () => {
  it('retourne site.nom si fourni (champ canonique backend)', () => {
    expect(formatSiteLabel({ nom: 'Siège HELIOS Paris', id: 1 })).toBe('Siège HELIOS Paris');
  });

  it('retourne site.name si nom absent (alias)', () => {
    expect(formatSiteLabel({ name: 'HQ Paris', id: 1 })).toBe('HQ Paris');
  });

  it('retourne site.label si nom et name absents', () => {
    expect(formatSiteLabel({ label: 'Mon Site', id: 1 })).toBe('Mon Site');
  });

  it('retourne site.display_name si autres absents', () => {
    expect(formatSiteLabel({ display_name: 'Site Display', id: 1 })).toBe('Site Display');
  });

  it("retourne FALLBACK_SITE_SELECTED si seul l'id est connu", () => {
    expect(formatSiteLabel({ id: 1 })).toBe(FALLBACK_SITE_SELECTED);
    expect(formatSiteLabel({ id: 42 })).toBe('Site sélectionné');
  });

  it('retourne FALLBACK_NO_SITE si site null', () => {
    expect(formatSiteLabel(null)).toBe(FALLBACK_NO_SITE);
    expect(formatSiteLabel(null)).toBe('Sélectionner un site');
  });

  it('retourne FALLBACK_NO_SITE si site undefined', () => {
    expect(formatSiteLabel(undefined)).toBe(FALLBACK_NO_SITE);
  });

  it('retourne FALLBACK_NO_SITE si site sans id ni nom', () => {
    expect(formatSiteLabel({})).toBe(FALLBACK_NO_SITE);
  });
});

describe('formatSiteLabel — interdictions strictes (anti-régression hotfix)', () => {
  it('JAMAIS de fallback `Site #${id}`', () => {
    const result = formatSiteLabel({ id: 1 });
    expect(result).not.toMatch(/Site #\d+/);
    expect(result).not.toMatch(/#\d+/);
    expect(result).not.toContain('#');
  });

  it('JAMAIS de fallback `#${id}` sans préfixe', () => {
    const result = formatSiteLabel({ id: 42 });
    expect(result).not.toMatch(/^#/);
  });

  it('JAMAIS de double « Site Site » dans le label', () => {
    // formatSiteLabel ne retourne PAS le préfixe « Site » seul ;
    // le préfixe est rendu par le FilterGroup label="Site".
    expect(formatSiteLabel({ id: 1 })).not.toMatch(/^Site Site/);
    expect(formatSiteLabel({ nom: 'HQ' })).not.toMatch(/^Site /);
  });
});

describe('Hotfix Énergie — recherche statique interdit `Site #` dans ui/energy + pages énergie', () => {
  // Cette suite vérifie statiquement que les fichiers SOURCE des vues
  // énergie ne contiennent plus le pattern `Site #${...}`.
  const { readFileSync } = require('fs');
  const { resolve } = require('path');

  const FILES = [
    '../ui/energy/EnergyFilterBar.jsx',
    '../ui/energy/scopeLabel.js',
    '../pages/consumption/LoadCurveTab.jsx',
    '../pages/consumption/CostContractTab.jsx',
    '../pages/consumption/MarketExposureTab.jsx',
    '../pages/usages/WeekProfileTab.jsx',
  ];

  for (const file of FILES) {
    it(`${file.split('/').pop()} ne contient PAS \`Site #\${id}\` ni \`#\${id}\` technique`, () => {
      const src = readFileSync(resolve(__dirname, file), 'utf8');
      // Pour éviter les faux-positifs sur les commentaires (//, /**, etc.),
      // on extrait uniquement le code non-commenté.
      const lines = src.split('\n').filter((line) => {
        const trimmed = line.trim();
        return !trimmed.startsWith('//') && !trimmed.startsWith('*');
      });
      const code = lines.join('\n');

      // Pattern interdit dans le CODE (pas dans commentaires)
      expect(code).not.toMatch(/`Site #\$\{[^}]*\}`/);
      expect(code).not.toMatch(/`Compteur #\$\{[^}]*\}`/);
      expect(code).not.toMatch(/`Organisation #\$\{[^}]*\}`/);
      expect(code).not.toMatch(/`Entité #\$\{[^}]*\}`/);
      // Pattern : concat directe `#${scope.id}` ou `#${site.id}` utilisée
      // comme label utilisateur (sans passer par formatSiteLabel)
      expect(code).not.toMatch(/['"`]#\$\{scope\?\.id\}['"`]/);
      expect(code).not.toMatch(/['"`]#\$\{site\.id\}['"`]/);
    });
  }
});
