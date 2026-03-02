/**
 * PROMEOS — E2E Operations happy path
 * Validates: conformite tabs, compliance redirect, anomalies centre, drawer creation.
 * Requires: backend on :8001, frontend on :5173, demo data seeded.
 */
import { test, expect } from '@playwright/test';

async function login(page) {
  await page.goto('/login');
  await page.fill('input[type="email"]', 'sophie@atlas.demo');
  await page.fill('input[type="password"]', 'demo2024');
  await page.click('button[type="submit"]');
  await page.waitForURL((url) => !url.pathname.includes('/login'), {
    timeout: 10_000,
  });
}

test.describe('Operations happy path', () => {
  test('/conformite loads with 4 tabs', async ({ page }) => {
    await login(page);
    await page.goto('/conformite');
    await page.waitForTimeout(3000);

    const body = await page.textContent('body');
    expect(body).not.toContain('Something went wrong');

    // 4 tabs should be visible
    await expect(page.locator('text=Obligations')).toBeVisible({ timeout: 10_000 });
    await expect(page.locator('text=Données')).toBeVisible();
    await expect(page.locator('text=Recommandations')).toBeVisible();
    await expect(page.locator('text=Preuves')).toBeVisible();
  });

  test('/compliance redirects to /conformite', async ({ page }) => {
    await login(page);
    await page.goto('/compliance');
    await page.waitForURL(/\/conformite/, { timeout: 10_000 });
    expect(page.url()).toContain('/conformite');
  });

  test('/compliance/pipeline loads correctly', async ({ page }) => {
    await login(page);
    await page.goto('/compliance/pipeline');
    await page.waitForTimeout(3000);

    const body = await page.textContent('body');
    expect(body).not.toContain('Something went wrong');
    expect(body.length).toBeGreaterThan(100);
  });

  test('/anomalies loads with Centre d\'actions', async ({ page }) => {
    await login(page);
    await page.goto('/anomalies');
    await page.waitForTimeout(3000);

    const body = await page.textContent('body');
    expect(body).not.toContain('Something went wrong');
    await expect(page.locator('text=Centre d\'actions')).toBeVisible({ timeout: 10_000 });
  });

  test('Conformite — create action opens unified drawer', async ({ page }) => {
    await login(page);
    await page.goto('/conformite');
    await page.waitForTimeout(3000);

    // Switch to Recommandations tab (where "Créer action" CTA lives)
    const recoTab = page.locator('text=Recommandations');
    await expect(recoTab).toBeVisible({ timeout: 10_000 });
    await recoTab.click();
    await page.waitForTimeout(1000);

    // Look for a "Créer action" button (may or may not be visible depending on data)
    const cta = page.locator('text=Créer action').first();
    const ctaVisible = await cta.isVisible().catch(() => false);
    if (!ctaVisible) {
      test.skip(true, 'No "Créer action" CTA visible — no actionable findings in demo data');
      return;
    }

    await cta.click();
    // Drawer should open with "Créer une action" title
    await expect(page.locator('text=Créer une action')).toBeVisible({ timeout: 5_000 });
  });

  test('Anomalies — create action opens unified drawer (not modal)', async ({ page }) => {
    await login(page);
    await page.goto('/anomalies');
    await page.waitForTimeout(3000);

    const cta = page.locator('text=Créer action').first();
    const ctaVisible = await cta.isVisible().catch(() => false);
    if (!ctaVisible) {
      test.skip(true, 'No "Créer action" CTA visible — no anomalies in demo data');
      return;
    }

    await cta.click();
    // Should open the unified drawer, NOT the old AnomalyActionModal
    await expect(page.locator('text=Créer une action')).toBeVisible({ timeout: 5_000 });
  });

  test('/actions page loads', async ({ page }) => {
    await login(page);
    await page.goto('/actions');
    await page.waitForTimeout(3000);

    const body = await page.textContent('body');
    expect(body).not.toContain('Something went wrong');
    expect(body.length).toBeGreaterThan(100);
  });
});
