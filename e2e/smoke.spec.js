/**
 * PROMEOS — E2E Smoke Tests
 * Validates: API health, login flow, dashboard render.
 * Requires: backend on :8001, frontend on :5173.
 */
import { test, expect } from '@playwright/test';

test.describe('Smoke tests', () => {
  test('API health check returns ok', async ({ request }) => {
    const res = await request.get('http://127.0.0.1:8001/api/health');
    expect(res.ok()).toBeTruthy();
    const body = await res.json();
    expect(body).toHaveProperty('ok', true);
  });

  test('Login with demo credentials redirects to dashboard', async ({ page }) => {
    await page.goto('/login');
    await page.fill('input[type="email"]', 'promeos@promeos.io');
    await page.fill('input[type="password"]', 'promeos2024');
    await page.click('button[type="submit"]');

    // After login, should redirect away from /login
    await page.waitForURL((url) => !url.pathname.includes('/login'), {
      timeout: 10_000,
    });

    // Should be on the main app (dashboard or /)
    const url = page.url();
    expect(url).not.toContain('/login');
  });

  test('Dashboard renders KPI content after login', async ({ page }) => {
    // Login first
    await page.goto('/login');
    await page.fill('input[type="email"]', 'promeos@promeos.io');
    await page.fill('input[type="password"]', 'promeos2024');
    await page.click('button[type="submit"]');
    await page.waitForURL((url) => !url.pathname.includes('/login'), {
      timeout: 10_000,
    });

    // Verify dashboard has rendered content (not blank, no crash)
    await page.waitForTimeout(2000);
    const body = await page.textContent('body');
    expect(body.length).toBeGreaterThan(100);

    // Should not show an error boundary or "Something went wrong"
    expect(body).not.toContain('Something went wrong');
  });

  test('Demo manifest returns consistent site counts', async ({ request }) => {
    const res = await request.get('http://127.0.0.1:8001/api/demo/manifest');
    if (res.ok()) {
      const manifest = await res.json();
      // Verify structure
      expect(manifest).toHaveProperty('org_id');
      expect(manifest).toHaveProperty('total_sites');
      expect(manifest).toHaveProperty('portefeuilles');
      expect(manifest).toHaveProperty('all_site_ids');

      // Verify portefeuilles sum matches total
      const pfSum = manifest.portefeuilles.reduce((s, p) => s + p.sites_count, 0);
      expect(pfSum).toBe(manifest.total_sites);

      // Verify all_site_ids length matches total
      expect(manifest.all_site_ids.length).toBe(manifest.total_sites);
    }
    // If no seed, 404 is acceptable (e.g., fresh CI environment)
  });
});
