/**
 * NonApplicableLabel.test.js — Sprint C-2 Phase 4.5a
 *
 * Tests structurels (env=node, pas de DOM) :
 * - export default + structure props
 * - 3 variants reconnus (default/compact/large)
 * - tooltip + aria-label accessible
 *
 * Pattern repo : readFileSync + import + regex.
 */
import { readFileSync } from 'fs';
import { dirname, resolve } from 'path';
import { fileURLToPath } from 'url';
import { describe, it, expect } from 'vitest';

import NonApplicableLabel from '../components/NonApplicableLabel';

const __dirname = dirname(fileURLToPath(import.meta.url));
const componentSrc = readFileSync(
  resolve(__dirname, '../components/NonApplicableLabel.jsx'),
  'utf8'
);

describe('NonApplicableLabel — structure', () => {
  it('exporte default un composant React', () => {
    expect(NonApplicableLabel).toBeDefined();
    expect(typeof NonApplicableLabel).toBe('function');
  });

  it('accepte 3 variants : default | compact | large', () => {
    expect(componentSrc).toContain("variant === 'compact'");
    expect(componentSrc).toContain("variant === 'large'");
    // default est la valeur par défaut
    expect(componentSrc).toMatch(/variant\s*=\s*['"]default['"]/);
  });

  it('expose tooltip configurable avec default explicite "Aucune obligation réglementaire active"', () => {
    expect(componentSrc).toContain('Aucune obligation réglementaire active');
    expect(componentSrc).toContain('title={tooltip}');
  });
});

describe('NonApplicableLabel — accessibilité', () => {
  it("inclut aria-label pour lecteurs d'écran", () => {
    expect(componentSrc).toContain('aria-label');
    expect(componentSrc).toMatch(/aria-label=\{`Non applicable\./);
  });

  it('texte affiché = "Non applicable" (terme français doctrine PROMEOS)', () => {
    expect(componentSrc).toContain('Non applicable');
  });

  it('utilise convention design system text-gray-400 italic (cohérent existant)', () => {
    // Cf. ActionDetailDrawer.jsx, DossierPrintView.jsx, FreshnessIndicator.jsx,
    // InsightDrawer.jsx — pattern "text-gray-400 italic" pour textes secondaires.
    expect(componentSrc).toContain('text-gray-400');
    expect(componentSrc).toContain('italic');
  });
});
