/**
 * PROMEOS — Bloc D.2 Data Freshness — Source Guards
 * Vérifie : FreshnessIndicator, glossary, API, intégrations Site360 + MonitoringPage.
 */
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));

function readSrc(relPath) {
  return readFileSync(join(__dirname, '..', relPath), 'utf-8');
}

// ── A. FreshnessIndicator component ────────────────────────────────────

describe('D.2 — FreshnessIndicator component', () => {
  const src = readSrc('components/FreshnessIndicator.jsx');

  it('exports FreshnessIndicator as default', () => {
    expect(src).toContain('export default function FreshnessIndicator');
  });

  it('accepts freshness, size, showBanner, onImport props', () => {
    expect(src).toContain('freshness');
    expect(src).toContain('size');
    expect(src).toContain('showBanner');
    expect(src).toContain('onImport');
  });

  it('has sm and md size variants', () => {
    expect(src).toContain("size === 'sm'");
  });

  it('has STATUS_CONFIG with 5 statuses', () => {
    expect(src).toContain("fresh:");
    expect(src).toContain("recent:");
    expect(src).toContain("stale:");
    expect(src).toContain("expired:");
    expect(src).toContain("no_data:");
  });

  it('imports Explain for popover', () => {
    expect(src).toContain('Explain');
    expect(src).toContain('freshness');
  });

  it('has data-testid for sm and md', () => {
    expect(src).toContain('freshness-sm');
    expect(src).toContain('freshness-md');
  });

  it('has expired banner with data-testid', () => {
    expect(src).toContain('freshness-expired-banner');
  });

  it('shows last_reading and last_invoice in popover', () => {
    expect(src).toContain('last_reading');
    expect(src).toContain('last_invoice');
    expect(src).toContain('Dernier relevé');
    expect(src).toContain('Dernière facture');
  });

  it('has import CTA button', () => {
    expect(src).toContain('Importer des données');
  });

  it('renders staleness_days', () => {
    expect(src).toContain('staleness_days');
  });
});

// ── B. Glossary ────────────────────────────────────────────────────────

describe('D.2 — Glossary freshness entry', () => {
  const src = readSrc('ui/glossary.js');

  it('has freshness entry', () => {
    expect(src).toContain("freshness:");
  });

  it('freshness entry has term and short', () => {
    expect(src).toContain("Fraîcheur des données");
  });
});

// ── C. API function ────────────────────────────────────────────────────

describe('D.2 — API function', () => {
  const src = readSrc('services/api.js');

  it('exports getSiteFreshness', () => {
    expect(src).toContain('getSiteFreshness');
  });

  it('calls /data-quality/freshness/ endpoint', () => {
    expect(src).toContain('/data-quality/freshness/');
  });

  it('uses _cachedGet', () => {
    const lines = src.split('\n').filter((l) => l.includes('data-quality/freshness'));
    lines.forEach((line) => {
      expect(line).toContain('_cachedGet');
    });
  });
});

// ── D. Site360 integration ─────────────────────────────────────────────

describe('D.2 — Site360 freshness integration', () => {
  const src = readSrc('pages/Site360.jsx');

  it('imports FreshnessIndicator', () => {
    expect(src).toContain('FreshnessIndicator');
  });

  it('imports getSiteFreshness', () => {
    expect(src).toContain('getSiteFreshness');
  });

  it('has freshness state', () => {
    expect(src).toContain('setFreshness');
  });

  it('renders FreshnessIndicator with size="sm"', () => {
    expect(src).toMatch(/FreshnessIndicator[\s\S]*?size="sm"/);
  });

  it('has expired banner with data-testid', () => {
    expect(src).toContain('freshness-expired-banner');
  });

  it('applies opacity on KPIs when expired', () => {
    expect(src).toContain("freshness.status === 'expired'");
  });
});

// ── E. MonitoringPage integration ──────────────────────────────────────

describe('D.2 — MonitoringPage freshness integration', () => {
  const src = readSrc('pages/MonitoringPage.jsx');

  it('imports FreshnessIndicator', () => {
    expect(src).toContain('FreshnessIndicator');
  });

  it('imports getSiteFreshness', () => {
    expect(src).toContain('getSiteFreshness');
  });

  it('has siteFreshness state', () => {
    expect(src).toContain('siteFreshness');
    expect(src).toContain('setSiteFreshness');
  });

  it('renders FreshnessIndicator with size="sm"', () => {
    expect(src).toMatch(/FreshnessIndicator[\s\S]*?size="sm"/);
  });
});
