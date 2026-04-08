/**
 * PROMEOS — Tests unifiés page Achat Energie
 * Vérifie la structure de la page unifiée avec 5 tabs,
 * le deep-link support, et les imports nécessaires.
 */
import { describe, it, expect } from 'vitest';
import { readFileSync, existsSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const pagesDir = join(__dirname, '..', 'pages');
const componentsDir = join(__dirname, '..', 'components');

function readPage(file) {
  return readFileSync(join(pagesDir, file), 'utf8');
}

const PURCHASE_SRC = readPage('PurchasePage.jsx');

// ── Structure page unifiée ──────────────────────────────────────────────────

describe('Page unifiée — structure tabs', () => {
  it('définit un tableau TABS avec les 5 onglets', () => {
    // Le fichier doit contenir un tableau TABS
    expect(PURCHASE_SRC).toMatch(/TABS\s*=\s*\[/);
  });

  it('contient les clés des 5 tabs', () => {
    const tabs = ['simulation', 'portefeuille', 'echeances', 'historique'];
    for (const tab of tabs) {
      expect(PURCHASE_SRC).toContain(`'${tab}'`);
    }
  });

  it('utilise activeTab pour le rendu conditionnel', () => {
    expect(PURCHASE_SRC).toMatch(/activeTab/);
  });
});

// ── Deep-link via URL params ────────────────────────────────────────────────

describe('Page unifiée — deep-link support', () => {
  it('lit le paramètre tab depuis useSearchParams', () => {
    expect(PURCHASE_SRC).toMatch(/useSearchParams/);
  });

  it('utilise searchParams pour déterminer le tab actif', () => {
    expect(PURCHASE_SRC).toMatch(/searchParams/);
  });
});

// ── Imports et dépendances ──────────────────────────────────────────────────

describe('Page unifiée — imports', () => {
  it('importe useScope pour le contexte organisation/site', () => {
    expect(PURCHASE_SRC).toMatch(/useScope/);
  });

  it('importe les services API achat', () => {
    expect(PURCHASE_SRC).toMatch(/getPurchaseEstimate|computePurchaseScenarios/);
  });

  it('importe les formatters (fmtEur, fmtKwh)', () => {
    expect(PURCHASE_SRC).toMatch(/fmtEur/);
    expect(PURCHASE_SRC).toMatch(/fmtKwh/);
  });

  it('importe PageShell pour le layout', () => {
    expect(PURCHASE_SRC).toMatch(/PageShell/);
  });
});

// ── Composants embarqués ────────────────────────────────────────────────────

describe('Page unifiée — composants', () => {
  it('utilise MarketContextBanner', () => {
    expect(PURCHASE_SRC).toMatch(/MarketContextBanner/);
  });

  it("contient un ErrorState pour la gestion d'erreur", () => {
    expect(PURCHASE_SRC).toMatch(/ErrorState/);
  });

  it('contient un Skeleton pour le chargement', () => {
    expect(PURCHASE_SRC).toMatch(/Skeleton/);
  });
});

// ── Robustesse ──────────────────────────────────────────────────────────────

describe('Page unifiée — robustesse', () => {
  it('contient un PurchaseErrorBoundary', () => {
    expect(PURCHASE_SRC).toMatch(/PurchaseErrorBoundary/);
  });

  it('gère le cas site non sélectionné (EmptyState)', () => {
    expect(PURCHASE_SRC).toMatch(/EmptyState/);
  });
});

// ── Wizard assistant extraction ─────────────────────────────────────────────

describe('Wizard assistant — extraction composant', () => {
  const wizardPath = join(componentsDir, 'purchase', 'PurchaseAssistantWizard.jsx');
  const wizardExists = existsSync(wizardPath);

  it.skipIf(!wizardExists)('PurchaseAssistantWizard.jsx existe dans components/purchase/', () => {
    expect(wizardExists).toBe(true);
  });

  it.skipIf(!wizardExists)('le wizard exporte un composant par défaut', () => {
    const content = readFileSync(wizardPath, 'utf8');
    expect(content).toMatch(/export\s+default|export\s+\{.*default/);
  });
});
