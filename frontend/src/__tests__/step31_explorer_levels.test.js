/**
 * PROMEOS — Step 31 source-guard : Explorer 3 niveaux
 */
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { join } from 'path';

const explorerPath = join(__dirname, '..', 'pages', 'ConsumptionExplorerPage.jsx');
const src = readFileSync(explorerPath, 'utf-8');

describe('ConsumptionExplorerPage — 3 niveaux', () => {
  it('defines TABS_ESSENTIAL', () => {
    expect(src).toMatch(/TABS_ESSENTIAL\s*=/);
  });

  it('defines TABS_ANALYSIS', () => {
    expect(src).toMatch(/TABS_ANALYSIS\s*=/);
  });

  it('defines TABS_SPECIALIST', () => {
    expect(src).toMatch(/TABS_SPECIALIST\s*=/);
  });

  it('TABS_ESSENTIAL contains timeseries and insights', () => {
    // Extract TABS_ESSENTIAL block
    const match = src.match(/TABS_ESSENTIAL\s*=\s*\[([\s\S]*?)\];/);
    expect(match).not.toBeNull();
    expect(match[1]).toMatch(/timeseries/);
    expect(match[1]).toMatch(/insights/);
  });

  it('TABS_ANALYSIS contains signature, meteo, tunnel, targets', () => {
    const match = src.match(/TABS_ANALYSIS\s*=\s*\[([\s\S]*?)\];/);
    expect(match).not.toBeNull();
    expect(match[1]).toMatch(/signature/);
    expect(match[1]).toMatch(/meteo/);
    expect(match[1]).toMatch(/tunnel/);
    expect(match[1]).toMatch(/targets/);
  });

  it('TABS_SPECIALIST contains hphc and gas', () => {
    const match = src.match(/TABS_SPECIALIST\s*=\s*\[([\s\S]*?)\];/);
    expect(match).not.toBeNull();
    expect(match[1]).toMatch(/hphc/);
    expect(match[1]).toMatch(/gas/);
  });

  it('has showAdvanced state toggle', () => {
    expect(src).toMatch(/showAdvanced/);
    expect(src).toMatch(/setShowAdvanced/);
  });

  it('computes visibleTabs from mode + showAdvanced', () => {
    expect(src).toMatch(/visibleTabs/);
  });

  it('renders visual separators between levels', () => {
    expect(src).toMatch(/isAnalysisStart/);
    expect(src).toMatch(/isSpecialistStart/);
  });

  it('has Plus/Moins toggle button', () => {
    expect(src).toMatch(/Moins/);
    expect(src).toMatch(/Plus/);
  });

  it('auto-expands specialist level when active tab is specialist', () => {
    expect(src).toMatch(/specialistKeys.*has.*activeTab/);
  });

  it('Classic mode shows only Essential tabs', () => {
    expect(src).toMatch(/isClassic.*return TABS_ESSENTIAL/);
  });

  it('preserves TAB_CONFIG for backward compat', () => {
    expect(src).toMatch(/TAB_CONFIG\s*=.*TABS_ESSENTIAL.*TABS_ANALYSIS.*TABS_SPECIALIST/);
  });
});
