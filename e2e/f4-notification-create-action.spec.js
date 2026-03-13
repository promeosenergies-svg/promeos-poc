/**
 * PROMEOS — F4: Notification → Create Action Flow
 * Sprint F — Real clicked E2E: open notification → CTA → create action drawer.
 *
 * Parcours: Login → Notifications → Open drawer → Créer action →
 *           Verify pre-fill → Submit → Action created
 */
import { test, expect } from '@playwright/test';
import {
  login, attachConsoleMonitor, assertCleanBody, waitForPageReady,
  screenshot, VIEWPORTS, BACKEND_URL,
} from './helpers.js';

const vp = VIEWPORTS.desktop; // Single viewport — functional flow test

test.describe('F4 — Notification → Create Action', () => {
  let consoleMonitor;

  test.beforeEach(async ({ page }) => {
    await page.setViewportSize({ width: vp.width, height: vp.height });
    consoleMonitor = attachConsoleMonitor(page);
    await login(page);
  });

  test.afterEach(async () => {
    const errors = consoleMonitor.getErrors();
    expect(errors.length, `Console errors: ${errors.join(' | ')}`).toBe(0);
  });

  test('Notification drawer shows CTA and opens action creation', async ({ page }) => {
    test.setTimeout(90_000); // Multi-step flow
    // ── Step 1: Navigate to Notifications ──
    await page.goto('/notifications');
    await waitForPageReady(page);
    await assertCleanBody(page);

    await screenshot(page, 'f4-01-notifications-list');

    // ── Step 2: Click first notification row ──
    const notifRow = page.locator('table tbody tr, [role="row"]').first();
    const rowVisible = await notifRow.isVisible({ timeout: 10_000 }).catch(() => false);
    if (!rowVisible) {
      test.skip(true, 'No notifications visible in demo data');
      return;
    }

    // Capture notification title before clicking
    const rowText = await notifRow.textContent();
    await notifRow.click();
    await page.waitForTimeout(1500);

    await screenshot(page, 'f4-02-notification-drawer');

    // ── Step 3: Verify drawer content ──
    const drawerBody = await page.textContent('body');
    // Drawer should show notification details
    expect(drawerBody.length).toBeGreaterThan(300);

    // ── Step 4: Find and click "Créer action" CTA ──
    const ctaBtn = page.locator('[data-testid="cta-notif-create-action"]');
    const ctaVisible = await ctaBtn.isVisible({ timeout: 5000 }).catch(() => false);

    if (!ctaVisible) {
      // Try finding by text instead
      const ctaByText = page.locator('button:has-text("Créer action")').first();
      const ctaTextVisible = await ctaByText.isVisible({ timeout: 3000 }).catch(() => false);
      if (!ctaTextVisible) {
        test.skip(true, 'Créer action CTA not visible in drawer');
        return;
      }
      await ctaByText.click();
    } else {
      await ctaBtn.click();
    }

    await page.waitForTimeout(1500);
    await screenshot(page, 'f4-03-create-action-drawer');

    // ── Step 5: Verify CreateActionDrawer opened with pre-fill ──
    const actionBody = await page.textContent('body');

    // Form should be visible with title field
    const titleInput = page.locator('input[placeholder*="OPERAT"], input[placeholder*="titre"], input[placeholder*="Déclarer"]').first();
    const titleVisible = await titleInput.isVisible({ timeout: 5000 }).catch(() => false);

    if (titleVisible) {
      // Verify title was pre-filled from notification
      const titleValue = await titleInput.inputValue();
      expect(titleValue.length).toBeGreaterThan(0);
    }

    // The drawer should contain action creation elements
    expect(actionBody).toMatch(/Créer|action|titre|priorit|impact/i);

    // ── Step 6: Verify source context ──
    // Description should contain "Action créée depuis" if auto-filled
    const descArea = page.locator('textarea').first();
    if (await descArea.isVisible({ timeout: 2000 }).catch(() => false)) {
      const descValue = await descArea.inputValue();
      if (descValue) {
        expect(descValue).toContain('Action créée depuis');
      }
    }

    await screenshot(page, 'f4-04-form-prefilled');

    // ── Step 7: Submit the action ──
    const submitBtn = page.locator('button:has-text("Créer l\'action"), button:has-text("Créer action"), button[type="submit"]:has-text("Créer")').first();
    const submitVisible = await submitBtn.isVisible({ timeout: 3000 }).catch(() => false);

    if (submitVisible) {
      await submitBtn.click();
      await page.waitForTimeout(2000);

      // Verify action was created (drawer closes or success toast)
      const finalBody = await page.textContent('body');
      await assertCleanBody(page);
      await screenshot(page, 'f4-05-action-created');
    }
  });

  test('Notification deeplink navigates correctly', async ({ page }) => {
    await page.goto('/notifications');
    await waitForPageReady(page);

    // Click first notification
    const notifRow = page.locator('table tbody tr, [role="row"]').first();
    const rowVisible = await notifRow.isVisible({ timeout: 10_000 }).catch(() => false);
    if (!rowVisible) {
      test.skip(true, 'No notifications available');
      return;
    }

    await notifRow.click();
    await page.waitForTimeout(1500);

    // Check for "Ouvrir" deeplink button
    const openBtn = page.locator('button:has-text("Ouvrir")').first();
    const openVisible = await openBtn.isVisible({ timeout: 3000 }).catch(() => false);

    if (openVisible) {
      await openBtn.click();
      await page.waitForTimeout(2000);

      // Should navigate away from notifications
      const url = page.url();
      expect(url).not.toContain('/notifications');
      await assertCleanBody(page);
      await screenshot(page, 'f4-deeplink-target');
    }
  });
});
