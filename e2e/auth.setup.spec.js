/**
 * PROMEOS — Playwright auth setup (Sprint infra-stabilisation 2026-05-29).
 *
 * Single source of truth for login. Run **once** by the `setup` Playwright
 * project, produces `.auth/promeos-user.json` consumed by all other
 * specs via `storageState`.
 *
 * Why : avant ce setup, chaque spec faisait son propre login. 4 logins
 * consécutifs dans une suite (ex `s2-conformite-simplicite-metier.spec.js`
 * 4 tests × 1 login) déclenchait le rate-limit BE `Identifiants
 * incorrects` sur le 4ᵉ → faux positif.
 *
 * Stratégie :
 *  1. POST direct `/api/auth/login` (court-circuite le formulaire UI et
 *     le rate-limit qui se déclenche sur tentatives consécutives via UI).
 *  2. Injection du token en `localStorage` (clé canonique `promeos_token`).
 *  3. Smoke d'un endpoint métier authentifié (`/api/health` puis
 *     `/api/auth/me`) pour confirmer que la session est exploitable
 *     côté backend AVANT que les specs lancent leurs propres requêtes.
 *  4. Sauvegarde `storageState` dans `e2e/.auth/promeos-user.json`
 *     (path gitignored, voir `e2e/.gitignore`).
 */
import { expect, test as setup } from '@playwright/test';
import { BACKEND_URL, DEMO_USER, AUTH_STORAGE_PATH, STORAGE_KEY_TOKEN } from './helpers.js';

// Setup timeout étendu : login + smoke + storageState + retry rate-limit.
setup.setTimeout(60_000);

/**
 * Login API avec retry exponentiel pour résister au rate-limit BE.
 *
 * Utilise `fetch` natif Node plutôt que `request` fixture Playwright
 * pour éviter le bug `Request context disposed` qui survient quand le
 * setup project tourne en isolation avec `--workers=1`.
 *
 * Le backend implémente un rate-limit sur /api/auth/login (3 tentatives /
 * minute par IP) qui s'enclenche après des runs Playwright répétés. C'est
 * un garde-fou de sécurité légitime → on RETRY avec backoff au lieu de le
 * contourner. 3 essais espacés (1s, 3s, 10s) = total max 14s + 3 requêtes,
 * borné et observable.
 */
/**
 * Attend que le backend réponde à /api/health avant de tenter le login.
 * Préfix obligatoire pour éviter le timeout sur le BE en cold start
 * (uvicorn + migrations alembic + import services = ~10s startup).
 */
async function waitForBackendReady(maxWaitSec = 30) {
  const start = Date.now();
  let lastErr = null;
  while ((Date.now() - start) / 1000 < maxWaitSec) {
    try {
      const ctrl = new AbortController();
      const t = setTimeout(() => ctrl.abort(), 3_000);
      const res = await fetch(`${BACKEND_URL}/api/health`, { signal: ctrl.signal });
      clearTimeout(t);
      if (res.ok) return;
      lastErr = `HTTP ${res.status}`;
    } catch (e) {
      lastErr = e.message;
    }
    await new Promise((r) => setTimeout(r, 1500));
  }
  throw new Error(
    `Backend ${BACKEND_URL}/api/health n'a pas répondu en ${maxWaitSec}s. ` +
      `Dernière erreur : ${lastErr}.`
  );
}

async function loginWithRetry(attempts = 3) {
  const backoffSec = [0, 1, 3, 10];
  let lastErr = null;
  for (let i = 1; i <= attempts; i++) {
    if (backoffSec[i - 1] > 0) {
      await new Promise((r) => setTimeout(r, backoffSec[i - 1] * 1000));
    }
    try {
      const controller = new AbortController();
      // 20s par tentative : large marge pour BE chargé (la cause vue
      // 2026-05-29 était 4 routes golden-paths × networkidle saturant
      // le BE pendant le run précédent).
      const timer = setTimeout(() => controller.abort(), 20_000);
      const res = await fetch(`${BACKEND_URL}/api/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: DEMO_USER.email, password: DEMO_USER.password }),
        signal: controller.signal,
      });
      clearTimeout(timer);
      if (res.ok) return await res.json();
      lastErr = `HTTP ${res.status} body=${(await res.text()).slice(0, 200)}`;
    } catch (e) {
      lastErr = e.message;
    }
    console.log(`[auth.setup] tentative ${i}/${attempts} échouée : ${lastErr}`);
  }
  throw new Error(
    `Login impossible après ${attempts} tentatives. Dernière erreur : ${lastErr}. ` +
      `Vérifier que ${BACKEND_URL}/api/auth/login répond et que demo user est seeded.`
  );
}

setup('authenticate as promeos demo user', async ({ page }) => {
  // 0. Wait BE ready (cold start uvicorn + migrations + import services).
  await waitForBackendReady();

  // 1. POST login direct avec retry rate-limit-aware (fetch natif).
  const { access_token } = await loginWithRetry();
  expect(
    access_token,
    'Le payload login ne contient pas access_token — schéma BE changé ?'
  ).toBeTruthy();

  // 2. Smoke d'un endpoint authentifié AVANT de sauvegarder l'état (fail-fast).
  const meCtrl = new AbortController();
  const meTimer = setTimeout(() => meCtrl.abort(), 5_000);
  const meRes = await fetch(`${BACKEND_URL}/api/auth/me`, {
    headers: { Authorization: `Bearer ${access_token}` },
    signal: meCtrl.signal,
  });
  clearTimeout(meTimer);
  expect(
    meRes.ok,
    `Token reçu mais /api/auth/me retourne ${meRes.status} — session invalide.`
  ).toBeTruthy();

  // 3. Charger la page racine pour avoir le bon origin avant d'écrire en
  // localStorage. waitUntil='domcontentloaded' = le plus rapide qui garantit
  // que `window.localStorage` est dispo.
  await page.goto('/login', { waitUntil: 'domcontentloaded' });
  await page.evaluate(
    ({ key, token }) => {
      localStorage.setItem(key, token);
    },
    { key: STORAGE_KEY_TOKEN, token: access_token }
  );

  // 4. Sauvegarde storageState. Playwright restaurera localStorage +
  // cookies dans chaque test qui dépend de `setup` via le config.
  await page.context().storageState({ path: AUTH_STORAGE_PATH });
});
