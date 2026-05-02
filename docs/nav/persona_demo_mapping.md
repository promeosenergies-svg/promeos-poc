# Mapping Persona Démo PROMEOS — Navigation Rail

> **But** : éviter la confusion lors d'audits visuels du rail nav. L'ordre
> rendu dépend du `UserRole` du compte connecté.
>
> **Phase 3.E — P1.8** (2026-05-02) : le compte démo principal
> `promeos@promeos.io` a été réaligné `DG_OWNER → ENERGY_MANAGER` pour
> cohérence avec doctrine §2 (persona dominant Sol = Energy Manager) et
> le wedge MVP. L'ordre rail rendu correspond désormais à l'ordre
> `default` Sol v1.1.
>
> Référence audit : [docs/audits/nav_render_diagnosis_20260502.md](../audits/nav_render_diagnosis_20260502.md) (Phase 0.ter).

---

## 1. Comptes seedés (HELIOS demo)

| Email | UserRole | Source seed |
|---|---|---|
| `promeos@promeos.io` | `ENERGY_MANAGER` (Phase 3.E P1.8 — ex DG_OWNER) | [backend/services/demo_seed/orchestrator.py:1132](../../backend/services/demo_seed/orchestrator.py) |
| `m.leclerc@helios-energie.fr` | `ENERGY_MANAGER` | orchestrator.py |
| `j.dupont@helios-energie.fr` | `AUDITEUR` | orchestrator.py |
| `s.moreau@helios-energie.fr` | … | orchestrator.py |

→ Mot de passe demo (CLAUDE.md / MEMORY.md) : `promeos2024`

---

## 2. Conséquence sur le rail rendu

### 2.1 Ordre cible Sol v1.1 (= `default` = `energy_manager`)

```
Accueil → Énergie → Conformité → Facturation → Achat → [séparateur] → Patrimoine
```

Source : [NavRegistry.js:994 ROLE_MODULE_ORDER.default](../../frontend/src/layout/NavRegistry.js).

**À voir quand** :
- Mode déauth (DEMO_MODE actif sans login) → fallback `default` ([NavRail.jsx:58](../../frontend/src/layout/NavRail.jsx) `useAuth().role` = null → `getOrderedModules` fallback).
- Compte avec `UserRole.ENERGY_MANAGER` (à créer si besoin de QA visuel ciblé).

### 2.2 Ordre `dg_owner` (compte démo principal)

```
Accueil → Facturation → Achat → Conformité → Énergie → [séparateur] → Patrimoine
```

Source : [NavRegistry.js:983 ROLE_MODULE_ORDER.dg_owner](../../frontend/src/layout/NavRegistry.js).

**À voir quand** : login `promeos@promeos.io` (toutes captures de démo CFO/DG par défaut).

### 2.3 Tableau récapitulatif des 8 personas

| Persona | UserRole | Position 2 (module dominant) |
|---|---|---|
| `default` (no auth) | — | Énergie |
| `energy_manager` | ENERGY_MANAGER | Énergie |
| `daf` | DAF | Facturation |
| `dg_owner` | **DG_OWNER (demo principal)** | **Facturation** |
| `acheteur` | ACHETEUR | Achat |
| `resp_conformite` | RESP_CONFORMITE | Conformité |
| `resp_immobilier` | RESP_IMMOBILIER | Conformité |
| `resp_site` | RESP_SITE | Énergie |

→ Tous les personas ont **Patrimoine en dernière position visible** (séparateur graphique avant — `groupBoundary: 'config'` sur [NAV_MODULES.patrimoine](../../frontend/src/layout/NavRegistry.js)).

---

## 3. Comment vérifier le persona actif

3 méthodes :

1. **Backend `/api/auth/me`** retourne le `role` du user connecté.
2. **DevTools React** : inspection `AuthContext.role` ou `localStorage` (ScopeContext).
3. **Capture rail** : si l'ordre matche un des 8 above → persona identifié.

---

## 4. Stratégie QA multi-persona

Pattern Playwright role-swap déjà éprouvé en [P1.0 nav_p0_smoke.spec.mjs](../../tools/playwright/nav_p0_smoke.spec.mjs) :

```js
await page.route('**/api/auth/login', async (route) => {
  const body = JSON.parse((await route.request().postData()) || '{}');
  body.role = 'energy_manager'; // swap pour QA visuel
  await route.fulfill({
    contentType: 'application/json',
    body: JSON.stringify({ ..., role: body.role, token: 'mock-token' }),
  });
});
```

Captures recommandées (rotation persona) : `default`, `dg_owner`, `daf`,
`energy_manager`, `acheteur` — couvrent les 5 ordres distincts du rail.

---

## 5. Tests guard-rails associés

| Test | Niveau | Source |
|---|---|---|
| `SG_NAV_FE_05` | Source-guard statique | [nav_fe_source_guards.test.js](../../frontend/src/__tests__/source_guards/nav_fe_source_guards.test.js) — interdit la mutation `sort/reverse/filter/splice` de `getOrderedModules` dans NavRail |
| `Phase 3.D — P1.7 persona parity` (9 tests) | Logique pure `getOrderedModules` | [NavRegistry.test.js](../../frontend/src/layout/__tests__/NavRegistry.test.js) — assert position 2 par persona + Patrimoine last cross-cutting |
| `Phase 1.E — P0.5 ordre rail cible Sol v1.1` | Logique pure | NavRegistry.test.js — `default` exact + `default = energy_manager` + Patrimoine last forEach |

---

## 6. Références

- [docs/audits/navigation_audit_20260501.md](../audits/navigation_audit_20260501.md) — Phase 0 modules rail
- [docs/audits/navigation_panels_audit_20260502.md](../audits/navigation_panels_audit_20260502.md) — Phase 0.bis panels
- [docs/audits/nav_render_diagnosis_20260502.md](../audits/nav_render_diagnosis_20260502.md) — Phase 0.ter render diagnosis
- `ROLE_MODULE_ORDER` figé : commit `b7e25880` (P0.5)
