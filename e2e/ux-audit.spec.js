/**
 * PROMEOS — UX Audit Spec
 * Automated evidence capture for UX review: screenshot + axe-core + console errors.
 *
 * Usage:
 *   cd e2e && npx playwright test ux-audit.spec.js --headed
 *
 * Output:
 *   e2e/ux-report/screenshots/<slug>.png   — full-page screenshots
 *   e2e/ux-report/findings.json            — structured a11y + metrics data
 *
 * To review specific sections, edit the SECTIONS array below.
 * Requires: backend on :8001, frontend on :5173, demo data seeded.
 */
import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import { promises as fs } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

// ── Output directories ─────────────────────────────────────────────────────────
// UX_REPORT_NAME env var lets the skill write evidence into a named folder so
// screenshots are never overwritten between runs.
// e.g.  UX_REPORT_NAME=UX_REVIEW_2026-03-07_16-02  playwright test ux-audit.spec.js
const REPORT_NAME   = process.env.UX_REPORT_NAME || 'ux-report';
const REPORT_DIR    = path.join(__dirname, REPORT_NAME);
const SCREENSHOTS_DIR = path.join(REPORT_DIR, 'screenshots');

// ── Section config — edit this to target specific pages ──────────────────────
const SECTIONS = [
  { name: 'Explorer',     path: '/consommations/explorer',  slug: 'explorer'  },
];

// ── Helpers ───────────────────────────────────────────────────────────────────
async function login(page) {
  await page.goto('/login');
  await page.fill('input[type="email"]', 'promeos@promeos.io');
  await page.fill('input[type="password"]', 'promeos2024');
  await page.click('button[type="submit"]');
  await page.waitForURL((url) => !url.pathname.includes('/login'), { timeout: 10_000 });
}

async function ensureDirs() {
  await fs.mkdir(SCREENSHOTS_DIR, { recursive: true });
}

/**
 * Count interactive elements missing accessible names.
 * Returns count of buttons/links/inputs with no text, aria-label, aria-labelledby, or title.
 */
async function countMissingAria(page) {
  return page.evaluate(() => {
    const els = [...document.querySelectorAll('button, a[href], input, select, textarea')];
    return els.filter((el) => {
      const hasText     = (el.textContent?.trim().length ?? 0) > 0;
      const hasAriaLbl  = el.getAttribute('aria-label') || el.getAttribute('aria-labelledby');
      const hasTitle    = el.getAttribute('title');
      const hasPlaceholder = el.getAttribute('placeholder'); // valid for inputs
      return !hasText && !hasAriaLbl && !hasTitle && !hasPlaceholder;
    }).length;
  });
}

/** Return tab order issues: elements with tabindex > 0 (anti-pattern). */
async function countPositiveTabindex(page) {
  return page.evaluate(() =>
    [...document.querySelectorAll('[tabindex]')].filter(
      (el) => parseInt(el.getAttribute('tabindex'), 10) > 0
    ).length
  );
}

// ── Findings accumulator (module-level, shared within serial worker) ──────────
const findings = [];

// ── Suite ─────────────────────────────────────────────────────────────────────
test.describe.serial('UX Audit — Consommations module', () => {

  for (const section of SECTIONS) {
    test(`[${section.slug}] ${section.name}`, async ({ page }) => {
      await ensureDirs();

      // Collect console errors for this page
      const consoleErrors = [];
      page.on('console', (msg) => {
        if (msg.type() === 'error') consoleErrors.push(msg.text());
      });

      // Login + navigate
      await login(page);
      const t0 = Date.now();
      await page.goto(section.path);
      await page.waitForLoadState('networkidle');
      // Extra wait for React async renders (charts, skeleton → content)
      await page.waitForTimeout(2500);
      const loadMs = Date.now() - t0;

      // Full-page screenshot
      const screenshotFile = `${section.slug}.png`;
      await page.screenshot({
        fullPage: true,
        path: path.join(SCREENSHOTS_DIR, screenshotFile),
      });

      // Axe-core accessibility scan
      const axeResults = await new AxeBuilder({ page })
        .withTags(['wcag2a', 'wcag2aa'])
        .disableRules(['color-contrast']) // handled globally by design system
        .analyze();

      const violations = axeResults.violations.map((v) => ({
        id:          v.id,
        impact:      v.impact,
        description: v.description,
        nodes:       v.nodes.length,
        helpUrl:     v.helpUrl,
        // First failing node selector for context
        selector:    v.nodes[0]?.target?.join(' > ') ?? null,
      }));

      // Additional probes
      const missingAriaCount      = await countMissingAria(page);
      const positiveTabindexCount = await countPositiveTabindex(page);
      const focusableCount        = await page.evaluate(() =>
        document.querySelectorAll(
          'a[href], button:not([disabled]), input:not([disabled]), ' +
          'select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'
        ).length
      );

      // Record finding
      findings.push({
        slug:                 section.slug,
        name:                 section.name,
        path:                 section.path,
        screenshotFile,
        loadMs,
        consoleErrors,
        consoleErrorCount:    consoleErrors.length,
        a11yViolations:       violations,
        criticalViolations:   violations.filter((v) => v.impact === 'critical').length,
        seriousViolations:    violations.filter((v) => v.impact === 'serious').length,
        moderateViolations:   violations.filter((v) => v.impact === 'moderate').length,
        missingAriaCount,
        positiveTabindexCount,
        focusableCount,
      });

      // Soft assertion on critical violations (non-blocking — audit continues)
      const critical = violations.filter((v) => v.impact === 'critical');
      if (critical.length > 0) {
        const summary = critical.map((v) => `${v.id} (${v.nodes} nodes)`).join(', ');
        expect
          .soft(critical.length, `[${section.slug}] Critical a11y violations: ${summary}`)
          .toBe(0);
      }
    });
  }

  // Write consolidated report after all sections complete
  test.afterAll(async () => {
    await ensureDirs();
    const report = {
      generatedAt: new Date().toISOString(),
      totalSections: findings.length,
      summary: {
        totalCriticalViolations: findings.reduce((s, f) => s + f.criticalViolations, 0),
        totalSeriousViolations:  findings.reduce((s, f) => s + f.seriousViolations, 0),
        totalConsoleErrors:      findings.reduce((s, f) => s + f.consoleErrorCount, 0),
        totalMissingAria:        findings.reduce((s, f) => s + f.missingAriaCount, 0),
        avgLoadMs:               Math.round(
          findings.reduce((s, f) => s + f.loadMs, 0) / (findings.length || 1)
        ),
      },
      sections: findings,
    };

    const reportPath = path.join(REPORT_DIR, 'findings.json');
    await fs.writeFile(reportPath, JSON.stringify(report, null, 2), 'utf8');
    console.log(`\nUX audit report: ${reportPath}`);
    console.log(`Screenshots:     ${SCREENSHOTS_DIR}`);
  });
});
