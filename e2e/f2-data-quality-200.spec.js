/**
 * PROMEOS — F2: Data Quality Endpoints Return 200
 * Sprint F — Verify /api/data-quality/ endpoints no longer return 500.
 */
import { test, expect } from '@playwright/test';
import {
  login, attachConsoleMonitor, BACKEND_URL,
} from './helpers.js';

test.describe('F2 — Data Quality Endpoints', () => {
  let consoleMonitor;

  test.beforeEach(async ({ page }) => {
    consoleMonitor = attachConsoleMonitor(page);
    await login(page);
  });

  test.afterEach(async () => {
    const errors = consoleMonitor.getErrors();
    expect(errors.length, `Console errors: ${errors.join(' | ')}`).toBe(0);
  });

  test('GET /api/data-quality/freshness returns 200 for all demo sites', async ({ page }) => {
    const manifest = await (await page.request.get(`${BACKEND_URL}/api/demo/manifest`)).json();

    for (const sid of manifest.all_site_ids) {
      const res = await page.request.get(`${BACKEND_URL}/api/data-quality/freshness/${sid}`);
      expect(res.status(), `freshness/${sid} should return 200`).toBe(200);
      const data = await res.json();
      expect(data.status).toMatch(/^(fresh|recent|stale|expired|no_data)$/);
      expect(typeof data.staleness_days).toBe('number');
    }
  });

  test('GET /api/data-quality/site returns 200 for all demo sites', async ({ page }) => {
    const manifest = await (await page.request.get(`${BACKEND_URL}/api/demo/manifest`)).json();

    for (const sid of manifest.all_site_ids) {
      const res = await page.request.get(`${BACKEND_URL}/api/data-quality/site/${sid}`);
      expect(res.status(), `site/${sid} should return 200`).toBe(200);
      const data = await res.json();
      expect(typeof data.score).toBe('number');
      expect(data.score).toBeGreaterThanOrEqual(0);
      expect(data.score).toBeLessThanOrEqual(100);
      expect(data.grade).toMatch(/^[A-F]$/);
    }
  });

  test('GET /api/data-quality/portfolio returns 200', async ({ page }) => {
    const res = await page.request.get(`${BACKEND_URL}/api/data-quality/portfolio?org_id=1`);
    expect(res.status()).toBe(200);
  });
});
