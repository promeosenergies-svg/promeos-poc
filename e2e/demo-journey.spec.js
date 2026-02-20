/**
 * PROMEOS — E2E Demo Journey Tests
 * Validates: Cockpit → Patrimoine → Site360 drill-down flow.
 * Requires: backend on :8000, frontend on :5173, demo data seeded.
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

test.describe('Demo journey: Cockpit → Patrimoine → Site360', () => {
  test('Cockpit loads with executive content and no crash', async ({ page }) => {
    await login(page);
    await page.goto('/cockpit');

    // Wait for skeleton to resolve
    await page.waitForTimeout(3000);

    // Should display Vue exécutive title
    await expect(page.locator('text=Vue exécutive')).toBeVisible({ timeout: 10_000 });

    // Should have substantial content (not a blank page)
    const body = await page.textContent('body');
    expect(body.length).toBeGreaterThan(200);

    // No crash indicators
    expect(body).not.toContain('Something went wrong');
    expect(body).not.toContain('Site introuvable');
  });

  test('Full drill-down: Patrimoine drawer → Site360 shows consistent data', async ({ page }) => {
    await login(page);
    await page.goto('/patrimoine');

    // Wait for patrimoine table to render
    await expect(page.locator('text=Patrimoine')).toBeVisible({ timeout: 10_000 });
    await page.waitForTimeout(2000);

    const body = await page.textContent('body');
    expect(body).not.toContain('Something went wrong');

    // Click first site row to open drawer
    const firstRow = page.locator('table tbody tr').first();
    await expect(firstRow).toBeVisible({ timeout: 10_000 });
    await firstRow.click();

    // Drawer should open with "Voir la fiche site" action
    const ficheSiteBtn = page.locator('text=Voir la fiche site');
    await expect(ficheSiteBtn).toBeVisible({ timeout: 5_000 });
    await ficheSiteBtn.click();

    // Should navigate to /sites/:id
    await page.waitForURL(/\/sites\/\d+/, { timeout: 10_000 });
    await page.waitForTimeout(2000);

    // Site360 should render correctly
    const site360Body = await page.textContent('body');

    // Must NOT show "Site introuvable" (proves scope data is connected)
    expect(site360Body).not.toContain('Site introuvable');

    // Should show the expected tabs
    expect(site360Body).toContain('Résumé');
    expect(site360Body).toContain('Consommation');
    expect(site360Body).toContain('Conformité');
    expect(site360Body).toContain('Actions');

    // Should show the back button to Patrimoine
    expect(site360Body).toContain('Patrimoine');
  });
});
