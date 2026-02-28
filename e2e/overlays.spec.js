/**
 * PROMEOS — Overlay Premium Smoke Tests (V2)
 * Validates that portal-based overlays are:
 *   - Rendered as direct children of <body> (createPortal)
 *   - Using position:fixed (immune to stacking-context trapping)
 *   - z-index ≥ 120 (above sticky header z-40, sidebar z-30, StickyFilterBar z-20)
 *   - Correctly positioned relative to their trigger
 *   - Stable after scroll + viewport resize (useFloatingPortalPosition hook)
 *
 * Regressions guarded:
 *   1. ScopeSwitcher dropdown clipped behind sticky+backdrop-blur (backdrop-filter stacking context)
 *   2. InfoTip rendering empty black dots (content prop undefined)
 *   3. Dropdowns drifting from trigger after scroll or viewport resize
 *   4. TooltipPortal z-[9999] — now standardized to z-[120]
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
  await page.waitForURL((url) => !url.pathname.includes('/login'), { timeout: 10_000 });
}

/** Assert the overlay element is portaled to <body>, position:fixed, z >= 120. */
async function assertPremiumPortal(el, label = 'overlay') {
  const parentTag = await el.evaluate((node) => node.parentElement?.tagName ?? 'UNKNOWN');
  expect(parentTag, `${label}: must be portaled to <body>`).toBe('BODY');

  const position = await el.evaluate((node) => window.getComputedStyle(node).position);
  expect(position, `${label}: must use position:fixed`).toBe('fixed');

  const zIndex = await el.evaluate((node) => parseInt(window.getComputedStyle(node).zIndex, 10));
  expect(zIndex, `${label}: z-index must be ≥ 120`).toBeGreaterThanOrEqual(120);
}

/** Assert panel bounding box is near the trigger (within tolerance px). */
async function assertAlignedNear(trigger, panel, label = 'panel', tolerance = 40) {
  const tBox = await trigger.boundingBox();
  const pBox = await panel.boundingBox();
  expect(tBox, `${label}: trigger must be visible`).not.toBeNull();
  expect(pBox, `${label}: panel must have a bounding box`).not.toBeNull();

  // Panel Y should be below the trigger bottom (within tolerance)
  expect(pBox.y, `${label}: panel top should be near trigger bottom`)
    .toBeGreaterThanOrEqual(tBox.y + tBox.height - tolerance);
  expect(pBox.y, `${label}: panel should not be far below trigger`)
    .toBeLessThan(tBox.y + tBox.height + tolerance + 200); // allow for panel height

  // Panel X should be near the trigger X
  expect(Math.abs(pBox.x - tBox.x), `${label}: panel X should be near trigger X`)
    .toBeLessThan(tolerance);
}

test.beforeAll(() => {
  fs.mkdirSync(SCREENSHOTS, { recursive: true });
});

test.describe('Overlay premium — portal + z-index + scroll/resize regression', () => {

  // ── Test 1: ScopeSwitcher dropdown — portal + fixed + z + scroll + resize ──
  test('ScopeSwitcher: portaled, fixed, z≥120, stable on scroll and resize', async ({ page }) => {
    await login(page);
    await page.goto('/consommations');
    await page.waitForTimeout(2000);

    const trigger = page.locator('[data-testid="scope-switcher-trigger"]');
    await expect(trigger).toBeVisible({ timeout: 8_000 });

    // Open dropdown
    await trigger.click();
    const panel = page.locator('[data-testid="scope-switcher-panel"]');
    await expect(panel).toBeVisible({ timeout: 5_000 });

    // ── Premium assertions ───────────────────────────────────────────────────
    await assertPremiumPortal(panel, 'ScopeSwitcher panel');

    // Bounding box: non-zero, visible
    const box = await panel.boundingBox();
    expect(box).not.toBeNull();
    expect(box.width).toBeGreaterThan(100);
    expect(box.height).toBeGreaterThan(20);

    // Content visible
    await expect(panel.locator('text=Organisation')).toBeVisible();

    // Alignment: panel is near trigger
    await assertAlignedNear(trigger, panel, 'ScopeSwitcher initial');

    await page.screenshot({ path: path.join(SCREENSHOTS, 'scope-switcher-open.png') });

    // ── Scroll 400px — panel must follow trigger (trigger is in sticky header) ─
    await page.evaluate(() => window.scrollBy(0, 400));
    await page.waitForTimeout(200); // rAF + visualViewport settle

    await expect(panel).toBeVisible({ timeout: 3_000 });
    await assertAlignedNear(trigger, panel, 'ScopeSwitcher after scroll');

    await page.screenshot({ path: path.join(SCREENSHOTS, 'scope-switcher-after-scroll.png') });

    // ── Resize viewport — panel must clamp within new bounds ─────────────────
    await page.setViewportSize({ width: 900, height: 600 });
    await page.waitForTimeout(200);

    await expect(panel).toBeVisible({ timeout: 3_000 });
    const panelBox = await panel.boundingBox();
    expect(panelBox.x + panelBox.width).toBeLessThan(900 + 20); // within viewport (+ clamp margin)

    // ESC closes
    await page.keyboard.press('Escape');
    await expect(panel).not.toBeVisible({ timeout: 2_000 });
  });

  // ── Test 2: InfoTip — portal + fixed + z + non-empty text ──────────────────
  test('InfoTip: portaled tooltip, z≥120, never empty', async ({ page }) => {
    await login(page);
    await page.goto('/cockpit');

    await page.waitForSelector('[data-testid="impact-decision-panel"]', { timeout: 15_000 });
    await page.waitForTimeout(1500);

    // No ghost tooltip before hover
    await expect(page.locator('[role="tooltip"]')).toHaveCount(0);

    // At least one InfoTip button
    const infotips = page.locator('[data-testid="infotip"]');
    expect(await infotips.count()).toBeGreaterThan(0);
    await expect(infotips.first()).toBeVisible({ timeout: 5_000 });

    // Hover → tooltip appears with non-empty text
    await infotips.first().hover();
    const tooltip = page.locator('[role="tooltip"]');
    await expect(tooltip).toBeVisible({ timeout: 3_000 });

    const text = (await tooltip.textContent() ?? '').trim();
    expect(text.length, 'Tooltip must contain meaningful text (no empty bubble)').toBeGreaterThan(5);

    // Premium assertions
    await assertPremiumPortal(tooltip, 'InfoTip tooltip');

    await page.screenshot({ path: path.join(SCREENSHOTS, 'infotip-tooltip-visible.png') });

    // Mouse away → tooltip disappears
    await page.mouse.move(0, 0);
    await expect(page.locator('[role="tooltip"]')).toHaveCount(0, { timeout: 2_000 });
  });

  // ── Test 3: StickyFilterBar dropdowns ───────────────────────────────────────
  test('StickyFilterBar: presets dropdown portaled, fixed, z≥120', async ({ page }) => {
    await login(page);

    // Navigate to a consumption page with presets enabled
    await page.goto('/consommations');
    await page.waitForTimeout(3000);

    // Locate presets trigger (only visible when savedPresets.length > 0)
    const presetsTrigger = page.locator('[data-testid="sticky-presets-trigger"]');
    const presetsVisible = await presetsTrigger.isVisible().catch(() => false);

    if (!presetsVisible) {
      test.skip(true, 'No saved presets available in this demo session — skip presets test');
      return;
    }

    await presetsTrigger.click();
    const presetsPanel = page.locator('[data-testid="sticky-presets-panel"]');
    await expect(presetsPanel).toBeVisible({ timeout: 5_000 });

    await assertPremiumPortal(presetsPanel, 'Presets panel');
    await assertAlignedNear(presetsTrigger, presetsPanel, 'Presets panel');

    await page.screenshot({ path: path.join(SCREENSHOTS, 'presets-panel-open.png') });
  });

});
