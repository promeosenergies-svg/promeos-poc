/**
 * PROMEOS — Step 5: KPI Messaging Handlers + Integration
 * Vérifie les 3 nouveaux handlers (load_factor, night_ratio, weekend_ratio)
 * et leur intégration sur MonitoringPage.
 */
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));

function readSrc(relPath) {
  return readFileSync(join(__dirname, '..', relPath), 'utf-8');
}

// ── A. kpiMessaging.js — 3 new handlers exist ──────────────────────────────

describe('Step5 — kpiMessaging new handlers', () => {
  const src = readSrc('services/kpiMessaging.js');

  it('has load_factor handler', () => {
    expect(src).toMatch(/load_factor:\s*\(v/);
  });

  it('has night_ratio handler', () => {
    expect(src).toMatch(/night_ratio:\s*\(v/);
  });

  it('has weekend_ratio handler', () => {
    expect(src).toMatch(/weekend_ratio:\s*\(v/);
  });
});

// ── B. kpiMessaging.js — handler quality ────────────────────────────────────

describe('Step5 — kpiMessaging handler quality', () => {
  const src = readSrc('services/kpiMessaging.js');

  it('load_factor returns severity levels', () => {
    expect(src).toMatch(/load_factor[\s\S]*?severity:\s*'ok'/);
    expect(src).toMatch(/load_factor[\s\S]*?severity:\s*'warn'/);
    expect(src).toMatch(/load_factor[\s\S]*?severity:\s*'crit'/);
  });

  it('night_ratio returns severity levels', () => {
    expect(src).toMatch(/night_ratio[\s\S]*?severity:\s*'ok'/);
    expect(src).toMatch(/night_ratio[\s\S]*?severity:\s*'warn'/);
    expect(src).toMatch(/night_ratio[\s\S]*?severity:\s*'crit'/);
  });

  it('weekend_ratio returns severity levels', () => {
    expect(src).toMatch(/weekend_ratio[\s\S]*?severity:\s*'ok'/);
    expect(src).toMatch(/weekend_ratio[\s\S]*?severity:\s*'warn'/);
    expect(src).toMatch(/weekend_ratio[\s\S]*?severity:\s*'crit'/);
  });

  it('messages are in French', () => {
    expect(src).toMatch(/Facteur de charge/);
    expect(src).toMatch(/consommation nocturne/i);
    expect(src).toMatch(/consommation week-end/i);
  });
});

// ── C. Unit tests — getKpiMessage returns correct structure ─────────────────

describe('Step5 — getKpiMessage unit tests', () => {
  let getKpiMessage, SUPPORTED_KPIS;

  // Dynamic import to test actual logic
  it('imports successfully', async () => {
    const mod = await import('../services/kpiMessaging.js');
    getKpiMessage = mod.getKpiMessage;
    SUPPORTED_KPIS = mod.SUPPORTED_KPIS;
    expect(getKpiMessage).toBeDefined();
  });

  it('SUPPORTED_KPIS includes new handlers', async () => {
    const mod = await import('../services/kpiMessaging.js');
    expect(mod.SUPPORTED_KPIS).toContain('load_factor');
    expect(mod.SUPPORTED_KPIS).toContain('night_ratio');
    expect(mod.SUPPORTED_KPIS).toContain('weekend_ratio');
  });

  it('load_factor(60) returns ok', async () => {
    const mod = await import('../services/kpiMessaging.js');
    const msg = mod.getKpiMessage('load_factor', 60);
    expect(msg).not.toBeNull();
    expect(msg.severity).toBe('ok');
    expect(msg.simple).toBeTruthy();
    expect(msg.expert).toBeTruthy();
  });

  it('load_factor(15) returns crit', async () => {
    const mod = await import('../services/kpiMessaging.js');
    const msg = mod.getKpiMessage('load_factor', 15);
    expect(msg.severity).toBe('crit');
    expect(msg.action).toBeDefined();
  });

  it('night_ratio(0.10) returns ok', async () => {
    const mod = await import('../services/kpiMessaging.js');
    const msg = mod.getKpiMessage('night_ratio', 0.10);
    expect(msg.severity).toBe('ok');
  });

  it('night_ratio(0.50) returns crit', async () => {
    const mod = await import('../services/kpiMessaging.js');
    const msg = mod.getKpiMessage('night_ratio', 0.50);
    expect(msg.severity).toBe('crit');
  });

  it('weekend_ratio(0.10) returns ok', async () => {
    const mod = await import('../services/kpiMessaging.js');
    const msg = mod.getKpiMessage('weekend_ratio', 0.10);
    expect(msg.severity).toBe('ok');
  });

  it('weekend_ratio(0.50) returns crit', async () => {
    const mod = await import('../services/kpiMessaging.js');
    const msg = mod.getKpiMessage('weekend_ratio', 0.50);
    expect(msg.severity).toBe('crit');
  });

  it('null value returns neutral for all 3', async () => {
    const mod = await import('../services/kpiMessaging.js');
    for (const kpi of ['load_factor', 'night_ratio', 'weekend_ratio']) {
      const msg = mod.getKpiMessage(kpi, null);
      expect(msg.severity).toBe('neutral');
    }
  });
});

// ── D. MonitoringPage integration ───────────────────────────────────────────

describe('Step5 — MonitoringPage KPI message integration', () => {
  const src = readSrc('pages/MonitoringPage.jsx');

  it('imports getKpiMessage', () => {
    expect(src).toContain('getKpiMessage');
  });

  it('calls getKpiMessage for load_factor', () => {
    expect(src).toMatch(/getKpiMessage\(\s*['"]load_factor['"]/);
  });

  it('has data-testid for load_factor message', () => {
    expect(src).toContain('kpi-message-load-factor');
  });

  it('uses isExpert for message toggle', () => {
    // Verify expert mode is used for KPI messages
    expect(src).toContain('isExpert ? msg.expert : msg.simple');
  });
});
