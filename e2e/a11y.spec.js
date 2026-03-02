/**
 * PROMEOS — E2E Accessibility smoke tests (axe-core)
 * Validates: 0 critical a11y violations on key operations pages.
 * Requires: backend on :8001, frontend on :5173, demo data seeded.
 * Install: npm i -D @axe-core/playwright (in e2e/)
 */
import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

async function login(page) {
  await page.goto('/login');
  await page.fill('input[type="email"]', 'sophie@atlas.demo');
  await page.fill('input[type="password"]', 'demo2024');
  await page.click('button[type="submit"]');
  await page.waitForURL((url) => !url.pathname.includes('/login'), {
    timeout: 10_000,
  });
}

/**
 * Run axe-core and assert 0 critical violations.
 * color-contrast is excluded (design system handles it globally).
 */
async function assertNoCriticalViolations(page, label) {
  const results = await new AxeBuilder({ page })
    .withTags(['wcag2a', 'wcag2aa'])
    .disableRules(['color-contrast'])
    .analyze();

  const critical = results.violations.filter(v => v.impact === 'critical');
  if (critical.length > 0) {
    const summary = critical.map(v => `${v.id}: ${v.description} (${v.nodes.length} nodes)`).join('\n');
    expect.soft(critical.length, `${label} — critical a11y violations:\n${summary}`).toBe(0);
  }
}

test.describe('Accessibility smoke — axe-core', () => {
  test('/conformite has no critical a11y violations', async ({ page }) => {
    await login(page);
    await page.goto('/conformite');
    await page.waitForTimeout(3000);
    await assertNoCriticalViolations(page, '/conformite');
  });

  test('/actions has no critical a11y violations', async ({ page }) => {
    await login(page);
    await page.goto('/actions');
    await page.waitForTimeout(3000);
    await assertNoCriticalViolations(page, '/actions');
  });

  test('/anomalies has no critical a11y violations', async ({ page }) => {
    await login(page);
    await page.goto('/anomalies');
    await page.waitForTimeout(3000);
    await assertNoCriticalViolations(page, '/anomalies');
  });

  test('/compliance/pipeline has no critical a11y violations', async ({ page }) => {
    await login(page);
    await page.goto('/compliance/pipeline');
    await page.waitForTimeout(3000);
    await assertNoCriticalViolations(page, '/compliance/pipeline');
  });
});
