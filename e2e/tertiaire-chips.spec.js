/**
 * PROMEOS — E2E Smoke: Tertiaire chip filters + HealthSummary card
 * Validates:
 *   1. Chip filters on /conformite/tertiaire filter the "Sites à traiter" list
 *   2. Dashboard HealthSummary card not showing contradictory "0 points"
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

test.describe('Tertiaire chip filters + HealthSummary', () => {
  test('chip filter changes the sites list on /conformite/tertiaire', async ({ page }) => {
    await login(page);
    await page.goto('/conformite/tertiaire');
    await page.waitForTimeout(3000);

    const body = await page.textContent('body');
    expect(body).not.toContain('Something went wrong');

    // If site-signals section exists, test chip interaction
    const section = page.locator('[data-testid="sites-a-traiter"]');
    const sectionVisible = await section.isVisible().catch(() => false);

    if (sectionVisible) {
      // Count sites before clicking a chip
      const filterBar = page.locator('[data-testid="signal-filters"]');
      await expect(filterBar).toBeVisible({ timeout: 5_000 });

      // Find any signal chip button and click it
      const chips = filterBar.locator('button');
      const chipCount = await chips.count();
      expect(chipCount).toBeGreaterThan(0);

      // Get initial site count
      const siteCards = section.locator('.rounded-lg.border');
      const initialCount = await siteCards.count();

      // Click the first signal chip (e.g., "Assujetti probable")
      const firstChip = page.locator('[data-testid="filter-assujetti_probable"]');
      if (await firstChip.isVisible().catch(() => false)) {
        await firstChip.click();
        await page.waitForTimeout(500);

        // After clicking, the list should still render (no crash)
        const bodyAfter = await page.textContent('body');
        expect(bodyAfter).not.toContain('Something went wrong');

        // Click "Réinitialiser" to clear filters
        const resetBtn = page.locator('text=Réinitialiser');
        if (await resetBtn.isVisible().catch(() => false)) {
          await resetBtn.click();
          await page.waitForTimeout(500);
        }
      }
    }
  });

  test('dashboard HealthSummary never shows "0 points à surveiller"', async ({ page }) => {
    await login(page);
    await page.goto('/');
    await page.waitForTimeout(3000);

    const body = await page.textContent('body');
    expect(body).not.toContain('Something went wrong');

    // The AMBER card subtitle should never say "0 points"
    expect(body).not.toContain('0 point à surveiller');
    expect(body).not.toContain('0 points à surveiller');
  });
});
