/**
 * PROMEOS — Step 3: No Legacy CompliancePage
 * Vérifie que /compliance redirige vers /conformite et que CompliancePage
 * n'est plus routée ni dans la navigation.
 */
import { describe, it, expect } from 'vitest';
import { readFileSync, existsSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));

function readSrc(relPath) {
  return readFileSync(join(__dirname, '..', relPath), 'utf-8');
}

// ── A. App.jsx routing ──────────────────────────────────────────────────────

describe('Step3 — App.jsx CompliancePage removed from routing', () => {
  const src = readSrc('App.jsx');

  it('does not import CompliancePage as a routed component', () => {
    // SiteCompliancePage is OK — it's the V68 page, not legacy
    // But "CompliancePage" (without "Site" prefix) should NOT be lazy-imported
    expect(src).not.toMatch(/lazy\(\(\)\s*=>\s*import\('\.\/pages\/CompliancePage'\)\)/);
  });

  it('does not render CompliancePage in a Route element', () => {
    // No <Route ... element={<CompliancePage />} />
    expect(src).not.toMatch(/element=\{<CompliancePage\s/);
  });

  it('/compliance redirects to /conformite', () => {
    // Should have: <Route path="/compliance" element={<Navigate to="/conformite" replace />} />
    const lines = src.split('\n');
    const complianceLine = lines.find((l) => l.includes('path="/compliance"') && !l.includes('/compliance/'));
    expect(complianceLine).toBeDefined();
    expect(complianceLine).toMatch(/Navigate.*conformite|conformite.*Navigate/i);
  });
});

// ── B. NavRegistry — no CompliancePage reference ────────────────────────────

describe('Step3 — NavRegistry no legacy link', () => {
  const src = readSrc('layout/NavRegistry.js');

  it('does not reference CompliancePage component', () => {
    expect(src).not.toMatch(/CompliancePage/);
  });

  it('does not have a nav entry pointing to bare /compliance', () => {
    // /compliance/pipeline is fine (V68), but bare "to: '/compliance'" would be legacy
    expect(src).not.toMatch(/to:\s*['"]\/compliance['"]\s*[,}]/);
  });
});

// ── C. CommandPalette — no CompliancePage action ────────────────────────────

describe('Step3 — CommandPalette no CompliancePage', () => {
  const palettePath = join(__dirname, '..', 'ui', 'CommandPalette.jsx');

  it('CommandPalette does not reference CompliancePage', () => {
    if (!existsSync(palettePath)) return; // skip if no CommandPalette
    const src = readFileSync(palettePath, 'utf-8');
    expect(src).not.toMatch(/CompliancePage/);
  });
});

// ── D. CompliancePage.jsx is not imported anywhere (except tests) ───────────

describe('Step3 — CompliancePage orphan check', () => {
  it('App.jsx does not lazy-import CompliancePage (without Site prefix)', () => {
    const src = readSrc('App.jsx');
    // Only SiteCompliancePage should be imported
    const imports = src.split('\n').filter((l) => l.includes("import('./pages/CompliancePage')"));
    expect(imports).toHaveLength(0);
  });
});
