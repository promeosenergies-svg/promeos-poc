/**
 * PROMEOS — Source guards pour le scope switching Usages V4.
 * Vérifie que le scope multi-niveaux est correctement câblé.
 */
import { readFileSync } from 'fs';
import { resolve } from 'path';
import { describe, it, expect } from 'vitest';

const pageSrc = readFileSync(resolve(__dirname, '../UsagesDashboardPage.jsx'), 'utf-8');
const scopeBarSrc = readFileSync(
  resolve(__dirname, '../../components/usages/ScopeBar.jsx'),
  'utf-8'
);
const scopeCtxSrc = readFileSync(resolve(__dirname, '../../contexts/ScopeContext.jsx'), 'utf-8');
const energySrc = readFileSync(resolve(__dirname, '../../services/api/energy.js'), 'utf-8');

describe('UsagesDashboardPage — scope wiring', () => {
  it('importe getScopedUsagesDashboard (pas getUsagesDashboard seul)', () => {
    expect(pageSrc).toMatch(/getScopedUsagesDashboard/);
  });

  it('importe getScopedUsageTimeline', () => {
    expect(pageSrc).toMatch(/getScopedUsageTimeline/);
  });

  it('dependency array inclut scope.portefeuilleId', () => {
    expect(pageSrc).toMatch(/scope\.portefeuilleId/);
  });

  it('dependency array inclut scope.entiteId', () => {
    expect(pageSrc).toMatch(/scope\.entiteId/);
  });

  it('masque Comptage en mode multi-site', () => {
    expect(pageSrc).toMatch(/comptage/);
    expect(pageSrc).toMatch(/isMultiSite/);
  });

  it('ne contient plus entiteFilter (dead code supprimé)', () => {
    expect(pageSrc).not.toMatch(/entiteFilter/);
  });

  it('ne contient plus onEntiteFilter', () => {
    expect(pageSrc).not.toMatch(/onEntiteFilter/);
  });
});

describe('ScopeBar — scope-tree dynamique', () => {
  it('importe getScopeTree', () => {
    expect(scopeBarSrc).toMatch(/getScopeTree/);
  });

  it('appelle setEntite', () => {
    expect(scopeBarSrc).toMatch(/setEntite/);
  });

  it('ne contient plus onEntiteFilter prop', () => {
    expect(scopeBarSrc).not.toMatch(/onEntiteFilter/);
  });

  it('contient 4 niveaux (org, entite, portfolio, site)', () => {
    expect(scopeBarSrc).toMatch(/id:\s*'org'/);
    expect(scopeBarSrc).toMatch(/id:\s*'entite'/);
    expect(scopeBarSrc).toMatch(/id:\s*'portfolio'/);
    expect(scopeBarSrc).toMatch(/id:\s*'site'/);
  });
});

describe('ScopeContext — entiteId support', () => {
  it('exporte setEntite', () => {
    expect(scopeCtxSrc).toMatch(/setEntite/);
  });

  it('scope par défaut inclut entiteId', () => {
    expect(scopeCtxSrc).toMatch(/entiteId:\s*null/);
  });
});

describe('API energy — scoped functions', () => {
  it('exporte getScopedUsagesDashboard', () => {
    expect(energySrc).toMatch(/export const getScopedUsagesDashboard/);
  });

  it('exporte getScopedUsageTimeline', () => {
    expect(energySrc).toMatch(/export const getScopedUsageTimeline/);
  });

  it('exporte getScopeTree', () => {
    expect(energySrc).toMatch(/export const getScopeTree/);
  });

  it('scoped-dashboard appelle le bon endpoint', () => {
    expect(energySrc).toMatch(/\/usages\/scoped-dashboard/);
  });

  it('scoped-timeline appelle le bon endpoint', () => {
    expect(energySrc).toMatch(/\/usages\/scoped-timeline/);
  });

  it('scope-tree appelle le bon endpoint', () => {
    expect(energySrc).toMatch(/\/patrimoine\/scope-tree/);
  });
});
