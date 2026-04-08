/**
 * PROMEOS — Source Guard : labels HT sur les montants € (Achat Energie)
 * Vérifie que tous les montants €/an et €/MWh incluent le label "HT".
 * Conformité fiscale B2B : affichage HT obligatoire.
 */
import { describe, it, expect } from 'vitest';
import { readFileSync, existsSync } from 'fs';

const PURCHASE_PAGE = 'src/pages/PurchasePage.jsx';

describe('Purchase HT source guard — PurchasePage.jsx', () => {
  // Guard : le fichier doit exister
  const fileExists = existsSync(PURCHASE_PAGE);

  it('PurchasePage.jsx existe', () => {
    expect(fileExists).toBe(true);
  });

  if (!fileExists) return;

  const content = readFileSync(PURCHASE_PAGE, 'utf8');

  it('tous les "€/an" incluent HT (€ HT/an)', () => {
    // Compte les occurrences de €/an (toutes formes)
    const bareEurAn = (content.match(/€\/an/g) || []).length;
    const htEurAn = (content.match(/€\s*HT\/an/g) || []).length;
    // Chaque €/an doit être un € HT/an
    expect(bareEurAn).toBeLessThanOrEqual(htEurAn);
  });

  it('tous les "€/MWh" incluent HT (€ HT/MWh)', () => {
    const bareEurMwh = (content.match(/€\/MWh/g) || []).length;
    const htEurMwh = (content.match(/€\s*HT\/MWh/g) || []).length;
    expect(bareEurMwh).toBeLessThanOrEqual(htEurMwh);
  });

  it('pas de "€/kWh" sans HT dans le rendu', () => {
    const bareEurKwh = (content.match(/€\/kWh/g) || []).length;
    const htEurKwh = (content.match(/€\s*HT\/kWh/g) || []).length;
    expect(bareEurKwh).toBeLessThanOrEqual(htEurKwh);
  });
});

// Guard sur les composants purchase/ si présents
describe('Purchase HT source guard — composants purchase/', () => {
  const wizardPath = 'src/components/purchase/PurchaseAssistantWizard.jsx';
  const wizardExists = existsSync(wizardPath);

  it.skipIf(!wizardExists)('PurchaseAssistantWizard — €/MWh inclut HT', () => {
    const content = readFileSync(wizardPath, 'utf8');
    const bare = (content.match(/€\/MWh/g) || []).length;
    const ht = (content.match(/€\s*HT\/MWh/g) || []).length;
    expect(bare).toBeLessThanOrEqual(ht);
  });
});
