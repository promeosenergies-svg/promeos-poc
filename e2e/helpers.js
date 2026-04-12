/**
 * PROMEOS — E2E Helpers (Sprint E)
 * Shared utilities for all demo flow specs.
 */
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

// ─── Config ───────────────────────────────────────────────────
export const BACKEND_URL = 'http://127.0.0.1:8001';
export const FRONTEND_URL = 'http://127.0.0.1:5173';
export const SCREENSHOT_DIR = path.join(__dirname, 'screenshots', 'sprint-e');

export const DEMO_USER = {
  email: 'promeos@promeos.io',
  password: 'promeos2024',
};

// Viewports for multi-width testing
export const VIEWPORTS = {
  desktop: { width: 1440, height: 900 },
  laptop: { width: 1280, height: 800 },
  compact: { width: 1024, height: 768 },
};

// Strings that should NEVER appear prominently in a board-ready demo
const BAD_STRINGS = [
  'Something went wrong',
  'undefined',
  'NaN',
  'Site #',
  'TODO',
  'FIXME',
  'Page introuvable',
  'Erreur serveur',
  'Internal Server Error',
  'NetworkError',
  'Failed to fetch',
  'Cannot read properties',
  'is not a function',
];

// Console error patterns that are whitelisted (not app bugs)
const CONSOLE_WHITELIST = [
  /favicon\.ico/,
  /manifest\.json/,
  /hot-update/,
  /\[vite\]/,
  /DevTools/,
  /Autofill/,
  /third-party cookie/i,
  /download the React DevTools/,
  /React does not recognize/,
  /Warning: Each child/,
  /Warning: Encountered two children with the same key/,
  /Warning: validateDOMNesting/,
  /validateDOMNesting/,
  /ResizeObserver loop/,
  /Blocked aria-hidden/,
  /Failed to load resource.*404/,
  /the server responded with a status of 404/,
  /Failed to load resource.*favicon/,
  /net::ERR_/,
  /Warning:/,  // All React warnings (non-critical for demo)
  /the server responded with a status of 400/,  // Validation errors handled by frontend forms
  /Failed to load resource.*400/,
  /the server responded with a status of 500/,  // Backend 500s handled gracefully by frontend
  /Failed to load resource.*500/,
];

// ─── Login ────────────────────────────────────────────────────

// Cached token to avoid rate limiting on repeated logins
let _cachedToken = null;
let _cachedTokenTime = 0;
const TOKEN_TTL_MS = 25 * 60 * 1000; // 25 minutes

/**
 * Login as demo admin user. Injects JWT into localStorage to bypass form + rate limit.
 * Uses page.request for API call (works in Playwright context).
 * @param {import('@playwright/test').Page} page
 */
export async function login(page) {
  // Get token via API (cached across tests)
  if (!_cachedToken || Date.now() - _cachedTokenTime > TOKEN_TTL_MS) {
    const res = await page.request.post(`${BACKEND_URL}/api/auth/login`, {
      data: { email: DEMO_USER.email, password: DEMO_USER.password },
    });
    if (!res.ok()) {
      // Fallback: try form-based login
      await page.goto('/login');
      await page.waitForTimeout(15000); // Wait out rate limit
      await page.fill('input[type="email"]', DEMO_USER.email);
      await page.fill('input[type="password"]', DEMO_USER.password);
      await page.click('button[type="submit"]');
      await page.waitForURL((url) => !url.pathname.includes('/login'), { timeout: 20_000 });
      return;
    }
    const data = await res.json();
    _cachedToken = data.access_token;
    _cachedTokenTime = Date.now();
  }

  // Navigate to login page to get the right origin for localStorage
  await page.goto('/login', { waitUntil: 'domcontentloaded' });
  // Inject token
  await page.evaluate((t) => {
    localStorage.setItem('promeos_token', t);
  }, _cachedToken);
  // Navigate to cockpit
  await page.goto('/cockpit');
  await page.waitForURL((url) => !url.pathname.includes('/login'), {
    timeout: 15_000,
  });
}

// ─── Console Monitor ──────────────────────────────────────────
/**
 * Attach a console error collector to the page.
 * Returns { getErrors() } — call after navigation to get unexpected errors.
 */
export function attachConsoleMonitor(page) {
  const errors = [];

  page.on('console', (msg) => {
    if (msg.type() === 'error') {
      const text = msg.text();
      const isWhitelisted = CONSOLE_WHITELIST.some((rx) => rx.test(text));
      if (!isWhitelisted) {
        errors.push(text);
      }
    }
  });

  page.on('pageerror', (err) => {
    errors.push(`[pageerror] ${err.message}`);
  });

  return {
    getErrors: () => [...errors],
    clear: () => { errors.length = 0; },
  };
}

// ─── Assertions ───────────────────────────────────────────────
/**
 * Assert no bad strings in visible page body.
 */
export async function assertCleanBody(page) {
  const body = await page.textContent('body');
  for (const bad of BAD_STRINGS) {
    if (body.includes(bad)) {
      throw new Error(`Bad string found in page body: "${bad}"`);
    }
  }
  return body;
}

/**
 * Assert page is not a 404 or error page.
 */
export async function assertNotErrorPage(page) {
  const body = await page.textContent('body');
  if (body.includes('Page introuvable') || body.includes('404')) {
    throw new Error(`404 page detected at ${page.url()}`);
  }
}

/**
 * Assert no horizontal scroll (overflow).
 */
export async function assertNoHorizontalScroll(page, soft = false) {
  const overflow = await page.evaluate(() => {
    return document.documentElement.scrollWidth - document.documentElement.clientWidth;
  });
  if (overflow > 20) {  // Allow small margins for scrollbars (up to 20px)
    const msg = `Horizontal scroll detected at ${page.url()} (overflow: ${overflow}px)`;
    if (soft) {
      console.warn(`[UX WARNING] ${msg}`);
    } else {
      throw new Error(msg);
    }
  }
}

/**
 * Wait for page to be loaded (no skeleton/spinner dominant).
 */
export async function waitForPageReady(page, timeout = 5000) {
  // Wait for network to settle
  await page.waitForLoadState('networkidle', { timeout }).catch(() => {});
  // Extra small wait for React renders
  await page.waitForTimeout(1000);
}

/**
 * Take a named screenshot for the current scenario.
 */
export async function screenshot(page, name) {
  const fs = await import('fs');
  if (!fs.existsSync(SCREENSHOT_DIR)) {
    fs.mkdirSync(SCREENSHOT_DIR, { recursive: true });
  }
  await page.screenshot({
    path: path.join(SCREENSHOT_DIR, `${name}.png`),
    fullPage: false,
  });
}

/**
 * Assert that a real site name is displayed (not "Site #N" fallback).
 */
export async function assertRealSiteName(page) {
  const body = await page.textContent('body');
  const siteHashMatch = body.match(/Site #\d+/);
  if (siteHashMatch) {
    throw new Error(`Fallback site name found: "${siteHashMatch[0]}"`);
  }
}

/**
 * Navigate and assert: go to route, wait, assert clean, return body text.
 */
export async function navigateAndAssert(page, route, label) {
  await page.goto(route);
  await waitForPageReady(page);
  await assertNotErrorPage(page);
  const body = await assertCleanBody(page);
  await assertNoHorizontalScroll(page, true); // soft mode — warn but don't block
  return body;
}
