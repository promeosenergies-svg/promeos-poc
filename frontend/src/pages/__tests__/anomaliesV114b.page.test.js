/**
 * anomaliesV114b.page.test.js — V114b Centre d'actions UX Polish
 * Source-guard tests (readFileSync + regex) — no DOM, no mocks needed.
 * 6 groups.
 */
import { readFileSync } from 'fs';
import { resolve } from 'path';
import { describe, it, expect } from 'vitest';

const root = resolve(__dirname, '../../../');

function src(relPath) {
  return readFileSync(resolve(root, relPath), 'utf-8');
}

/* ── A. Page title ── */
describe("A. Page title — Centre d'actions", () => {
  const code = src('src/pages/AnomaliesPage.jsx');

  it('has title="Centre d\'actions" in PageShell', () => {
    expect(code).toMatch(/title="Centre d'actions"/);
  });

  it('has Anomalies tab', () => {
    expect(code).toMatch(/label:\s*'Anomalies'/);
  });

  it("has Plan d'actions tab", () => {
    expect(code).toMatch(/Plan d'actions/);
  });
});

/* ── B. URL reflète filtres ── */
describe('B. URL filter sync — useAnomalyFilters', () => {
  const hook = src('src/pages/useAnomalyFilters.js');

  it('uses useSearchParams from react-router-dom', () => {
    expect(hook).toMatch(/useSearchParams/);
  });

  it('defines fw filter key', () => {
    expect(hook).toMatch(/['"]fw['"]/);
  });

  it('defines sev filter key', () => {
    expect(hook).toMatch(/['"]sev['"]/);
  });

  it('defines site filter key', () => {
    expect(hook).toMatch(/['"]site['"]/);
  });

  it('defines q filter key', () => {
    expect(hook).toMatch(/['"]q['"]/);
  });

  it('calls searchParams.get to read URL params', () => {
    expect(hook).toMatch(/searchParams\.get\(/);
  });

  it('exports default function useAnomalyFilters', () => {
    expect(hook).toMatch(/export default function useAnomalyFilters/);
  });

  it('AnomaliesPage imports useAnomalyFilters', () => {
    const page = src('src/pages/AnomaliesPage.jsx');
    expect(page).toMatch(/import useAnomalyFilters/);
  });
});

/* ── C. Tri stable + indicateur ── */
describe('C. Smart sort — tri intelligent', () => {
  const code = src('src/pages/AnomaliesPage.jsx');

  it('sorts by estimated_risk_eur', () => {
    expect(code).toMatch(/estimated_risk_eur/);
  });

  it('sorts by priority_score', () => {
    expect(code).toMatch(/priority_score/);
  });

  it('has "Tri intelligent actif" badge', () => {
    expect(code).toMatch(/Tri intelligent actif/);
  });

  it('uses InfoTip component', () => {
    expect(code).toMatch(/InfoTip/);
  });

  it('InfoTip mentions risque EUR', () => {
    expect(code).toMatch(/risque EUR/);
  });
});

/* ── D. Evidence drawer — Pourquoi ? ── */
describe('D. Evidence drawer — Pourquoi ?', () => {
  const page = src('src/pages/AnomaliesPage.jsx');

  it('has "Pourquoi ?" button', () => {
    expect(page).toMatch(/Pourquoi \?/);
  });

  it('has data-testid="pourquoi-btn"', () => {
    expect(page).toMatch(/data-testid="pourquoi-btn"/);
  });

  it('imports EvidenceDrawer', () => {
    expect(page).toMatch(/EvidenceDrawer/);
  });

  it('imports buildAnomalyEvidence', () => {
    expect(page).toMatch(/buildAnomalyEvidence/);
  });

  it('anomalyEvidence.js calls buildEvidence', () => {
    const ev = src('src/pages/anomalyEvidence.js');
    expect(ev).toMatch(/import.*buildEvidence.*from.*evidence/);
    expect(ev).toMatch(/export function buildAnomalyEvidence/);
  });

  it('anomalyEvidence.js maps code to source label', () => {
    const ev = src('src/pages/anomalyEvidence.js');
    expect(ev).toMatch(/anom\.code/);
  });
});

/* ── E. Deep-link CTA ── */
describe('E. Deep-link CTA — URL priority over localStorage', () => {
  const hook = src('src/pages/useAnomalyFilters.js');

  it('reads searchParams.get in priority', () => {
    // URL params are read first (searchParams.get), then fallback to saved
    expect(hook).toMatch(/searchParams\.get\(/);
  });

  it('falls back to localStorage saved value', () => {
    expect(hook).toMatch(/saved\[key\]/);
  });

  it('uses replace: true to avoid history pollution', () => {
    expect(hook).toMatch(/replace:\s*true/);
  });
});

/* ── F. Filtres persistants — localStorage ── */
describe('F. Persistent filters — localStorage', () => {
  const hook = src('src/pages/useAnomalyFilters.js');

  it('uses promeos_anomaly_filters key', () => {
    expect(hook).toMatch(/promeos_anomaly_filters/);
  });

  it('calls localStorage.setItem', () => {
    expect(hook).toMatch(/localStorage\.setItem/);
  });

  it('calls localStorage.getItem', () => {
    expect(hook).toMatch(/localStorage\.getItem/);
  });

  it('calls localStorage.removeItem on reset', () => {
    expect(hook).toMatch(/localStorage\.removeItem/);
  });

  it('exports resetFilters', () => {
    expect(hook).toMatch(/resetFilters/);
  });
});
