# Audit postfix — Infra Playwright stabilisation (post-S3)

**Branche** : `claude/infra-playwright-stabilisation-post-s3`
**Base** : `claude/refonte-sol2` (HEAD `a75d14e1` post #328)
**Date** : 2026-05-29

---

## 1. Cause probable du flake

### Symptôme observé

Pendant la QA pré-merge S2 (PR #326) puis pré-merge S3 (PR #327), le test
Playwright **Item 11** de `s2-conformite-simplicite-metier.spec.js`
échouait avec `Identifiants incorrects` après la 4ᵉ tentative de login
consécutive, en suite — vert en isolation.

Le smoke postmerge S3 (#328) sur même environnement ne reproduisait pas
le flake, indiquant un état transient lié à la cadence d'appels login.

### Diagnostic

La spec S2 implémentait son propre `beforeEach login()` qui faisait :
1. `page.goto('/login')`
2. `page.fill('email')` + `page.fill('password')`
3. `page.click('Se connecter')`
4. `page.waitForURL`

Pour **4 tests** = 4 logins UI consécutifs en quelques secondes. Le backend
(uvicorn + `slowapi`) applique un rate-limit sur `/api/auth/login` qui
bloque silencieusement après ~3 tentatives par minute par IP, retournant
401 « Identifiants incorrects ». Le 4ᵉ test tombait juste sous le seuil.

Autres specs du repo utilisent déjà un helper `e2e/helpers.js::login()`
qui cache le token API (TTL 25 min). La spec S2 ne l'utilisait pas, ce
qui expliquait l'exposition spécifique au flake.

### Cause racine

**Pas un bug du produit** — le rate-limit BE est un garde-fou de
sécurité légitime. C'est l'architecture des tests qui exposait le
problème : chaque spec re-faisait son login indépendamment.

---

## 2. Stratégie storageState

Approche choisie : **login one-shot au début du run + storageState
partagé** entre tous les tests via `project.dependencies`.

### Fichiers livrés

| Fichier | Rôle |
|---|---|
| `e2e/auth.setup.spec.js` | Login one-shot, persiste storageState (clé localStorage `promeos_token` = AuthContext FE). Utilise `fetch` natif Node (pas la fixture `request` qui produit `Request context disposed`). Retry+backoff sur rate-limit. Wait BE `/api/health` avant login. |
| `e2e/playwright.config.js` | 2 projects : `setup` (testMatch `auth.setup.spec.js`) + `chromium` (storageState path, `dependencies: ['setup']`, testIgnore `auth.setup`). |
| `e2e/.gitignore` | Protège `.auth/`, `test-results/`, `playwright-report/`. |
| `e2e/helpers.js` | Constantes `AUTH_STORAGE_PATH` + `STORAGE_KEY_TOKEN` partagées. |

### Spec S2 migrée

`s2-conformite-simplicite-metier.spec.js` : retrait du `beforeEach login()`
local. Les pages héritent du storageState — plus aucun appel `/api/auth/login`
côté tests applicatifs.

### Nouvelle spec golden paths

`e2e/golden-paths.spec.js` : 4 routes cardinales validées sans console
error ni network 5xx :
- `/conformite`
- `/usages?tab=pilotage`
- `/action-center-v4`
- `/bill-intel`

Utilise `domcontentloaded` + settle 500 ms au lieu de `networkidle`
(qui saturait le BE pendant la suite et provoquait des timeouts
sur les login retry des runs suivants).

---

## 3. Helper login robuste

`auth.setup.spec.js` enchaîne 3 garde-fous :

1. **`waitForBackendReady(maxWaitSec=30)`** : poll `/api/health` toutes
   les 1.5s jusqu'à 200 ou timeout 30s. Évite le faux échec en cold start
   uvicorn (~10s sur cette machine).
2. **`loginWithRetry(attempts=3)`** : backoff exponentiel 0/1/3/10s
   entre tentatives. Timeout 20s par tentative (large marge BE chargé).
3. **Smoke `/api/auth/me`** : vérifie que le token reçu donne accès à
   un endpoint authentifié avant de sauvegarder le storageState.

Aucun `setTimeout` arbitraire long dans les specs — uniquement dans le
setup et borné par les paramètres ci-dessus.

---

## 4. Commandes pour lancer

### Pré-requis stack

```bash
# Backend (Python 3.11 venv)
cd ~/projects/promeos-poc/backend
source .venv/bin/activate
nohup python main.py > /tmp/promeos-be.log 2>&1 &

# Frontend (Vite)
cd ~/projects/promeos-poc/frontend
nohup npx vite --port 5173 --host 127.0.0.1 > /tmp/promeos-fe.log 2>&1 &

# Attendre ready
until curl -s -o /dev/null --max-time 2 -w "%{http_code}\n" \
  http://127.0.0.1:8001/api/health | grep -q "^200"; do sleep 2; done
until curl -s -o /dev/null --max-time 2 -w "%{http_code}\n" \
  http://127.0.0.1:5173/ | grep -q "^200"; do sleep 2; done
```

### Run Playwright

```bash
cd ~/projects/promeos-poc/e2e
npx playwright test golden-paths.spec.js s2-conformite-simplicite-metier.spec.js \
  --reporter=list --workers=1
```

Le project `setup` tourne automatiquement avant `chromium` (déclaration
`dependencies` dans `playwright.config.js`).

### Validation stabilité 2x

```bash
npx playwright test golden-paths.spec.js --reporter=list --workers=1 && \
npx playwright test golden-paths.spec.js --reporter=list --workers=1
```

---

## 5. Résultats

### Run #1 (post-stack-restart fresh)

```
✓ [setup] authenticate as promeos demo user (539 ms)
✓ /conformite rend sans erreur (697 ms)
✓ /usages?tab=pilotage rend sans erreur (660 ms)
✓ /action-center-v4 rend sans erreur (686 ms)
✓ /bill-intel rend sans erreur (665 ms)
✓ Item 8a · /conformite mode normal : tab Plan d'exécution ABSENT (294 ms)
✓ Item 8b · /conformite mode expert : tab Plan d'exécution PRESENT (653 ms)
✓ Item 9 · /conformite?tab=execution → /action-center-v4 (294 ms)
✓ Item 11 · /action-center-v4?domain=conformite : 0 console error · 0 4xx/5xx (6.3 s)

9 passed (12.4 s)
```

### Run #2 (immédiat après #1)

```
✓ [setup] authenticate as promeos demo user (373 ms)
✓ /conformite rend sans erreur (691 ms)
✓ /usages?tab=pilotage rend sans erreur (669 ms)
✓ /action-center-v4 rend sans erreur (665 ms)
✓ /bill-intel rend sans erreur (691 ms)
✓ Item 8a (278 ms)
✓ Item 8b (687 ms)
✓ Item 9 (287 ms)
✓ Item 11 (4.0 s)

9 passed (9.6 s)
```

**Critère « tests Playwright passent 2 fois de suite »** : ✅ validé.

### Régression produit

Aucune. Les changements sont strictement test infrastructure :
- 0 fichier produit (`backend/`, `frontend/src/`) modifié.
- 0 nouveau menu, 0 nouvelle route, 0 changement métier.

---

## 6. Hypothèses non retenues + alternatives écartées

| Alternative | Raison du rejet |
|---|---|
| Désactiver le rate-limit BE en env test | Contournement d'un garde-fou de sécurité — interdit par le brief. |
| `page.waitForTimeout(15_000)` dans la spec | « Wait arbitraire long » interdit par le brief. |
| Bypass via JWT en-dur dans le code de test | Risque sécurité (token committé) + couplage fragile sur la signature BE. |
| Lancer chaque spec avec `--workers=N` parallèle | Sature encore plus le rate-limiter. |
| `request` fixture Playwright | Provoque `Request context disposed` sur le project `setup` isolé. Remplacé par `fetch` natif Node. |

---

## 7. Limitations connues

- **TTL token JWT** : ~25-30 min. Suite Playwright qui dépasserait cette
  durée verrait des 401 en cours de run. Aujourd'hui le smoke complet
  tourne en < 1 min, donc safe. À reconsidérer si la suite grandit.
- **Cold start BE** : `waitForBackendReady` gère jusqu'à 30s. Si le
  démarrage prend plus (migrations lourdes, seed re-run), augmenter.
- **Specs legacy** : les 10 specs déjà sur `helpers.js::login()` continuent
  de fonctionner (le storageState ne casse pas leur login API direct,
  les deux mécanismes coexistent). Migration progressive possible en S4+.

---

## 8. Verdict

✅ **GO**

- 9/9 tests verts en run #1 (12.4 s).
- 9/9 tests verts en run #2 (9.6 s).
- Login non flakey : 0 « Identifiants incorrects » sur 2 runs consécutifs
  (vs 1/4 avant fix).
- Aucun changement produit.
- Audit livré.

**Suite suggérée** (hors scope ce sprint) :
- Migrer les 10 specs `helpers.js::login()` vers le storageState pour
  unifier (gain : suite Playwright complète plus rapide encore).
- Ajouter `playwright test --reporter=junit` + upload artefact en CI
  pour traçabilité des runs.
