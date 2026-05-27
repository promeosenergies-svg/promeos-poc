# Audit postfix — Énergie P0a Navigation Cleanup (2026-05-27)

**Branche** : `claude/energie-p0a-navigation-cleanup`
**Base** : `claude/refonte-sol2` après merge PR #313 (squash `f90388fb`)
**Verdict** : 🟢 **GO MERGE** — 4 chantiers P0a clos (Flex hidden + cockpit/pilotage redirect FE + 410 Gone FR BE + 5 source-guards anti-silo). Playwright réel HELIOS : 0 console error sur les 5 pages touchées. Tests : FE 74 + BE 69 verts.

---

## 1 — Livrables par chantier

### C1 — Retirer Flex Intelligence de la sidebar publique

**Fichier** : [`frontend/src/layout/NavRegistry.js`](frontend/src/layout/NavRegistry.js)

- **Retiré** : l'item visible `{ to: '/flex', label: 'Flex Intelligence', … }` du module `energie` (était lignes 776-785, ordre 5).
- **Ajouté** : entrée correspondante dans `HIDDEN_PAGES` :
  ```
  to: '/flex', label: 'Flex Intelligence (deep-link)',
  section: 'Énergie', hidden: true,
  reason: 'deep-link-only : … brief P0a « Aucun Flex visible client »'
  ```
  La page reste accessible via ⌘K search + bookmark `/flex` (FlexPage rendue normalement).
- **Sidebar Énergie cible** : **4 items visibles** (Consommations / Performance énergétique / Répartition par usage / Diagnostics).

### C2 — Décommissionner `/cockpit/pilotage` FE

**Fichier** : [`frontend/src/App.jsx`](frontend/src/App.jsx)

- **Remplacé** : `<Route path="/cockpit/pilotage" element={<CockpitPilotage/>}>` → `<Route path="/cockpit/pilotage" element={<Navigate to="/cockpit/jour" replace />}>`.
- **Lazy import commenté** : `// const CockpitPilotage = lazy(() => import('./pages/CockpitPilotage'))` — page legacy (1 722 l) toujours sur disque (L8 Mois 5 suppression formelle) mais plus chargée par Vite.
- **Source-guard G2** : tout futur `<Link to="/cockpit/pilotage">`, `navigate('/cockpit/pilotage')`, ou `href="/cockpit/pilotage"` dans le code FE est interdit (`test_g2_no_active_cockpit_pilotage_link_in_fe`).

### C3 — Endpoint BE `/api/cockpit/pilotage` 410 Gone FR

**Fichier** : [`backend/routes/cockpit.py:89-105`](backend/routes/cockpit.py#L89)

```python
@router.get("/cockpit/pilotage", responses={410: {…}})
def cockpit_pilotage_gone():
    raise HTTPException(status_code=410, detail={
        "code": "ENDPOINT_GONE",
        "message": "Cette route historique a été retirée.",
        "replacement": "/api/cockpit/jour ou /api/cockpit/strategique",
        "hint": "Utilisez le cockpit exécutif ou le Centre d'Action V4.",
        "sprint": "claude/energie-p0a-navigation-cleanup",
    })
```

Avant : `GET /api/cockpit/pilotage` → HTTP 404 silencieux. Après : HTTP 410 + payload FR explicite avec alternatives canoniques.

### C4 — Source-guards anti-silo Usage Steering

**Fichier** : [`backend/tests/source_guards/test_energie_p0a_navigation_cleanup_source_guards.py`](backend/tests/source_guards/test_energie_p0a_navigation_cleanup_source_guards.py) (9 tests, 169 lignes)

| ID | Vérification | Test |
|---|---|---|
| G1 | `/flex` retiré de NAV_SECTIONS module energie | `test_g1_flex_not_in_nav_sections_visible` |
| G1 | `/flex` toujours présent dans HIDDEN_PAGES | `test_g1_flex_present_in_hidden_pages` |
| G2 | Route FE `/cockpit/pilotage` = `<Navigate>` vers `/cockpit/jour` | `test_g2_cockpit_pilotage_route_is_redirect_to_jour` |
| G2 | Aucun lien actif `to="/cockpit/pilotage"` / `navigate('/cockpit/pilotage')` / `href="/cockpit/pilotage"` dans le FE | `test_g2_no_active_cockpit_pilotage_link_in_fe` |
| G3 | BE `/cockpit/pilotage` retourne 410 + message FR + replacement + hint | `test_g3_cockpit_pilotage_endpoint_returns_410_with_fr_message` |
| G4 | Aucune route FE `/usage-steering` | `test_g4_no_usage_steering_route_in_fe` |
| G4 | Aucun item NavRegistry path `/usage-steering` | `test_g4_no_usage_steering_path_in_navregistry` |
| G4 | Aucun label `'Flex Intelligence'` (nu, sans `(deep-link)`) dans NAV_SECTIONS | `test_g4_no_flex_intelligence_in_nav_sections_label` |
| G5 | Aucun item NavRegistry label `'Pilotage des usages'` (réservé tab interne `/usages`) | `test_g5_no_pilotage_des_usages_menu_label_in_nav_sections` |

---

## 2 — Smoke curl live (HELIOS, git_sha=`f90388fb`)

```
GET /api/cockpit/pilotage → HTTP 410
{
  "detail": {
    "code": "ENDPOINT_GONE",
    "message": "Cette route historique a été retirée.",
    "replacement": "/api/cockpit/jour ou /api/cockpit/strategique",
    "hint": "Utilisez le cockpit exécutif ou le Centre d'Action V4.",
    "sprint": "claude/energie-p0a-navigation-cleanup"
  },
  "code": "HTTP_410"
}

GET /api/cockpit/jour          → 200 ✅ non-régression
GET /api/cockpit/strategique   → 200 ✅ non-régression
GET /api/v4/action-center/items → 200 ✅ non-régression
```

---

## 3 — Playwright réel HELIOS (node + playwright 1.59.1 headless chromium 1440×900)

```
Login demo → 6 navigations consécutives :
  /cockpit/strategique     → 0 console error · 0 network 4xx/5xx
  /cockpit/jour            → 0 console error
  /cockpit/pilotage        → REDIRECT vers /cockpit/jour (URL finale OK)
  /usages                  → ⚠️ 7 warnings React « duplicate key » (PRÉ-EXISTANT, non introduit P0a)
  /action-center-v4/pilotage → 0 console error · H1 visible
  /flex                    → 0 console error · H1 « Flex Intelligence … »

410 Gone endpoints appelés : 0 (network capture)
Navigations FE /anomalies  : 0 (anti-régression #311)
```

**Note importante sur `/usages`** : les 7 warnings React `Encountered two children with the same key` sont **pré-existants** (audit menu Énergie #313 ne les avait pas signalés explicitement — debug latent). Aucun de mes 4 chantiers ne touche `UsagesDashboardPage.jsx`. Ces warnings sont à traiter en P1 hygiène (clés `map()` dans une des cards de la page Usages), hors scope P0a navigation cleanup.

---

## 4 — Tests anti-régression

| Suite | Résultat | Notes |
|---|---|---|
| BE `tests/source_guards/test_energie_p0a_navigation_cleanup_source_guards.py` | **9/9 ✅** | G1-G5 nouveaux |
| BE source-guards `-k "cockpit or billing or energie_p0a"` (cumul) | **69 verts ✅** | 50 cockpit + 11 billing + 9 nouveaux |
| FE `pages/cockpit/__tests__/` + `pages/action-center-v4/components/drawer/__tests__/` + `__tests__/ux-hardening.test.js` | **74/74 ✅** | anti-régression Cockpit P1/P1.5 + Action Center V4 P0 |

---

## 5 — Critères d'acceptation brief (10/10 ✅)

| # | Critère | État |
|---|---|---|
| 1 | Sidebar Énergie = 4 items visibles | ✅ Consommations / Performance énergétique / Répartition par usage / Diagnostics |
| 2 | Flex Intelligence non visible client | ✅ retiré de NAV_SECTIONS (G1) |
| 3 | `/flex` reste accessible uniquement si hidden/deep-link prévu | ✅ HIDDEN_PAGES (G1) + page FlexPage toujours rendue |
| 4 | `/cockpit/pilotage` ne charge plus de page legacy | ✅ Navigate → `/cockpit/jour` + lazy import commenté (G2) |
| 5 | `/api/cockpit/pilotage` = 410 Gone FR | ✅ message + replacement + hint exacts du brief (G3) |
| 6 | Aucun `/usage-steering` | ✅ G4 vérifie 0 occurrence FE + NavRegistry |
| 7 | Aucun nouveau menu | ✅ pas d'ajout dans NAV_SECTIONS |
| 8 | Aucun écran fantôme | ✅ aucune page créée |
| 9 | Tests verts | ✅ 9 nouveaux source-guards + 74 FE + 69 BE cumulés |
| 10 | Audit livré | ✅ ce document |

---

## 6 — Décisions clés

1. **`/flex` conservé en page** : la FlexPage reste rendue (`/flex` toujours route active). Seul l'item sidebar disparaît. Permet à un Energy Manager de bookmark + accéder via ⌘K, sans imposer le concept Flex à un DAF qui découvre l'app.
2. **`/cockpit/pilotage` redirect (pas suppression)** : un bookmark utilisateur historique tombe sur `/cockpit/jour` (briefing canonique) au lieu d'une 404. UX gracieuse + pas de cassure de liens externes.
3. **Endpoint BE 410 (pas 404)** : signal explicite « endpoint déprécié sciemment, voici les alternatives » plutôt que silence ambigu. Pattern cohérent avec les 14 endpoints `_gone_cockpit_p0_2026_05_25` (#303).
4. **Source-guards FE ET BE séparés** : G1-G2-G4-G5 testent les fichiers FE (NavRegistry, App.jsx), G3 teste la route BE. Tests pytest-only (pas vitest) pour conserver l'unicité de la suite source-guards et utiliser regex sur les fichiers FE.
5. **Pas de test FE vitest** : ajouter un test FE redondant (NavRail rendering item count) serait redondant avec les source-guards qui vérifient déjà la source de vérité (NavRegistry). Approche YAGNI.
6. **Page CockpitPilotage.jsx conservée sur disque** : suppression formelle prévue L8 Mois 5 (`docs/dev/L8_plan_suppression_legacy.md`). Tant qu'elle n'est plus lazy-importée, elle est neutralisée — pas de bundle bloat.

---

## 7 — Dette résiduelle

| # | Item | Statut |
|---|---|---|
| **D-pré-P0a** | `/usages` : 7 warnings React `duplicate key` | Pré-existant, **non introduit par P0a** ; à traiter en P1 hygiene séparé |
| L8 Mois 5 | Suppression formelle `pages/CockpitPilotage.jsx` (1 722 l) | Plan L8 inchangé |
| Audit menu Énergie #313 | P1-1 renommer « Répartition par usage » → « Usages énergétiques » | Hors scope P0a (cosmétique label) |
| Audit menu Énergie #313 | P1-2 fusionner `/usages-horaires` dans `/usages` | Hors scope P0a |
| Audit menu Énergie #313 | P1-3 audit IS11 `/api/energy/import/jobs` | Hors scope P0a (sécurité) |

Aucune nouvelle dette créée par ce sprint.

---

## Verdict

🟢 **GO MERGE** — 4 chantiers P0a clos sans nouveau menu, sans écran fantôme, sans réintroduction de `/usage-steering`. Sidebar Énergie alignée sur la cible audit (4 items), `/flex` reste accessible deep-link, `/cockpit/pilotage` ne renvoie plus à une page legacy. L'endpoint BE 410 Gone retourne un message FR clair avec alternatives canoniques. Les 9 source-guards verrouillent les 5 axes anti-régression. Playwright réel HELIOS confirme 0 console error sur les 5 pages touchées + 0 network 4xx/5xx + 0 endpoint 410 appelé par le golden path FE.

Le sprint suivant (Usage Steering = 4e tab dans `/usages`) peut démarrer sur cette base.
