/**
 * PROMEOS — Source Guard : fusion Achat Energie (5 tabs unifiés)
 * Vérifie que PurchaseAssistantPage est redirigé (pas standalone),
 * que PurchasePage a les 5 onglets, et que les deep-links sont corrects.
 */
import { describe, it, expect } from 'vitest';
import { readFileSync, existsSync as _existsSync } from 'fs';

describe('Purchase fusion source guard', () => {
  it('PurchaseAssistantPage route redirects to fused tab', () => {
    const redirectsSrc = readFileSync('src/routes/legacyRedirects.js', 'utf8');
    expect(redirectsSrc).toMatch(/\['\/achat-assistant',\s*'\/achat-energie\?tab=assistant'\]/);
  });

  it("App.jsx n'importe pas PurchaseAssistantPage directement", () => {
    const content = readFileSync('src/App.jsx', 'utf8');
    // Après fusion, on doit utiliser Navigate redirect, pas un import direct
    expect(content).not.toMatch(/import\s+.*PurchaseAssistantPage\s+from/);
  });

  it('PurchasePage a les 5 onglets attendus', () => {
    const content = readFileSync('src/pages/PurchasePage.jsx', 'utf8');
    // Les 5 tabs de la page unifiée
    expect(content).toContain("'simulation'");
    expect(content).toContain("'assistant'");
    expect(content).toContain("'portefeuille'");
    expect(content).toContain("'echeances'");
    expect(content).toContain("'historique'");
  });

  it('routes.js utilise /achat-energie + tab=assistant (pas /achat-assistant)', () => {
    const routes = readFileSync('src/services/routes.js', 'utf8');
    // toPurchaseAssistant sets tab=assistant and returns /achat-energie?...
    expect(routes).toContain("p.set('tab', 'assistant')");
    expect(routes).toContain('/achat-energie');
    // L'ancienne route standalone ne doit plus exister
    expect(routes).not.toMatch(/['"]\/achat-assistant['"]/);
  });
});
