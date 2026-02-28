/**
 * PROMEOS — Overlay Layering Smoke Tests
 * Validates that portal-based overlays are:
 *   - Rendered as direct children of <body> (createPortal)
 *   - Using position:fixed (not absolute — immune to stacking-context trapping)
 *   - Carrying z-index ≥ 120 (above sticky header z-40 and sidebar z-30)
 *   - Occupying visible screen space (not clipped behind other layers)
 *
 * Regressions guarded:
 *   1. ScopeSwitcher dropdown clipped on /consommations behind sticky+backdrop-blur
 *   2. InfoTip rendering empty black dots when content prop was undefined
 *
 * Requires: backend on :8000, frontend on :5173, demo data seeded.
 */
import { test, expect } from '@playwright/test';
import { fileURLToPath } from 'url';
import path from 'path';
import fs from 'fs';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const SCREENSHOTS = path.join(__dirname, 'screenshots');

async function login(page) {
  await page.goto('/login');
  await page.fill('input[type="email"]', 'sophie@atlas.demo');
  await page.fill('input[type="password"]', 'demo2024');
  await page.click('button[type="submit"]');
  await page.waitForURL((url) => !url.pathname.includes('/login'), {
    timeout: 10_000,
  });
}

test.beforeAll(() => {
  fs.mkdirSync(SCREENSHOTS, { recursive: true });
});

test.describe('Overlay layering — portal + z-index regression', () => {

  // ── Test 1: ScopeSwitcher dropdown ──────────────────────────────────────────
  test(
    'Consommations explorer: ScopeSwitcher dropdown is portaled, position:fixed, z≥120',
    async ({ page }) => {
      await login(page);
      await page.goto('/consommations');

      // Wait for the page to stabilize (data fetch + React hydration)
      await page.waitForTimeout(2000);

      // Locate the ScopeSwitcher trigger (the scope pill in the header)
      const trigger = page.locator('button[aria-haspopup="listbox"]');
      await expect(trigger).toBeVisible({ timeout: 8_000 });

      // Open the dropdown
      await trigger.click();

      // Dropdown must appear
      const listbox = page.locator('[role="listbox"]');
      await expect(listbox).toBeVisible({ timeout: 5_000 });

      // ── Portal assertion: must be a direct child of <body> ─────────────────
      const parentTag = await listbox.evaluate((el) =>
        el.parentElement?.tagName ?? 'UNKNOWN',
      );
      expect(parentTag, 'Listbox must be portaled to <body>').toBe('BODY');

      // ── position:fixed — immune to ancestor stacking-context trapping ──────
      const position = await listbox.evaluate((el) =>
        window.getComputedStyle(el).position,
      );
      expect(position, 'Listbox must use position:fixed').toBe('fixed');

      // ── z-index ≥ 120 — above sticky header (z-40) and sidebar (z-30) ──────
      const zIndex = await listbox.evaluate((el) =>
        parseInt(window.getComputedStyle(el).zIndex, 10),
      );
      expect(zIndex, 'Listbox z-index must be ≥ 120').toBeGreaterThanOrEqual(120);

      // ── Visible bounding box (not zero-size, not off-screen) ───────────────
      const box = await listbox.boundingBox();
      expect(box, 'Listbox must have a non-null bounding box').not.toBeNull();
      expect(box.width, 'Listbox must have visible width').toBeGreaterThan(100);
      expect(box.height, 'Listbox must have visible height').toBeGreaterThan(20);

      // ── Contains expected content ───────────────────────────────────────────
      await expect(listbox.locator('text=Organisation')).toBeVisible();

      // Regression screenshot — dropdown visible above page content
      await page.screenshot({
        path: path.join(SCREENSHOTS, 'scope-switcher-open.png'),
        fullPage: false,
      });

      await page.keyboard.press('Escape');
    },
  );

  // ── Test 2: InfoTip on Vue exécutive ────────────────────────────────────────
  test(
    'Vue exécutive: InfoTip icons show non-empty tooltip, no ghost bubbles',
    async ({ page }) => {
      await login(page);
      await page.goto('/cockpit');

      // Wait for ImpactDecisionPanel to finish loading (billing summary fetch)
      await page.waitForSelector('[data-testid="impact-decision-panel"]', {
        timeout: 15_000,
      });
      // Extra wait for async billing data
      await page.waitForTimeout(1500);

      // ── No ghost tooltip rendered before any hover ──────────────────────────
      await expect(
        page.locator('[role="tooltip"]'),
        'No tooltip should be visible without hover',
      ).toHaveCount(0);

      // ── At least one InfoTip icon exists on the executive view ─────────────
      const infotips = page.locator('button[aria-label="Aide contextuelle"]');
      const count = await infotips.count();
      expect(count, 'At least one InfoTip button must be rendered').toBeGreaterThan(0);
      await expect(infotips.first()).toBeVisible({ timeout: 5_000 });

      // ── Hover → tooltip appears with non-empty text content ─────────────────
      await infotips.first().hover();
      const tooltip = page.locator('[role="tooltip"]');
      await expect(tooltip, 'Tooltip must appear on hover').toBeVisible({
        timeout: 3_000,
      });

      const text = (await tooltip.textContent()).trim();
      expect(
        text.length,
        'Tooltip must contain meaningful text (no empty bubble)',
      ).toBeGreaterThan(5);

      // ── Portal assertion: tooltip must be in <body> ─────────────────────────
      const parentTag = await tooltip.evaluate((el) =>
        el.parentElement?.tagName ?? 'UNKNOWN',
      );
      expect(parentTag, 'Tooltip must be portaled to <body>').toBe('BODY');

      // ── position:fixed ──────────────────────────────────────────────────────
      const position = await tooltip.evaluate((el) =>
        window.getComputedStyle(el).position,
      );
      expect(position, 'Tooltip must use position:fixed').toBe('fixed');

      // Regression screenshot — tooltip visible above executive content
      await page.screenshot({
        path: path.join(SCREENSHOTS, 'infotip-tooltip-visible.png'),
        fullPage: false,
      });

      // ── Move away — tooltip must disappear (no lingering phantom ────────────
      await page.mouse.move(0, 0);
      await expect(
        page.locator('[role="tooltip"]'),
        'Tooltip must disappear after mouse leaves',
      ).toHaveCount(0, { timeout: 2_000 });
    },
  );
});
