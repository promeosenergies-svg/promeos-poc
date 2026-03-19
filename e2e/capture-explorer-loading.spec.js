/**
 * PROMEOS — Capture Explorer Loading Grey Block
 * Records the loading transition when switching sites on the Explorer page.
 * Video + rapid screenshots capture the grey block skeleton for before/after comparison.
 */
import { test, expect } from '@playwright/test';
import { login, waitForPageReady, screenshot, SCREENSHOT_DIR } from './helpers.js';
import fs from 'fs';
import path from 'path';

test.use({ video: 'on' });

test.describe('Explorer loading capture', () => {
  test('capture grey block during site switch', async ({ page }) => {
    // Ensure screenshot directory exists
    const dir = path.join(SCREENSHOT_DIR);
    if (!fs.existsSync(dir)) {
      fs.mkdirSync(dir, { recursive: true });
    }

    // Login and navigate to explorer
    await login(page);
    await page.goto('/consommations/explorer');
    await waitForPageReady(page);

    // Wait for chart area to be visible (page fully loaded)
    await page.waitForTimeout(2000);

    // "Before" screenshot — stable state with current site
    await screenshot(page, 'explorer-loading-before');

    // Open site search dropdown
    const trigger = page.locator('[data-testid="sticky-sitesearch-trigger"]');
    await expect(trigger).toBeVisible({ timeout: 5000 });
    await trigger.click();

    // Wait for search panel to appear
    const panel = page.locator('[data-testid="sticky-sitesearch-panel"]');
    await expect(panel).toBeVisible({ timeout: 3000 });

    // Screenshot the open panel
    await screenshot(page, 'explorer-loading-panel-open');

    // Select the first available site in the dropdown
    const siteButton = panel.locator('button').first();
    await expect(siteButton).toBeVisible({ timeout: 3000 });
    await siteButton.click();

    // Rapid screenshots every 200ms for ~3s to catch loading state
    for (let i = 0; i < 15; i++) {
      await page.waitForTimeout(200);
      await screenshot(page, `explorer-loading-transition-${String(i).padStart(2, '0')}`);
    }

    // Wait for loading to settle
    await waitForPageReady(page);

    // Final "after" screenshot
    await screenshot(page, 'explorer-loading-after');
  });
});
