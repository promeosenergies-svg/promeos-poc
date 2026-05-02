---
audit: navigation_phase_0_ter_render_diagnosis
date: 2026-05-02
branch: claude/refonte-sol2
mode: read-only strict
phase_0_ref: docs/audits/navigation_audit_20260501.md
phase_0_bis_ref: docs/audits/navigation_panels_audit_20260502.md
auteur: Claude Code (Opus 4.7)
---

# AUDIT NAVIGATION — Phase 0.ter — Diagnostic ordre rail rendu

> **Capture observée 2026-05-02** : `Accueil → Facturation → Achat → Conformité → Énergie → [sep] → Patrimoine`
>
> **Hypothèses à trancher** :
> - **A** persona actif non-default
> - **B** régression rendu silencieuse non couverte par tests
> - **C** config NavRegistry modifiée par session parallèle

---

## 1. TL;DR

1. **✅ Hypothèse A confirmée** — l'utilisateur est connecté comme **`DG_OWNER`** (admin demo `promeos@promeos.io` seedé avec ce rôle dans [orchestrator.py:1126](backend/services/demo_seed/orchestrator.py#L1126)). L'ordre observé matche exactement `ROLE_MODULE_ORDER.dg_owner` ([NavRegistry.js:983](frontend/src/layout/NavRegistry.js#L983)) — **comportement attendu by design**.
2. **❌ Hypothèses B et C éliminées** — `git log b7e25880..HEAD -- frontend/src/layout/NavRegistry.js` retourne 2 commits documentés (P1.5 `ca813498` + P1.6 `b1b2869c`, hors `ROLE_MODULE_ORDER` et `NAV_MODULES`). Aucun fichier nav `M` au `git status`, aucun stash actif sur la branche.
3. **⚠️ Trou de couverture identifié** — les tests Vitest couvrent la logique `getOrderedModules` (NavRegistry.test.js:659-708) mais **aucun test ne valide le rendu DOM réel** de `NavRail` pour un persona donné. Si NavRail court-circuitait `getOrderedModules` (ex: tri inline), les tests resteraient verts. Recommandation **SG_NAV_FE_05** = "NavRail rend exactement `getOrderedModules(role, isExpert)` dans cet ordre".

---

## 2. Inventaire des 5 dimensions

### 2.1 Dimension 1 — État config NavRegistry actuelle

**Commits depuis P0.5 (b7e25880) sur NavRegistry.js** :
```
b1b2869c docs(nav-p1): Phase 3.C — P1.6 document HIDDEN_PAGES intentional masking + SG_NAV_FE_04
ca813498 chore(nav-p1): Phase 3.B — P1.5 retarget QuickAction /anomalies → /action-center (audit Phase 0.bis Q2)
```

→ 2 commits, **aucun ne touche `ROLE_MODULE_ORDER` ni `NAV_MODULES`**. Diff vérifié = QUICK_ACTIONS (P1.5) + HIDDEN_PAGES `reason` (P1.6).

**`NAV_MODULES` actuel** ([NavRegistry.js:208-262](frontend/src/layout/NavRegistry.js)) — 7 entrées :

| order | key | label | expertOnly |
|---|---|---|---|
| 1 | cockpit | Accueil | false |
| 2 | conformite | Conformité | false |
| 3 | energie | Énergie | false |
| 4 | patrimoine | Patrimoine (groupBoundary='config') | false |
| 5 | achat | Achat | false |
| 6 | facturation | Facturation (Phase 1.D) | false |
| 7 | admin | Administration | true |

**`ROLE_MODULE_ORDER` actuel** ([NavRegistry.js:981-995](frontend/src/layout/NavRegistry.js#L981-L995)) — 8 personas + default :

| Persona | Ordre |
|---|---|
| **dg_owner** | `cockpit → facturation → achat → conformite → energie → patrimoine` |
| daf | cockpit → facturation → conformite → energie → achat → patrimoine |
| acheteur | cockpit → achat → facturation → energie → conformite → patrimoine |
| energy_manager | cockpit → energie → conformite → facturation → achat → patrimoine |
| resp_conformite | cockpit → conformite → energie → facturation → achat → patrimoine |
| resp_immobilier | cockpit → conformite → energie → facturation → achat → patrimoine |
| resp_site | cockpit → energie → conformite → facturation → achat → patrimoine |
| **default** | **cockpit → energie → conformite → facturation → achat → patrimoine** (cible Sol v1.1) |

`groupBoundary: 'config'` présent sur patrimoine ([NavRegistry.js:252](frontend/src/layout/NavRegistry.js#L252)) ✅.

### 2.2 Dimension 2 — Logique sélection persona à runtime

**NavRail.jsx** ([NavRail.jsx:58](frontend/src/layout/NavRail.jsx#L58)) :
```jsx
const { role } = useAuth();
const visibleModules = getOrderedModules(role, isExpert);
```

**AuthContext.jsx** ([AuthContext.jsx:15-27](frontend/src/contexts/AuthContext.jsx)) :
```jsx
const [role, setRole] = useState(null);
// ...
setRole(data.role);  // après login, vient du backend
```

**Backend demo seed** ([orchestrator.py:1126](backend/services/demo_seed/orchestrator.py#L1126)) :
```python
{"email": "promeos@promeos.io", "nom": "Admin", "prenom": "Promeos", "role": UserRole.DG_OWNER}
```

**Source du rôle** :
1. Login backend retourne `role` du UserOrgRole
2. AuthContext stocke en state React (pas localStorage direct)
3. NavRail lit via `useAuth()`
4. `getOrderedModules(role, isExpert)` ([NavRegistry.js:1003-1009](frontend/src/layout/NavRegistry.js)) :
   ```js
   const order = ROLE_MODULE_ORDER[role] || ROLE_MODULE_ORDER.default;
   const byKey = Object.fromEntries(NAV_MODULES.map((m) => [m.key, m]));
   const ordered = order.map((key) => byKey[key]).filter(Boolean);
   if (isExpert && byKey.admin) ordered.push(byKey.admin);
   return ordered;
   ```

**Fallback** : si `role` est `null` ou inconnu → `ROLE_MODULE_ORDER.default` (= ordre Sol v1.1 cible).

### 2.3 Dimension 3 — Ordre rendu vs ordre config

**Capture observée** : `cockpit → facturation → achat → conformite → energie → patrimoine`

**Comparaison aux 8 ROLE_MODULE_ORDER** :

| Persona | Ordre persona | Match capture ? |
|---|---|---|
| **dg_owner** | `cockpit → facturation → achat → conformite → energie → patrimoine` | ✅ **MATCH 1:1** |
| daf | cockpit → facturation → conformite → energie → achat → patrimoine | ❌ pos 3-5 différents |
| acheteur | cockpit → achat → facturation → ... | ❌ pos 2 différent |
| energy_manager | cockpit → energie → conformite → facturation → achat → patrimoine | ❌ pos 2 différent |
| resp_conformite | cockpit → conformite → ... | ❌ pos 2 différent |
| resp_immobilier | cockpit → conformite → ... | ❌ pos 2 différent |
| resp_site | cockpit → energie → ... | ❌ pos 2 différent |
| default | cockpit → energie → conformite → facturation → achat → patrimoine | ❌ pos 2 différent |

→ **MATCH UNIQUE : `dg_owner`**.

### 2.4 Dimension 4 — Tests d'ordre — couverture réelle

**Tests existants** ([NavRegistry.test.js:659-708](frontend/src/layout/__tests__/NavRegistry.test.js)) :

| Test | Scope | Niveau |
|---|---|---|
| `Patrimoine est la dernière position visible pour persona '${role}'` (8×) | Logique pure `getOrderedModules` | ✅ Tous personas |
| `default order = Accueil → Énergie → Conformité → Facturation → Achat → Patrimoine` | Logique pure default | ✅ |
| `default ordre identique à 'energy_manager'` | Logique pure equality | ✅ |
| `daf : Facturation est en position 2` | Logique pure DAF | ⚠️ Seul test position spécifique |
| `persona '${role}' expose 6 modules visibles uniques` (8×) | Logique pure unicité | ✅ |
| `expert mode : admin ajouté en queue` | Logique pure expert | ✅ |
| `NavRail uses getOrderedModules` ([expertMode.test.js:101](frontend/src/__tests__/expertMode.test.js)) | Source-guard `expect(src).toContain('getOrderedModules')` | ⚠️ String match seul |

**Trou de couverture** :
- ❌ **Pas de test rendu DOM** qui assert que NavRail produit un `<nav>` avec items dans l'ordre attendu pour un persona donné.
- ❌ **Pas de test position spécifique pour `dg_owner` Facturation #2** (le test DAF existe mais pas DG).
- ⚠️ Si NavRail.jsx faisait `visibleModules.sort(...)` ou `.reverse()` inline, les 14 tests `getOrderedModules` resteraient verts (ils testent la logique pure, pas le rendu).

**Mécanisme de mock** : aucun. Les tests utilisent directement `getOrderedModules(role, isExpert)` sans render React (env=node, convention repo source-guard).

**SG_NAV_FE_03** ([nav_fe_source_guards.test.js:212-233](frontend/src/__tests__/source_guards/nav_fe_source_guards.test.js)) : whitelist consommateurs `useNavigationBadges` — **n'a pas vocation à valider l'ordre rendu**.

### 2.5 Dimension 5 — Session parallèle vérification

| Check | Résultat |
|---|---|
| `git status` (fichiers nav `M`) | ❌ aucun (les `M` listés sont `backend/database/migrations.py`, `docs/audit/`, `docs/sprints/SPRINT_RETRO_COCKPIT_DUAL_SOL2/outputs/*` — préexistants, hors scope nav) |
| `git stash list` | 4 stashes anciens, aucun WIP nav (sprint2-vagueB, agents-kb, sol-refonte, fix-site-compliance) |
| `ps aux | grep claude` | Plusieurs sessions VSCode actives mais aucune ne semble écrire actuellement sur nav files |
| Session courante | PID 86849 (cette session) — la seule qui aurait pu modifier NavRegistry, et elle n'a pas touché ROLE_MODULE_ORDER |

→ **Aucune session parallèle n'a modifié les fichiers nav** sur les dernières heures.

---

## 3. Verdict sur les 3 hypothèses

### ✅ Hypothèse A — persona actif non-default — **CONFIRMÉE**

**Preuves** :
1. ROLE_MODULE_ORDER.dg_owner ([NavRegistry.js:983](frontend/src/layout/NavRegistry.js#L983)) = `['cockpit', 'facturation', 'achat', 'conformite', 'energie', 'patrimoine']` — match exact capture.
2. Demo admin `promeos@promeos.io` seedé `UserRole.DG_OWNER` ([orchestrator.py:1126](backend/services/demo_seed/orchestrator.py#L1126)).
3. AuthContext stocke `role` après login ([AuthContext.jsx:27](frontend/src/contexts/AuthContext.jsx#L27)).
4. NavRail lit `role` via `useAuth()` ([NavRail.jsx:58](frontend/src/layout/NavRail.jsx#L58)) et appelle `getOrderedModules(role, isExpert)`.
5. `getOrderedModules('dg_owner', false)` retourne l'ordre observé.

→ **Comportement par design**. L'ordre cible Sol v1.1 (P0.5) est l'ordre **`default`** (= `energy_manager`). Le persona DG_OWNER a sa propre matrice (Direction/finance focus décisionnel).

### ❌ Hypothèse B — régression rendu silencieuse — ÉLIMINÉE

`getOrderedModules` est utilisée telle quelle par NavRail ([NavRail.jsx:58](frontend/src/layout/NavRail.jsx#L58)). Aucun tri inline détecté. Les tests Vitest sur la logique sont verts (4 409 / 2 skipped).

### ❌ Hypothèse C — modif silencieuse session parallèle — ÉLIMINÉE

`git log b7e25880..HEAD -- frontend/src/layout/NavRegistry.js` ne montre que les 2 commits documentés (P1.5 + P1.6). Diff vérifié n'a touché ni ROLE_MODULE_ORDER ni NAV_MODULES. Pas de fichier nav `M` ni stash WIP nav actif.

---

## 4. Confirmation persona actif + capture multi-persona recommandée

### 4.1 Comment vérifier le persona actif côté utilisateur

3 méthodes :
1. **Backend `/api/auth/me`** : retourne le `role` du user connecté.
2. **DevTools Console** : `window.localStorage` (cf. ScopeContext) ou inspection React DevTools `AuthContext.role`.
3. **Capture rail** : si l'ordre matche `dg_owner` → confirmé.

### 4.2 Captures multi-persona recommandées

Pour valider visuellement le multi-persona en futur audit / démo :

| Persona | URL démo | Ordre attendu rail |
|---|---|---|
| dg_owner | (login admin demo) | `cockpit → facturation → achat → conformite → energie → patrimoine` (capture actuelle ✅) |
| daf | login DAF demo | `cockpit → facturation → conformite → energie → achat → patrimoine` |
| energy_manager | login EM demo | `cockpit → energie → conformite → facturation → achat → patrimoine` (= default) |
| default (no auth, DEMO_MODE) | logout + visit | `cockpit → energie → conformite → facturation → achat → patrimoine` (cible Sol v1.1) |

→ **Stratégie Playwright `page.route('**/api/auth/login')` swap role en mémoire** déjà utilisée en P1.0 ([nav_p0_smoke.spec.mjs](tools/playwright/nav_p0_smoke.spec.mjs)) — appliquer pour ces 4 personas en captures séparées.

---

## 5. Trou de couverture tests — Recommandation SG_NAV_FE_05

### 5.1 Constat

Les tests existants valident **la logique pure** `getOrderedModules` (pure function in/out) mais **pas le rendu DOM rail**. Si un futur changement faisait :

```jsx
// Hypothèse régression future :
const visibleModules = getOrderedModules(role, isExpert);
const sortedModules = [...visibleModules].sort((a, b) => a.label.localeCompare(b.label));
return sortedModules.map(...);
```

→ Les 14 tests `getOrderedModules` resteraient verts, mais le rail rendrait dans l'ordre alphabétique (régression silencieuse).

### 5.2 SG_NAV_FE_05 proposé

```js
// SG_NAV_FE_05 — NavRail rend exactement getOrderedModules sans tri additionnel
describe('SG_NAV_FE_05 — NavRail order matches getOrderedModules output', () => {
  it('NavRail.jsx ne tri/inverse/filtre PAS visibleModules après getOrderedModules', () => {
    const src = readNavFile('layout/NavRail.jsx');
    // Cherche les patterns de manipulation d'ordre POST getOrderedModules :
    const FORBIDDEN = [
      /visibleModules\.sort\(/,
      /visibleModules\.reverse\(/,
      /visibleModules\.filter\(/, // filter possible mais à challenger
      /\.sort\([^)]*\)\s*\.map/,
    ];
    for (const pattern of FORBIDDEN) {
      expect(src).not.toMatch(pattern);
    }
  });
});
```

**Niveau** : source-guard statique (cohérent avec SG_NAV_FE_01-04 pattern repo). Pas de DOM render (env=node, pas testing-library).

**Niveau supérieur (P2 backlog)** : test E2E Playwright avec role swap → assert ordre des `aria-label` modules dans le `<nav>`. Couverture rendering réelle. Hors scope source-guard simple.

---

## 6. Questions ouvertes (max 3)

1. **L'ordre observé est correct (DG_OWNER by design). Le user attendait-il l'ordre default Sol v1.1 ?** Si oui → mécompréhension du multi-persona. Si non → audit clos sur Hypothèse A confirmée.

2. **Faut-il poser SG_NAV_FE_05 (anti-régression rendu rail) maintenant ?** Coût marginal très faible (~10 LOC), bénéfice : verrou statique + alignement avec SG_NAV_FE_01-04.

3. **Faut-il enrichir le test `dg_owner: Facturation est en position 2` (manquant côté tests, alors que `daf:Facturation #2` existe) ?** Fait sens parité multi-persona — 1 ligne à ajouter dans NavRegistry.test.js.

---

## 7. STOP — Hard Gate Phase 0.ter

**Phase 0.ter read-only terminée.** Aucune modification de code/config/test.

**Verdict** : Hypothèse A confirmée — comportement by design (multi-persona). Aucun bug, aucune régression. Trou de couverture tests identifié (rendu DOM non couvert).

**Livrable unique** : [docs/audits/nav_render_diagnosis_20260502.md](docs/audits/nav_render_diagnosis_20260502.md) (ce fichier).

**git status** : modifs `M` préexistantes hors scope nav uniquement (vérifiées dim. 5).

→ **Aucune Phase corrective lancée tant que GO non donné.**

---

## Annexes

### A. Stratégie Playwright role swap (rappel P1.0)

```js
// tools/playwright/nav_p0_smoke.spec.mjs (référence)
await page.route('**/api/auth/login', async (route) => {
  const body = JSON.parse((await route.request().postData()) || '{}');
  body.role = 'energy_manager'; // swap
  await route.fulfill({
    contentType: 'application/json',
    body: JSON.stringify({ ..., role: body.role, token: 'mock-token' }),
  });
});
```

À répliquer pour 4 captures multi-persona si besoin de QA visuel multi-rôles.

### B. Paramètres audit

- **Branche** : `claude/refonte-sol2`
- **Date** : 2026-05-02
- **Mode** : read-only strict
- **Outil** : Claude Code Opus 4.7 (1M context)
- **Bases analysées** : NavRegistry.js (1093 LOC), NavRail.jsx, AuthContext.jsx, orchestrator.py (seed admin), tests Vitest, git log/stash/ps
