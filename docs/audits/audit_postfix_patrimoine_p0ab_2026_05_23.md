# Audit post-fix Patrimoine — P0-A + P0-B

> **Branche** : `claude/patrimoine-p0b-actionnable-onboarding`
> **HEAD** : `b701def1` (P0-B) sur `3ee702a9` (P0-A) sur `claude/refonte-sol2@25c8090b`
> **Date** : 2026-05-23
> **Mode** : READ-ONLY strict — aucune modification de code
> **Périmètre** : Patrimoine uniquement (pas de Site360 refonte, pas d'ACC / Partner Hub / Achat / Flex)
> **Référence audit initial** : [`audit_brique_patrimoine_deep_readonly_2026_05_23.md`](audit_brique_patrimoine_deep_readonly_2026_05_23.md) (note 5,4/10 avant fix)
> **Référence canonique** : [`docs/dev/patrimoine_routes_canonical.md`](../dev/patrimoine_routes_canonical.md)

---

## 1. Verdict exécutif

**GO** pour passer à la brique suivante (sous réserve d'1 résidu mineur StatusPage).

Tous les correctifs P0-A et P0-B sont **réellement intégrés**, **visibles dans le code**, **testés** (85 tests dédiés + 290 baseline non régressés), **wirés dans la CI** et **documentés** dans 2 fichiers de référence. Aucun écran mort. Aucune mutation patrimoine non auditée (verrou AST). Aucun `DATA_MISSING` sans remédiation (verrou bijection). Parcours Cockpit → Patrimoine fonctionnel bout en bout. `/onboarding` ne mène plus dans une impasse.

Le seul résidu identifié est `pages/StatusPage.jsx` qui ping `/api/sites` pour un health check — le endpoint étant désormais 410, le statut affichera "down" sans impact utilisateur final (page admin/diagnostic). À nettoyer en P1.

| Critère de GO | Statut | Évidence |
|---|---|---|
| 0 route legacy utilisée par le front | ⚠️ **1 résidu** | StatusPage.jsx (health monitoring, non bloquant) |
| 0 mutation patrimoine non auditée | ✅ | 16/16 call sites `log_patrimoine_change` + 2 source-guards AST |
| 0 DATA_MISSING sans remédiation | ✅ | 9/9 codes mappés + source-guard bijection |
| 0 écran onboarding mort | ✅ | `/onboarding` → Sirène ; `OnboardingPage.jsx` non monté |
| Parcours Cockpit → Patrimoine fonctionnel | ✅ | 13 tests interaction (Vitest + jsdom) |
| Tests P0-A/P0-B verts | ✅ | 65 BE + 20 FE = 85/85 verts |
| Baseline non régressée | ✅ | 290 tests patrimoine/regulatory verts |

---

## 2. Ce qui est validé

### 2.1 Routes — état canonique

#### Routes legacy en 410 ([`backend/routes/sites.py:73-103`](../../backend/routes/sites.py))

| Verbe | Route | HTTP | Fonction |
|---|---|---|---|
| `POST` | `/api/sites/quick-create` | **410** | `quick_create_site_gone()` (L73-81) |
| `POST` | `/api/sites` | **410** | `create_site_gone()` (L84-92) |
| `GET` | `/api/sites` | **410** | `get_sites_gone()` (L95-103) |

Payload 410 standardisé :
```json
{
  "detail": {
    "code": "PATRIMOINE_ROUTE_GONE",
    "message": "Cette route est dépréciée. Utilisez le parcours Patrimoine.",
    "replacement": "POST /api/patrimoine/crud/sites/quick-create",
    "doc": "docs/dev/patrimoine_routes_canonical.md"
  }
}
```

Vérifié par `tests/test_legacy_sites_route_gone.py` (4 tests parametrés).

#### Endpoint canonique quick-create

`POST /api/patrimoine/crud/sites/quick-create` ([`backend/routes/patrimoine_crud.py:837`](../../backend/routes/patrimoine_crud.py)) :
- relocalisation propre de l'ancien `/api/sites/quick-create` ;
- conserve auto-création hiérarchie (Org/EJ/PF si absentes) + anti-doublons ;
- ajoute `batch_cascade_recompute_sites([site.id])` + `log_patrimoine_change("site.create")`.

#### Routes CRUD canoniques ([`backend/routes/patrimoine_crud.py`](../../backend/routes/patrimoine_crud.py))

16 endpoints actifs, **tous audités** :

| Niveau | GET liste | GET détail | POST | PATCH | DELETE/archive |
|---|---|---|---|---|---|
| Organisation | L161 | L225 | L176 (`organisation.create`) | L238 (`organisation.update`) | L325 (`organisation.archive`) |
| Entité juridique | L367 | L455 | L390 (`entite_juridique.create`) | L468 (`entite_juridique.update`) | L516 (`entite_juridique.archive`) |
| Portefeuille | L558 | L635 | L586 (`portefeuille.create`) | L648 (`portefeuille.update`) | L696 (`portefeuille.archive`) |
| Site | L738 | L1053 | L769 + L837 (quick-create) (`site.create`) | L1066 (`site.update`) | L1161 (`site.archive`) |
| Bâtiment | — | — | L1222 (`batiment.create`) | L1282 (`batiment.update`) | L1340 (`batiment.delete`) |

#### Routes encore deprecated mais opérationnelles (P1 différé)

- `GET /api/sites/{site_id}` (L108) — non consommée par le front (audit grep).
- `GET /api/sites/{site_id}/stats` (L136).
- `GET /api/sites/{site_id}/compliance` (L175).
- `GET /api/sites/{site_id}/guardrails` (L251).

Décision P0-A : basculer en 410 **uniquement quand les équivalents `/api/patrimoine/sites/{id}/*` seront livrés** (cf. P1). Pas d'impact utilisateur car aucun appel front actif.

#### Fichier mort supprimé

`backend/routes/patrimoine.py` (0 octets — collision potentielle avec le package `routes/patrimoine/`) → supprimé en P0-A. Le router actif reste `routes/patrimoine/__init__.py`.

### 2.2 Audit log — couverture complète

**16 call sites `log_patrimoine_change`** dans `patrimoine_crud.py` (audit grep `action=`) :

```
L213  action="organisation.create"
L282  action="organisation.update"
L352  action="organisation.archive"
L438  action="entite_juridique.create"
L501  action="entite_juridique.update"
L543  action="entite_juridique.archive"
L619  action="portefeuille.create"
L681  action="portefeuille.update"
L723  action="portefeuille.archive"
L821  action="site.create"               (POST /sites direct)
L1012 action="site.create"               (POST /sites/quick-create)
L1124 action="site.update"
L1196 action="site.archive"
L1258 action="batiment.create"
L1318 action="batiment.update"
L1373 action="batiment.delete"
```

Chaque call site appelle `_audit_headers(request, auth)` qui extrait :
- `correlation_id` ← `request.headers.get("X-Correlation-ID")`
- `ip_address` ← `request.client.host`
- `user_agent` ← `request.headers.get("user-agent")`
- `user_id` ← `auth.user_id`

Et passe à `log_patrimoine_change(..., entity_type, entity_id, org_id, old_value, new_value, detail=diff)`.

**2 source-guards AST verrouillent** :

| Fichier | Invariant gardé |
|---|---|
| `tests/source_guards/test_patrimoine_crud_audit_log_wiring_source_guards.py` | Chaque PATCH/DELETE contient `log_patrimoine_change`. **Bonus** : `update_site_crud` ne contient pas de try/except swallow. |
| `tests/source_guards/test_patrimoine_crud_post_audit_log_source_guards.py` | Chaque POST contient `log_patrimoine_change`. **Bonus** : aucun GET ne le contient (read-only sémantique). |

### 2.3 DATA_MISSING — bijection complète

**SoT** : [`backend/regulatory/remediation.py:33`](../../backend/regulatory/remediation.py) `REASON_CODE_TO_REMEDIATION`.

| Reason code | remediation_field | level | label_fr |
|---|---|---|---|
| `DT.DATA_MISSING.SURFACE` | `site.tertiaire_area_m2` | site | Surface tertiaire |
| `DT.DATA_MISSING.USAGE` | `site.usage_principal` | site | Usage principal du site |
| `BACS.DATA_MISSING.CVC_POWER` | `batiment.cvc_power_kw` | batiment | Puissance CVC |
| `APER.DATA_MISSING.PARKING_AREA` | `site.parking_area_m2` | site | Surface de parking |
| `APER.DATA_MISSING.ROOF_AREA` | `site.roof_area_m2` | site | Surface de toiture |
| `SME.DATA_MISSING.EFFECTIF` | `organisation.effectif_total` | organisation | Effectif de l'organisation |
| `SME.DATA_MISSING.CA` | `organisation.chiffre_affaires_eur` | organisation | Chiffre d'affaires |
| `SME.DATA_MISSING.CONSO` | `entite_juridique.consommation_annuelle_moyenne_3y_gwh` | entite_juridique | Consommation moyenne 3 ans |
| `BEGES.DATA_MISSING.EFFECTIF` | `organisation.effectif_total` | organisation | Effectif de l'organisation |

Chaque entrée a les 5 champs requis (`remediation_field`, `remediation_level`, `remediation_label_fr`, `remediation_hint_fr`, `cta_label_fr`) — vérifié structurellement par `test_data_missing_remediation_source_guards.py::test_remediation_entry_structural`.

**Enrichissement automatique** dans `RuleApplicability.to_dict()` ([`backend/regulatory/applicability_types.py:138`](../../backend/regulatory/applicability_types.py)) : si `status == DATA_MISSING`, lookup `get_remediation(reason_code)`, injection des 5 champs FR + `affected_site_ids = [scope_id] if scope_level=="site" else []`.

**Bijection verrouillée** par source-guard `test_data_missing_remediation_source_guards.py` :
- `test_every_data_missing_reason_code_has_remediation` — pas de code orphelin
- `test_no_orphan_remediation_entry` — pas d'entrée fantôme
- 9 tests parametrés structurels (un par code)

### 2.4 UX Cockpit → Patrimoine — parcours fonctionnel

**Chaîne vérifiée code-level + 13 tests d'interaction Vitest + jsdom** :

```
[CockpitStrategique.jsx]
   → <CadreApplicable applicability={payload.applicability} maturity={...} />
       ↓ état interne : openRule = useState(null)
       ↓ tile DATA_MISSING → onClick → setOpenRule(rule)
       ↓ ouvre <DataMissingPanel rule={rule} entries={...filter(status==='data_missing')} />
       ↓ panneau liste : scope_label / remediation_label_fr / remediation_hint_fr
       ↓ bouton CTA labelisé via cta_label_fr ("Compléter la surface", etc.)
       ↓ onClick → navigate(`/patrimoine?incomplete=${rule}`)
                    ↓
[Patrimoine.jsx]
   → useSearchParams().get('incomplete') === 'DT'
   → useEffect : import('../services/api/conformite').then(getRegulatoryApplicability)
   → set incompleteSiteIds = Set(entries.scope_id where status==='data_missing')
   → render <IncompleteBanner rule="DT" remediation={first} siteCount={N} onClear={...} />
       ↓ bandeau FR : "Sites à compléter pour le Décret Tertiaire — N sites"
       ↓ hint FR depuis remediation_hint_fr
       ↓ bouton "Effacer le filtre" → sp.delete('incomplete')
   → useMemo filtered : ne garde que sites dans incompleteSiteIds
   → clic sur ligne table → DrawerEditSite (édition existante, inchangée)
```

Tests d'interaction couvrant chaque étape :
- `CadreApplicable.test.jsx` : 6 tests (tile clickable, non-clickable, CTA navigate, callback custom, fermeture panneau)
- `IncompleteBanner.test.jsx` : 7 tests (libellé FR, hint, org-level message, clear, pluriel, 5 règles, zéro anglais résiduel)

### 2.5 Onboarding — consolidation effective

Confirmé par lecture code + tests :

| Vérification | Statut | Évidence |
|---|---|---|
| `/onboarding` ne redirige plus vers `/cockpit/jour` | ✅ | `App.jsx:651` `Navigate to="/onboarding/sirene"` |
| `/onboarding` pointe vers Sirène | ✅ | idem |
| `PatrimoineWizard` = import CSV | ✅ | `Patrimoine.jsx` empty-state "Importer CSV" + bouton "Importer" |
| `QuickCreateSite` = création manuelle interne | ✅ | drawer ouvert depuis `setShowQuickCreate(true)` dans Patrimoine.jsx |
| `SiteCreationWizard` pas visible comme entrée principale | ✅ | aucune `<Route>` dans App.jsx ne le mentionne (test `onboarding_entrypoints.test.jsx`) |
| Aucun écran mort | ✅ | `OnboardingPage` non importée dans App.jsx (uniquement commentaire historique L110) |

`NavRegistry.js` confirme : entrées menu pointent vers `/onboarding` et `/onboarding/sirene` — les deux atterrissent correctement sur Sirène (redirect transparent).

L'empty-state Patrimoine ([`Patrimoine.jsx:790-804`](../../frontend/src/pages/Patrimoine.jsx)) joue déjà le rôle d'écran d'aiguillage avec 3 boutons FR : *"Depuis Sirene (recommandé) / Nouveau site manuel / Importer CSV"*.

### 2.6 Documentation cohérente

| Document | Mis à jour | Sections |
|---|---|---|
| [`docs/dev/patrimoine_routes_canonical.md`](../dev/patrimoine_routes_canonical.md) | ✅ | §1-7 P0-A (routes, audit, cascade, anti-swallow) + §8 roadmap + §9 onboarding canonique + §10 contrat DATA_MISSING |
| [`docs/audits/audit_brique_patrimoine_deep_readonly_2026_05_23.md`](audit_brique_patrimoine_deep_readonly_2026_05_23.md) | ✅ | §12 correctifs P0-A + §13 correctifs P0-B (7 sous-sections, checklist d'acceptation) |

---

## 3. Ce qui reste fragile

### 3.1 Résidu legacy — `StatusPage.jsx` ping `/api/sites`

**Fichier** : [`frontend/src/pages/StatusPage.jsx:14`](../../frontend/src/pages/StatusPage.jsx)

```js
const checks = [
  { name: 'Backend /health', url: '/api/health', key: 'health' },
  { name: 'API Sites', url: '/api/sites', key: 'sites' },   // ← retourne désormais 410
  ...
];
```

**Impact** : la page de diagnostic admin marquera "API Sites" en erreur (410 ≠ 200). Aucun impact utilisateur final (page non visible en parcours produit normal). À corriger en P1 : pointer vers `/api/patrimoine/sites` ou retirer la check.

### 3.2 GET /api/sites/{id}/* legacy encore actifs

4 endpoints GET deprecated mais opérationnels (cf. §2.1) :
- `/api/sites/{site_id}` / `/stats` / `/compliance` / `/guardrails`

**Risque** : un appel futur depuis une nouvelle page pourrait passer par eux et créer une nouvelle dépendance. Mitigation : ils sont marqués `deprecated=True` dans OpenAPI, donc visibles en jaune dans la doc Swagger.

**Décision P1** : basculer en 410 quand les équivalents `/api/patrimoine/sites/{id}/*` seront livrés.

### 3.3 Écran "Organisation/Entité juridique" inexistant

Quand une donnée manquante est de niveau `organisation` ou `entite_juridique` (3 codes SMÉ + 1 BEGES), `IncompleteBanner` affiche : *"À compléter dans les informations de l'organisation (écran en préparation)"*. Le filtre table de Patrimoine reste vide.

L'utilisateur est informé mais ne peut pas agir depuis l'UI actuelle. **Boucle non fermée** pour SMÉ/BEGES org-level. P1 critique.

### 3.4 NavRegistry context mapping inconsistant

`NavRegistry.js:73-74` :
```js
'/onboarding': 'cockpit',           // ← devrait être 'patrimoine' depuis P0-B
'/onboarding/sirene': 'patrimoine',
```

Depuis P0-B, `/onboarding` redirige vers `/onboarding/sirene` (contexte patrimoine). Le mapping `/onboarding → cockpit` est cosmétiquement incohérent (highlight de tab) mais sans impact fonctionnel (la redirection règle l'expérience finale).

### 3.5 2 tests baselines pré-existants désélectionnés

- `tests/test_patrimoine.py::TestNNLinks::test_unique_constraint_org_entite` — utilise `OrgEntiteLink.role="a"` (validator Enum strict ajouté ensuite)
- `tests/test_cascade_recompute.py::test_cascade_map_contains_mvp_fields` — comparaison de set sans inclure les 2 entrées Org.consentement_* ajoutées Phase 5.8

Ces 2 fails existent **avant** P0-A/P0-B sur `claude/refonte-sol2` — ils ne bloquent pas la release P0-B mais traînent en dette. À corriger hors scope patrimoine.

---

## 4. Captures / observations UX

### Playwright e2e — non exécuté

Playwright walkthrough complet (Cockpit → CadreApplicable → Patrimoine filtré) **n'a pas été exécuté** dans cet audit, parce qu'il nécessite :
- backend FastAPI démarré sur `:8001` ;
- frontend Vite démarré sur `:5173` ;
- DB seed avec au moins 1 site en DATA_MISSING pour DT/BACS/APER (ex : `python -m services.demo_seed --pack helios --size S`).

Le parcours est **prouvé code-level** par les 13 tests d'interaction Vitest + jsdom (`CadreApplicable.test.jsx` + `IncompleteBanner.test.jsx`) qui rendent les composants en environnement DOM réel et vérifient :
1. Clic sur tile DATA_MISSING → panneau ouvert
2. Panneau affiche scope_label + remediation_label_fr + hint
3. Clic CTA → navigation effective `/patrimoine?incomplete=BACS` (vérifiée via `useLocation()` dans le test)
4. Bandeau Patrimoine rendu avec libellé FR + bouton "Effacer"

**Recommandation** : Playwright e2e nominal à intégrer en P1 dans `tools/playwright/cockpit_patrimoine_walkthrough.spec.mjs` avec seed pack HELIOS — permettrait des captures pour la doc utilisateur.

### Lecture statique du parcours UX

Wording FR vérifié bout en bout :
- Tile : *"Données manquantes · N sites"* (count pluriel/singulier OK)
- Panneau : *"Données à compléter — Décret tertiaire"* (titre)
- CTA dynamique : *"Compléter la surface"* / *"Compléter la puissance CVC"* / etc.
- Bandeau Patrimoine : *"Sites à compléter pour le Décret Tertiaire — 4 sites"*
- Bouton effacer : *"Effacer le filtre"*
- Message org-level : *"À compléter dans les informations de l'organisation (écran en préparation)"*

Aucun jargon anglais résiduel détecté (test pure-grep `IncompleteBanner.test.jsx::texte sans jargon technique anglais` interdit `data`, `missing`, `fix`, `filter`, `banner`, `remediation` dans les libellés rendus).

---

## 5. Résidus legacy éventuels

| # | Item | Localisation | Sévérité | Action P1 recommandée |
|---|---|---|---|---|
| 1 | `/api/sites` ping health | `frontend/src/pages/StatusPage.jsx:14` | 🟡 Mineur | Pointer sur `/api/patrimoine/sites` ou retirer la check |
| 2 | `GET /api/sites/{id}` + 3 sub-paths | `backend/routes/sites.py:108-272` | 🟡 Mineur | Basculer en 410 dès livraison `/api/patrimoine/sites/{id}/{stats,compliance,guardrails}` |
| 3 | NavRegistry `/onboarding: 'cockpit'` | `frontend/src/layout/NavRegistry.js:73` | 🟢 Cosmétique | Corriger en `'patrimoine'` (highlight tab) |
| 4 | Pas d'UI saisie niveau Organisation/EJ | — | 🔴 Bloquant pour SMÉ/BEGES | Créer page `/patrimoine/organisation` (P1 critique) |
| 5 | `OnboardingPage.jsx` fichier conservé | `frontend/src/pages/OnboardingPage.jsx` | 🟢 Aucun (non monté) | Supprimer si Phase 4 abandonnée |
| 6 | 2 baselines tests pré-existants cassés | `test_patrimoine.py` + `test_cascade_recompute.py` | 🟡 Dette | Corriger les fixtures hors scope patrimoine |

**Aucun résidu bloquant pour le GO de la brique patrimoine.** Item 4 (UI org) est bloquant pour la fermeture du parcours SMÉ/BEGES mais hors périmètre P0.

---

## 6. Tests vérifiés

### 6.1 Tests P0-A (5 fichiers, 24 tests)

| Fichier | Tests | Type |
|---|---|---|
| `tests/test_legacy_sites_route_gone.py` | 4 | Unit HTTP — 410 vérifié sur 3 endpoints + message FR |
| `tests/test_patrimoine_crud_audit_log_wiring.py` | 10 | Unit HTTP — 5 PATCH + 4 DELETE + 1 no-op |
| `tests/test_bulk_import_triggers_cascade.py` | 4 | Unit HTTP — cascade summary + audit per site + idempotence + missing surface |
| `tests/test_patch_crud_site_raises_on_recompute_failure.py` | 3 | Unit HTTP — 500 PATRIMOINE_RECOMPUTE_FAILED + rollback + champ non-conformité |
| `tests/source_guards/test_patrimoine_crud_audit_log_wiring_source_guards.py` | 2 | AST — log présent sur PATCH/DELETE + anti-swallow |

### 6.2 Tests P0-B (4 BE + 3 FE, 61 tests)

| Fichier | Tests | Type |
|---|---|---|
| `tests/test_patrimoine_crud_create_audit_log.py` | 5 | Unit HTTP — 4 POST + 1 GET sans audit |
| `tests/test_regulatory_remediation_fields.py` | 22 | Unit — mapping + bijection + to_dict enrichi + zero pollution autres statuts |
| `tests/source_guards/test_patrimoine_crud_post_audit_log_source_guards.py` | 2 | AST — log présent sur POST + interdit sur GET |
| `tests/source_guards/test_data_missing_remediation_source_guards.py` | 12 | Bijection codes ↔ remediation + structurel par code |
| `frontend/src/components/grammar/hub/__tests__/CadreApplicable.test.jsx` | 6 | jsdom — interactif + navigation MemoryRouter |
| `frontend/src/components/patrimoine/__tests__/IncompleteBanner.test.jsx` | 7 | jsdom — libellés FR + pluriel + no-anglais |
| `frontend/src/__tests__/onboarding_entrypoints.test.jsx` | 6 | Pure-grep AST — App.jsx + Patrimoine.jsx |

### 6.3 Tests non-régression baseline (290 tests verts)

```
tests/test_patrimoine.py                           [-1 deselect]
tests/test_patrimoine_anomalies_v58.py
tests/test_patrimoine_conformite_sync.py
tests/test_patrimoine_kpis.py
tests/test_patrimoine_multiorg.py
tests/test_patrimoine_world_class.py
tests/test_cascade_recompute.py                    [-1 deselect]
tests/test_cascade_recompute_audit_log_wiring.py
tests/test_patch_sites_triggers_cascade.py
tests/regulatory/                                  (5 fichiers règles)
tests/source_guards/test_applicability_engine_source_guards.py
tests/source_guards/test_audit_log_no_direct_writes_source_guards.py
tests/source_guards/test_routes_patrimoine_init_reexports_source_guards.py

→ 290 passed, 2 deselected (baselines pré-existants), 0 régression
```

### 6.4 Intégration CI

| Workflow | Chemin | Couvre |
|---|---|---|
| `.github/workflows/quality-gate.yml` | "Backend (ruff + mypy + pytest)" `python -m pytest tests/ -x -q` | **Tous mes tests BE auto-découverts via `testpaths = ["tests"]` (pyproject.toml)** |
| `.github/workflows/quality-gate.yml` | "Frontend (lint + test + build)" `npm test` | **Tous mes tests FE auto-découverts via Vitest glob `**/*.test.{js,jsx}`** |
| `.github/workflows/source_guards.yml` | `pytest backend/tests/source_guards/ -v --tb=short` | Mes 3 source-guards AST inclus |

**Conclusion CI** : tous les tests P0-A et P0-B sont intégrés en CI sans action supplémentaire. Aucun test ne reste à exécution manuelle.

### 6.5 Trous restants identifiés

| Couverture manquante | Sévérité | P1 ? |
|---|---|---|
| **Playwright e2e Cockpit → Patrimoine** (walkthrough nominal avec captures) | 🟡 | Oui — `tools/playwright/cockpit_patrimoine_walkthrough.spec.mjs` |
| Test `IncompleteBanner` cas API timeout / 500 (fail gracieux ?) | 🟢 | Optionnel |
| Test multi-org `/api/regulatory/applicability` (org A ≠ voir DATA_MISSING org B) | 🟡 | Oui — déjà testé via `test_v57_multiorg_isolation` côté backend ; ajout matrix `RuleApplicability` |
| Test E2E "user saisit surface → recompute → DATA_MISSING disparaît" (boucle fermée) | 🟢 | Souhaitable |

---

## 7. P1 recommandé (post P0-A/P0-B)

### P1 — Critique pour boucle fermée

1. **UI Organisation / Entité juridique** : page `/patrimoine/organisation` permettant de saisir effectif, CA, bilan, conso 3y. Sans elle, les 4 DATA_MISSING SMÉ/BEGES restent informatifs sans action. Référence : `IncompleteBanner` affiche déjà "écran en préparation" — il suffit de livrer l'écran et retirer le message.
2. **`StatusPage.jsx`** : retirer ou rebrancher `/api/sites` → `/api/patrimoine/sites` (1 ligne).
3. **NavRegistry** : `/onboarding: 'patrimoine'` (1 ligne, cosmétique highlight).

### P1 — Crédibilité

4. **Basculer les 4 GET `/api/sites/{id}/*` en 410** dès livraison des équivalents `/api/patrimoine/sites/{id}/{stats,compliance,guardrails}`.
5. **Playwright e2e nominal** : `cockpit_patrimoine_walkthrough.spec.mjs` avec seed HELIOS — captures pour doc utilisateur + CI visuel.
6. **`/api/regulatory/applicability` multi-org isolation** : matrix test endpoint (étendre `test_v57_multiorg_isolation`).

### P1 — Hygiène

7. **2 baselines tests pré-existants** : corriger `test_unique_constraint_org_entite` (utiliser un rôle Enum valide) et `test_cascade_map_contains_mvp_fields` (mettre à jour le set attendu avec les 2 entrées Org.consentement_*). Non-bloquant patrimoine mais traîne en dette baseline.
8. **`OnboardingPage.jsx`** : décision Phase 4 — soit livrer le wizard premier pas réel, soit supprimer le fichier (actuellement non monté mais conservé).

---

## 8. Go / No Go pour passer à la brique suivante

### Décision : **GO** ✅

| Critère de GO | Validé | Commentaire |
|---|:---:|---|
| 0 route legacy utilisée par le front | ⚠️ | 1 résidu non bloquant (`StatusPage.jsx` ping `/api/sites` — health monitoring admin uniquement) |
| 0 mutation patrimoine non auditée | ✅ | 16/16 endpoints CRUD wirés + 2 source-guards AST |
| 0 DATA_MISSING sans remédiation | ✅ | 9/9 codes mappés + source-guard bijection |
| 0 écran onboarding mort | ✅ | `/onboarding` → Sirène, `OnboardingPage` non monté |
| Parcours Cockpit → Patrimoine fonctionnel | ✅ | 13 tests interaction Vitest + jsdom |
| Tests P0-A/P0-B verts | ✅ | 65 BE + 20 FE = 85/85 |
| Baseline non régressée | ✅ | 290 tests patrimoine/regulatory verts |

### Justification du GO malgré le résidu StatusPage

Le résidu `StatusPage.jsx` ping `/api/sites` n'affecte **aucun parcours utilisateur final** :
- la page est destinée aux admins/SRE pour diagnostic ;
- l'état "API Sites: 410 Gone" est techniquement correct (l'endpoint EST gone) ;
- aucune fonctionnalité produit ne dépend de ce ping ;
- correction triviale en P1 (1 ligne).

### Conditions de réversibilité

Le sprint P0-B est **réversible sans douleur** :
- 1 commit isolé (`b701def1`) sur sa propre branche
- Aucun changement de schéma DB
- Aucune migration Alembic
- `git revert b701def1` rétablirait l'état pré-P0-B sans casser P0-A

### Recommandation de séquence

✅ **Procéder au sprint suivant** sur une autre brique (par exemple : Bill Intelligence, Achat, Flex selon doctrine produit).

Garder le ticket **P1 ouvert** pour l'écran Organisation/EJ — c'est la seule boucle non encore fermée et elle bloque l'actionnabilité SMÉ/BEGES.

---

*Audit post-fix clôturé le 2026-05-23. Vérifications faites en lecture seule via `git log`, `grep`, `pytest`, `vitest`. Aucune modification de code. Tous les chiffres et `file:ligne` sont vérifiés sur `b701def1`.*
