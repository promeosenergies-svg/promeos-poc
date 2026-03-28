/**
 * Shadow Billing Drawer — Source Guards
 * Vérifie que le frontend n'effectue AUCUN calcul billing et respecte les règles P0/P1.
 */
import { describe, it, expect } from 'vitest';
import fs from 'fs';
import path from 'path';

function readFile(rel) {
  const full = path.resolve(rel);
  return fs.existsSync(full) ? fs.readFileSync(full, 'utf8') : null;
}

const drawerContent = readFile('src/components/InsightDrawer.jsx');
const cardContent = readFile('src/components/billing/ShadowBreakdownCard.jsx');

describe('InsightDrawer — Source Guards', () => {
  it('ne calcule AUCUN KPI ou montant', () => {
    expect(drawerContent).toBeTruthy();
    expect(drawerContent).not.toMatch(/ecart.*\/.*\*\s*100/);
    expect(drawerContent).not.toMatch(/delta.*\/.*\*\s*100/);
    expect(drawerContent).not.toMatch(/\*\s*0\.02569/);
    expect(drawerContent).not.toMatch(/\*\s*0\.0569/);
    expect(drawerContent).not.toMatch(/\*\s*0\.0795/);
    expect(drawerContent).not.toMatch(/\*\s*0\.2193/);
  });

  it("n'affiche jamais 'Reconstitution complète' en dur", () => {
    expect(drawerContent).not.toMatch(/["']Reconstitution complète["']/);
  });

  it('gère les valeurs null', () => {
    const hasNullCheck =
      drawerContent.includes('!== null') ||
      drawerContent.includes('!= null') ||
      drawerContent.includes('== null') ||
      drawerContent.includes('=== null') ||
      drawerContent.includes('missing_price');
    expect(hasNullCheck).toBe(true);
  });

  it('contient une section identification facture (P0.1)', () => {
    expect(drawerContent).toMatch(/InvoiceIdentCard|invoice_identification|invoice_number/);
  });

  it('contient un composant reconstitution banner (P0.3)', () => {
    expect(drawerContent).toMatch(
      /ReconstitutionBanner|reconstitution_status|reconstitution_label/
    );
  });

  it('contient un badge confiance (P0.4)', () => {
    expect(drawerContent).toMatch(/confidence_label|confidence_rationale/);
  });

  it('affiche TVA non détaillée quand null (P1.1)', () => {
    expect(drawerContent).toMatch(/TVA non détaillée/);
  });

  it('a une note "— = non disponible" sous le tableau (P1.6)', () => {
    expect(drawerContent).toMatch(/non disponible/);
  });

  it('a des CTAs actionnables (P1.8)', () => {
    expect(drawerContent).toMatch(/Créer une action/);
    expect(drawerContent).toMatch(/Contester/);
  });

  it('a une section debug technique collapsible (P1.7)', () => {
    expect(drawerContent).toMatch(/Debug technique/);
    expect(drawerContent).toMatch(/<details/);
  });
});

describe('ShadowBreakdownCard — Source Guards', () => {
  it('ne calcule AUCUN KPI ou montant', () => {
    expect(cardContent).toBeTruthy();
    expect(cardContent).not.toMatch(/ecart.*\/.*\*\s*100/);
    expect(cardContent).not.toMatch(/delta.*\/.*\*\s*100/);
    expect(cardContent).not.toMatch(/\*\s*0\.02569/);
    expect(cardContent).not.toMatch(/\*\s*0\.0569/);
    expect(cardContent).not.toMatch(/\*\s*0\.0795/);
    expect(cardContent).not.toMatch(/\*\s*0\.2193/);
  });

  it('gère le statut missing_price (P0.2)', () => {
    expect(cardContent).toMatch(/missing_price/);
    expect(cardContent).toMatch(/Prix manquant/);
  });

  it('gère le statut informational (CEE P1.4)', () => {
    expect(cardContent).toMatch(/informational/);
    expect(cardContent).toMatch(/Pour info/);
  });

  it('affiche formula et source_ref par composante', () => {
    expect(cardContent).toMatch(/formula/);
    expect(cardContent).toMatch(/source_ref/);
  });

  it('affiche prorata_display', () => {
    expect(cardContent).toMatch(/prorata_display/);
  });

  it('a un CTA pour compléter les données (P1.6)', () => {
    expect(cardContent).toMatch(/Compléter les données/);
  });

  it("utilise reconstitution_label de l'API", () => {
    expect(cardContent).toMatch(/reconstitution_label/);
  });
});
