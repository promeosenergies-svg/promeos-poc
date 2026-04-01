import { describe, test, expect } from 'vitest';
import fs from 'fs';

describe('Nav patrimoine contextuel', () => {
  test('NavRegistry ne contient plus "Sites & Bâtiments"', () => {
    const content = fs.readFileSync('src/layout/NavRegistry.js', 'utf-8');
    expect(content).not.toMatch(/Sites\s*&?\s*B[âa]timents/i);
  });

  test('NavRegistry contient "Registre patrimonial"', () => {
    const content = fs.readFileSync('src/layout/NavRegistry.js', 'utf-8');
    expect(content).toMatch(/Registre patrimonial/);
  });

  test('NavRegistry contient un hint pour le registre', () => {
    const content = fs.readFileSync('src/layout/NavRegistry.js', 'utf-8');
    expect(content).toMatch(/hint.*fiche/i);
  });

  test('activeSite.js existe', () => {
    expect(fs.existsSync('src/utils/activeSite.js')).toBe(true);
  });

  test('NavPanel référence activeSite', () => {
    const content = fs.readFileSync('src/layout/NavPanel.jsx', 'utf-8');
    expect(content).toMatch(/activeSite|getActiveSite/);
  });

  test('Site360 appelle setActiveSite', () => {
    const content = fs.readFileSync('src/pages/Site360.jsx', 'utf-8');
    expect(content).toContain('setActiveSite');
  });

  test('NavPanel a un bouton fermer (clearActiveSite)', () => {
    const content = fs.readFileSync('src/layout/NavPanel.jsx', 'utf-8');
    expect(content).toContain('clearActiveSite');
  });

  test('NavPanel affiche dot statut coloré', () => {
    const content = fs.readFileSync('src/layout/NavPanel.jsx', 'utf-8');
    expect(content).toMatch(
      /conforme.*#0F6E56|non_conforme.*#E24B4A|a_risque.*#E24B4A|a_evaluer.*#BA7517/
    );
  });

  test('NavPanel navigue vers /sites/:id au clic', () => {
    const content = fs.readFileSync('src/layout/NavPanel.jsx', 'utf-8');
    expect(content).toMatch(/navigate.*\/sites\//);
  });
});
