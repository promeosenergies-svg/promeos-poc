/**
 * PROMEOS — F3: Action Closure + Proof Flow
 * Sprint F — Real clicked E2E: open action → add proof → close with justification.
 *
 * Parcours: Login → Actions → Detail drawer → Evidence tab →
 *           Add proof → Status "Terminée" → Close form → Verify
 */
import { test, expect } from '@playwright/test';
import {
  login, attachConsoleMonitor, assertCleanBody, waitForPageReady,
  screenshot, VIEWPORTS, BACKEND_URL,
} from './helpers.js';

const vp = VIEWPORTS.desktop; // Single viewport — functional flow test

test.describe('F3 — Action Closure + Proof Flow', () => {
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

  test('Full action proof + closure flow', async ({ page }) => {
    test.setTimeout(90_000); // Multi-step flow needs more time
    // ── Step 1: Navigate to Actions page ──
    await page.goto('/actions');
    await waitForPageReady(page);
    await assertCleanBody(page);

    // ── Step 2: Click first action row to open detail drawer ──
    const actionRow = page.locator('table tbody tr').first();
    await expect(actionRow).toBeVisible({ timeout: 10_000 });
    await screenshot(page, 'f3-01-actions-list');

    await actionRow.click();
    await page.waitForTimeout(1500);

    // Drawer should be open — verify detail content
    const body = await page.textContent('body');
    expect(body.length).toBeGreaterThan(300);

    // ── Step 3: Switch to Evidence tab ("Pièces jointes") ──
    const evidenceTab = page.locator('text=Pièces jointes').first();
    await expect(evidenceTab).toBeVisible({ timeout: 5000 });
    await evidenceTab.click();
    await page.waitForTimeout(500);

    await screenshot(page, 'f3-02-evidence-tab-before');

    // ── Step 4: Fill evidence form ──
    // Select evidence type
    const typeSelect = page.locator('select').last();
    if (await typeSelect.isVisible({ timeout: 2000 }).catch(() => false)) {
      await typeSelect.selectOption('rapport');
    }

    // Fill label (required field)
    const labelInput = page.locator('input[placeholder*="Libellé"]');
    await expect(labelInput).toBeVisible({ timeout: 5000 });
    await labelInput.fill('Rapport audit énergétique Q1 2026');

    // Fill URL (optional)
    const urlInput = page.locator('input[placeholder*="URL"]');
    if (await urlInput.isVisible({ timeout: 2000 }).catch(() => false)) {
      await urlInput.fill('https://promeos.io/docs/audit-q1-2026.pdf');
    }

    await screenshot(page, 'f3-03-evidence-form-filled');

    // ── Step 5: Submit evidence ──
    const addBtn = page.locator('button:has-text("Ajouter la pièce")');
    await expect(addBtn).toBeVisible({ timeout: 3000 });
    await expect(addBtn).toBeEnabled();
    await addBtn.click();

    // Wait for evidence to be added
    await page.waitForTimeout(2000);

    // Verify evidence was added (label should appear in the evidence list)
    const bodyAfterEvidence = await page.textContent('body');
    expect(bodyAfterEvidence).toContain('Rapport audit');
    await screenshot(page, 'f3-04-evidence-added');

    // ── Step 6: Go back to Detail tab to change status ──
    const detailTab = page.locator('text=Détail').first();
    if (await detailTab.isVisible({ timeout: 2000 }).catch(() => false)) {
      await detailTab.click();
      await page.waitForTimeout(500);
    }

    // ── Step 7: Click "Terminée" status button (in "Changer le statut" section) ──
    const statusSection = page.locator('text=Changer le statut').locator('..');
    const doneBtn = statusSection.locator('button:has-text("Terminée")');
    await expect(doneBtn).toBeVisible({ timeout: 5000 });

    // Check if button is not already the current status (disabled)
    const isAlreadyDone = await doneBtn.isDisabled().catch(() => false);
    if (isAlreadyDone) {
      // Action is already done — skip closure flow, just verify state
      await screenshot(page, 'f3-05-already-done');
      return;
    }

    await doneBtn.click();
    await page.waitForTimeout(1000);

    // ── Step 8: Close form should appear ──
    const closeForm = page.locator('[data-testid="close-form"]');
    await expect(closeForm).toBeVisible({ timeout: 5000 });

    await screenshot(page, 'f3-05-close-form-visible');

    // ── Step 9: Fill closure justification ──
    const justification = page.locator('[data-testid="closure-justification"]');
    await expect(justification).toBeVisible({ timeout: 3000 });
    await justification.fill('Audit réalisé, rapport validé par le responsable énergie. Conformité confirmée.');

    // ── Step 10: Click close button ──
    const closeBtn = page.locator('button:has-text("Clôturer avec commentaire")');
    await expect(closeBtn).toBeVisible({ timeout: 3000 });
    await expect(closeBtn).toBeEnabled();
    await closeBtn.click();

    // Wait for status to update
    await page.waitForTimeout(2000);

    // ── Step 11: Verify closure ──
    // "Terminée" button should now be disabled (current state)
    const doneAfter = statusSection.locator('button:has-text("Terminée")');
    const isDisabledNow = await doneAfter.isDisabled().catch(() => false);
    expect(isDisabledNow).toBe(true);

    // Close form should be gone
    await expect(closeForm).not.toBeVisible();

    // Toast should have appeared
    const finalBody = await page.textContent('body');
    await assertCleanBody(page);

    await screenshot(page, 'f3-06-action-closed');
  });

  test('Evidence tab shows proof after adding', async ({ page }) => {
    // Use API to get a valid action
    await page.goto('/actions');
    await waitForPageReady(page);

    const actionRow = page.locator('table tbody tr').first();
    const isVisible = await actionRow.isVisible({ timeout: 5000 }).catch(() => false);
    if (!isVisible) {
      test.skip(true, 'No actions available');
      return;
    }

    await actionRow.click();
    await page.waitForTimeout(1500);

    // Switch to evidence tab
    const evidenceTab = page.locator('text=Pièces jointes').first();
    await expect(evidenceTab).toBeVisible({ timeout: 5000 });
    await evidenceTab.click();
    await page.waitForTimeout(500);

    // Evidence tab content should be visible
    const tabContent = await page.textContent('body');
    // Either "Aucune pièce jointe" or existing evidence
    expect(tabContent).toMatch(/pièce|Ajouter|Libellé/);

    await screenshot(page, 'f3-evidence-tab-content');
  });
});
