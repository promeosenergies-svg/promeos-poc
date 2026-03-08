/**
 * V117 Anomaly ↔ Action Contract — Source-guard tests
 * readFileSync + regex: no DOM, no mocks.
 */
import { readFileSync } from 'fs';
import { resolve } from 'path';
import { describe, it, expect } from 'vitest';

const root = resolve(__dirname, '../../../');
function src(relPath) {
  return readFileSync(resolve(root, relPath), 'utf-8');
}

describe('V117 Anomaly ↔ Action — AnomaliesPage', () => {
  const code = src('src/pages/AnomaliesPage.jsx');

  it('imports getAnomalyStatuses API', () => {
    expect(code).toMatch(/getAnomalyStatuses/);
    expect(code).toContain('getAnomalyStatuses');
  });

  it('imports dismissAnomaly API', () => {
    expect(code).toMatch(/dismissAnomaly/);
    expect(code).toContain('dismissAnomaly');
  });

  it('has context-aware openTarget function', () => {
    expect(code).toMatch(/openTarget/);
    expect(code).toMatch(/bill-intel/);
    expect(code).toMatch(/conformite/);
    expect(code).toMatch(/patrimoine/);
  });

  it('has context-aware getOpenLabel function', () => {
    expect(code).toMatch(/getOpenLabel/);
    expect(code).toMatch(/Ouvrir facture/);
    expect(code).toMatch(/Ouvrir BACS/);
    expect(code).toMatch(/Corriger donn/);
  });

  it('shows dismiss reasons in UI (faux positif, connu, hors perimetre, doublon)', () => {
    expect(code).toMatch(/Faux positif/);
    expect(code).toMatch(/connu/i);
    expect(code).toMatch(/Hors p/i);
    expect(code).toMatch(/Doublon/i);
  });

  it('uses toast for feedback after dismiss', () => {
    expect(code).toMatch(/useToast/);
    expect(code).toMatch(/toast\(/);
  });

  it('fetches anomaly statuses on load', () => {
    expect(code).toMatch(/getAnomalyStatuses/);
    expect(code).toMatch(/anomalyStatuses/);
  });

  it('shows linked/dismissed status badges', () => {
    expect(code).toMatch(/Ignor[eé]e/);
    expect(code).toMatch(/Voir action/);
  });
});

describe('V117 Anomaly ↔ Action — ActionsPage filter', () => {
  const code = src('src/pages/ActionsPage.jsx');

  it('reads action_id from searchParams', () => {
    expect(code).toMatch(/searchParams\.get\(['"]action_id['"]\)/);
  });

  it('reads linked_anomaly from searchParams', () => {
    expect(code).toMatch(/searchParams\.get\(['"]linked_anomaly['"]\)/);
  });

  it('filters by filterActionId', () => {
    expect(code).toMatch(/filterActionId/);
  });

  it('filters by filterLinkedAnomaly using anomaly_links', () => {
    expect(code).toMatch(/filterLinkedAnomaly/);
    expect(code).toMatch(/anomaly_links/);
  });
});

describe('V117 Anomaly ↔ Action — ROISummaryBar', () => {
  const code = src('src/components/ROISummaryBar.jsx');

  it('shows tooltip when realized=0', () => {
    expect(code).toMatch(/noRealized|total_realized_eur\s*===?\s*0/);
    expect(code).toMatch(/title=/);
    expect(code).toMatch(/Aucun gain/i);
  });

  it('displays ROI dash when no realized gains', () => {
    expect(code).toMatch(/noRealized.*—|'—'/);
  });
});

describe('V117 Anomaly ↔ Action — API service', () => {
  const code = src('src/services/api.js');

  it('exports createAnomalyActionLink', () => {
    expect(code).toMatch(/createAnomalyActionLink/);
  });

  it('exports dismissAnomaly', () => {
    expect(code).toMatch(/dismissAnomaly/);
  });

  it('exports getAnomalyStatuses', () => {
    expect(code).toMatch(/getAnomalyStatuses/);
  });
});
