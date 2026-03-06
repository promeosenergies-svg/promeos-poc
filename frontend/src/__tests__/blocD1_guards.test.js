/**
 * PROMEOS — Bloc D.1 Data Quality Score — Source Guards
 * Vérifie : DataQualityBadge, glossary, constants, API, intégrations 4 pages.
 */
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));

function readSrc(relPath) {
  return readFileSync(join(__dirname, '..', relPath), 'utf-8');
}

// ── A. DataQualityBadge component ──────────────────────────────────────

describe('D.1 — DataQualityBadge component', () => {
  const src = readSrc('components/DataQualityBadge.jsx');

  it('exports DataQualityBadge as default', () => {
    expect(src).toContain('export default function DataQualityBadge');
  });

  it('accepts score, dimensions, size props', () => {
    expect(src).toContain('score');
    expect(src).toContain('dimensions');
    expect(src).toContain('size');
  });

  it('has sm/md/lg size variants', () => {
    expect(src).toContain("size === 'sm'");
    expect(src).toContain("size === 'md'");
  });

  it('imports getDataQualityGrade from constants', () => {
    expect(src).toContain('getDataQualityGrade');
    expect(src).toContain("constants");
  });

  it('imports Explain for popover', () => {
    expect(src).toContain('Explain');
    expect(src).toContain('data_quality_score');
  });

  it('has popover with dimensions (DIM_LABELS)', () => {
    expect(src).toMatch(/Complétude/);
    expect(src).toMatch(/Fraîcheur/);
    expect(src).toMatch(/Précision/);
    expect(src).toMatch(/Cohérence/);
  });

  it('has recommendations section', () => {
    expect(src).toContain('recommendations');
    expect(src).toContain('Recommandations');
  });

  it('has data-testid for each size', () => {
    expect(src).toContain('dq-badge-sm');
    expect(src).toContain('dq-badge-md');
    expect(src).toContain('dq-badge-lg');
  });
});

// ── B. Glossary & Constants ────────────────────────────────────────────

describe('D.1 — Glossary & Constants', () => {
  it('glossary has data_quality_score entry', () => {
    const src = readSrc('ui/glossary.js');
    expect(src).toContain('data_quality_score');
    expect(src).toContain('Score qualité données');
  });

  it('constants has DATA_QUALITY_GRADES', () => {
    const src = readSrc('lib/constants.js');
    expect(src).toContain('DATA_QUALITY_GRADES');
  });

  it('constants has getDataQualityGrade function', () => {
    const src = readSrc('lib/constants.js');
    expect(src).toContain('export function getDataQualityGrade');
  });

  it('grade boundaries are A=85, B=70, C=50, D=30', () => {
    const src = readSrc('lib/constants.js');
    expect(src).toMatch(/A:\s*85/);
    expect(src).toMatch(/B:\s*70/);
    expect(src).toMatch(/C:\s*50/);
    expect(src).toMatch(/D:\s*30/);
  });
});

// ── C. API functions ───────────────────────────────────────────────────

describe('D.1 — API functions', () => {
  const src = readSrc('services/api.js');

  it('exports getDataQualityScore for site', () => {
    expect(src).toContain('getDataQualityScore');
    expect(src).toContain('/data-quality/site/');
  });

  it('exports getDataQualityPortfolio for org', () => {
    expect(src).toContain('getDataQualityPortfolio');
    expect(src).toContain('/data-quality/portfolio');
  });

  it('uses _cachedGet for both endpoints', () => {
    // Verify both D.1 endpoints use _cachedGet
    const lines = src.split('\n');
    const dqLines = lines.filter((l) => l.includes('data-quality/site') || l.includes('data-quality/portfolio'));
    dqLines.forEach((line) => {
      expect(line).toContain('_cachedGet');
    });
  });
});

// ── D. Site360 integration ─────────────────────────────────────────────

describe('D.1 — Site360 integration', () => {
  const src = readSrc('pages/Site360.jsx');

  it('imports DataQualityBadge', () => {
    expect(src).toContain('DataQualityBadge');
  });

  it('imports getDataQualityScore', () => {
    expect(src).toContain('getDataQualityScore');
  });

  it('fetches data quality for site', () => {
    expect(src).toContain('getDataQualityScore');
    expect(src).toContain('setDataQuality');
  });

  it('renders DataQualityBadge with size="md"', () => {
    expect(src).toMatch(/DataQualityBadge[\s\S]*?size="md"/);
  });

  it('has données partielles banner for score < 50', () => {
    expect(src).toContain('dq-partial-banner');
    expect(src).toContain('Données partielles');
  });

  it('applies opacity-60 on KPIs when score < 50', () => {
    expect(src).toContain('opacity-60');
  });
});

// ── E. Patrimoine integration ──────────────────────────────────────────

describe('D.1 — Patrimoine integration', () => {
  const src = readSrc('pages/Patrimoine.jsx');

  it('imports DataQualityBadge', () => {
    expect(src).toContain('DataQualityBadge');
  });

  it('imports getDataQualityPortfolio', () => {
    expect(src).toContain('getDataQualityPortfolio');
  });

  it('has dqMap state for portfolio scores', () => {
    expect(src).toContain('dqMap');
    expect(src).toContain('setDqMap');
  });

  it('has Qualité column header', () => {
    expect(src).toContain('Qualité');
  });

  it('renders DataQualityBadge with size="sm" in table', () => {
    expect(src).toMatch(/DataQualityBadge[\s\S]*?size="sm"/);
  });
});

// ── F. Cockpit integration ─────────────────────────────────────────────

describe('D.1 — Cockpit DataQualityWidget enriched', () => {
  const src = readSrc('pages/cockpit/DataQualityWidget.jsx');

  it('imports DataQualityBadge', () => {
    expect(src).toContain('DataQualityBadge');
  });

  it('imports getDataQualityPortfolio', () => {
    expect(src).toContain('getDataQualityPortfolio');
  });

  it('fetches portfolio data quality', () => {
    expect(src).toContain('dqPortfolio');
    expect(src).toContain('setDqPortfolio');
  });

  it('renders DataQualityBadge with avg_score', () => {
    expect(src).toContain('avg_score');
  });
});

// ── G. MonitoringPage integration ──────────────────────────────────────

describe('D.1 — MonitoringPage integration', () => {
  const src = readSrc('pages/MonitoringPage.jsx');

  it('imports DataQualityBadge', () => {
    expect(src).toContain('DataQualityBadge');
  });

  it('imports getDataQualityScore', () => {
    expect(src).toContain('getDataQualityScore');
  });

  it('fetches site data quality score', () => {
    expect(src).toContain('siteDq');
    expect(src).toContain('setSiteDq');
  });

  it('renders DataQualityBadge with size="sm"', () => {
    expect(src).toMatch(/DataQualityBadge[\s\S]*?size="sm"/);
  });
});
