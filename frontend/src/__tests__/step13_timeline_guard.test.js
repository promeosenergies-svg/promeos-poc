/**
 * Step 13 — C5 : Timeline reglementaire
 * Source-guard tests for RegulatoryTimeline component and integration.
 */
import { describe, it, expect } from 'vitest';
import fs from 'fs';

describe('Step 13 — RegulatoryTimeline component', () => {
  it('RegulatoryTimeline.jsx exists', () => {
    expect(fs.existsSync('src/components/compliance/RegulatoryTimeline.jsx')).toBe(true);
  });

  it('RegulatoryTimeline has passed/upcoming/future status handling', () => {
    const src = fs.readFileSync('src/components/compliance/RegulatoryTimeline.jsx', 'utf8');
    expect(src).toContain('passed');
    expect(src).toContain('upcoming');
    expect(src).toContain('future');
  });

  it("RegulatoryTimeline has Aujourd'hui marker", () => {
    const src = fs.readFileSync('src/components/compliance/RegulatoryTimeline.jsx', 'utf8');
    expect(src).toContain("Aujourd'hui");
  });

  it('RegulatoryTimeline is responsive (hidden md:block pattern)', () => {
    const src = fs.readFileSync('src/components/compliance/RegulatoryTimeline.jsx', 'utf8');
    expect(src).toContain('hidden md:block');
    expect(src).toContain('md:hidden');
  });

  it('RegulatoryTimeline uses Explain for glossary', () => {
    const src = fs.readFileSync('src/components/compliance/RegulatoryTimeline.jsx', 'utf8');
    expect(src).toContain('timeline_reglementaire');
    expect(src).toContain('Explain');
  });
});

describe('Step 13 — ConformitePage integration', () => {
  it('ConformitePage imports RegulatoryTimeline', () => {
    const src = fs.readFileSync('src/pages/ConformitePage.jsx', 'utf8');
    expect(src).toContain('RegulatoryTimeline');
  });

  it('ConformitePage fetches timeline data', () => {
    const src = fs.readFileSync('src/pages/ConformitePage.jsx', 'utf8');
    expect(src).toContain('getComplianceTimeline');
  });
});

describe('Step 13 — Cockpit integration', () => {
  it('Cockpit has next_deadline or echeance', () => {
    const src = fs.readFileSync('src/pages/Cockpit.jsx', 'utf8');
    expect(
      src.includes('nextDeadline') || src.includes('next_deadline') || src.includes('echeance')
    ).toBe(true);
  });

  it('Cockpit fetches timeline', () => {
    const src = fs.readFileSync('src/pages/Cockpit.jsx', 'utf8');
    expect(src).toContain('getComplianceTimeline');
  });

  it('Cockpit has "Prochaine échéance" text', () => {
    const src = fs.readFileSync('src/pages/Cockpit.jsx', 'utf8');
    expect(src).toMatch(/Prochaine [eé]ch[eé]ance/);
  });

  it('Cockpit navigates to /conformite', () => {
    const src = fs.readFileSync('src/pages/Cockpit.jsx', 'utf8');
    expect(src).toContain("'/conformite'");
  });
});

describe('Step 13 — Glossary & API', () => {
  it('glossary.js has timeline_reglementaire', () => {
    const src = fs.readFileSync('src/ui/glossary.js', 'utf8');
    expect(src).toContain('timeline_reglementaire');
  });

  it('api.js has getComplianceTimeline', () => {
    const src = fs.readFileSync('src/services/api.js', 'utf8');
    expect(src).toContain('getComplianceTimeline');
    expect(src).toContain('/compliance/timeline');
  });
});
