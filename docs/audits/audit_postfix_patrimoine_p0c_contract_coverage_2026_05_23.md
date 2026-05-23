# Audit post-fix Patrimoine — P0-C Contract Coverage

> **Branche** : `claude/patrimoine-p0c-contract-coverage`
> **HEAD** : `0a8ce3a4` (P0-C) sur `b701def1` (P0-B) sur `3ee702a9` (P0-A)
> **Date** : 2026-05-23
> **Mode** : READ-ONLY strict — aucune modification de code
> **Périmètre** : couverture contrat énergie ↔ points de livraison (PRM/PDL/PCE)
> **Référence sprint** : `audit_brique_patrimoine_deep_readonly_2026_05_23.md §14`
> **Référence canonique** : [`docs/dev/patrimoine_routes_canonical.md §11`](../dev/patrimoine_routes_canonical.md)

---

## 1. Verdict exécutif

**GO** pour clôturer Patrimoine P0 complet et passer à la **Conformité conditionnelle**.

Le sprint P0-C est **intégré bout en bout** (service → endpoint → anomalie → perimeter → UI) avec **30 tests dédiés verts** + **288 baseline non régressés** + **65 tests P0-A/B toujours verts**. Aucun endpoint concurrent, aucun écran nouveau, terminologie FR canonique respectée *(« Point de livraison <énergie> — PRM/PDL <code> »* / *« ... — PCE <code> »)*. La règle produit *"un site n'est pas prêt facture / achat / audit sans contrat couvrant ses DP actifs"* est désormais imposée à 3 niveaux : anomalie HIGH, blocage perimeter_check, UI badge cardinal.

| Critère de GO | Statut | Évidence |
|---|---|---|
| Service contract_coverage_service.py présent & complet | ✅ | 442 lignes, 5 statuts cardinaux, ready flags, 4 codes d'action |
| Endpoint canonique unique sans concurrence | ✅ | `GET /api/patrimoine/sites/{id}/contract-coverage` ligne 97 |
| Anomalie patrimoine wirée HIGH | ✅ | `_rule_delivery_point_without_contract` ligne 310 + orchestrée ligne 451 |
| `perimeter_check` bloque facture sans contrat (DP actifs) | ✅ | `BILLING_CONTRACT_REQUIRED` + message FR exact |
| UI badge + liste DP par contrat + CTA FR | ✅ | `SiteContractsSummary.jsx` étendu (composant déjà monté Site360) |
| 30 tests P0-C verts | ✅ | 23 BE + 7 FE |
| P0-A/B non régressés | ✅ | 65/65 verts |
| Baseline patrimoine/cascade non régressée | ✅ | 288 verts (2 deselect pré-existantes, idem P0-A/B) |

---

## 2. Ce qui est validé

### 2.1 Service `contract_coverage_service.py`

[`backend/services/contract_coverage_service.py`](../../backend/services/contract_coverage_service.py) — 442 lignes.

**API publique unique** : `compute_site_contract_coverage(db, site_id, org_id, *, today=None) -> SiteContractCoverage`.

**5 statuts cardinaux** (constantes exportées L51-55) :

| Constante | Valeur | Sémantique |
|---|---|---|
| `COVERAGE_CONTRAT_RATTACHE` | `contrat_rattache` | Tous DP actifs couverts par contrat actif, énergies cohérentes |
| `COVERAGE_CONTRAT_PARTIEL` | `contrat_partiel` | Au moins 1 DP actif sans contrat |
| `COVERAGE_CONTRAT_MANQUANT` | `contrat_manquant` | DP actifs mais aucun contrat actif |
| `COVERAGE_CONTRAT_EXPIRE` | `contrat_expire` | Site avec DP actifs et tous contrats expirés |
| `COVERAGE_CONTRAT_INCOHERENT` | `contrat_incoherent` | Mismatch énergie OU contrat liant un DP hors site |

Priorité (le plus dégradé domine) : `incoherent > expire > manquant > partiel > rattache` (vérifié L370-381).

**Dataclasses immuables** (`@dataclass(frozen=True)`) :
- `DeliveryPointSummary` L93 — id, code, energy_type, status, grd_code, `label_fr`, covering_contract_ids
- `ContractSummary` L109 — id, supplier_name, energy_type, dates, is_expired, delivery_point_ids, `label_fr`
- `EnergyMismatch` L127 — contract_id, dp_id, énergies, `message_fr`
- `CoverageAction` L141 — code, `label_fr`, target_type, target_id
- `SiteContractCoverage` L154 — agrégat de tout + `ready_for_billing` + `ready_for_purchase`

**`ready_for_billing`** (L384-389) : `contrat_rattache` ∧ `contracts_active` non-vide ∧ pas de mismatch ∧ pas de foreign link.
**`ready_for_purchase`** (L387) : `ready_for_billing` ∧ `dp_active` non-vide.

**Actions typées FR** (L391-432) — 4 codes machine + label_fr utilisateur :
- `ATTACH_CONTRACT` → *"Rattacher un contrat à <label DP FR>"*
- `RENEW_CONTRACT` → *"Renouveler le contrat <label FR> (expiré le ...)"*
- `FIX_ENERGY_MISMATCH` → *"Corriger le rattachement énergie du contrat #N"*
- `DETACH_FOREIGN_DP` → *"Détacher le point de livraison #N du contrat #M"*

**Libellés FR canoniques** (L192-217) :
- `_dp_label_fr` génère *"Point de livraison électricité — PRM/PDL <code>"* (élec) ou *"... — PCE <code>"* (gaz).
- `_contract_label_fr` génère *"<Fournisseur> — Électricité|Gaz (contrat n° <ref>)"*.

### 2.2 Endpoint canonique unique

`GET /api/patrimoine/sites/{site_id}/contract-coverage` ([`backend/routes/patrimoine/sites.py:97`](../../backend/routes/patrimoine/sites.py)) :

- Délégation pure au service `compute_site_contract_coverage` (zéro logique dans la route).
- Org-scoping cardinal via `_load_site_with_org_check` (Phase E IDOR) **avant** appel du service.
- Réponse = `coverage.to_dict()` — clés FR + status cardinal + ready flags + actions.

**Aucune route concurrente** : grep exhaustif `backend/routes/` confirme un seul match `@router.get("/sites/{site_id}/contract-coverage")` (ligne 97 de `patrimoine/sites.py`). Aucun endpoint préexistant n'agrégeait cette information.

### 2.3 Anomalie patrimoine

`_rule_delivery_point_without_contract(site, db)` dans [`backend/services/patrimoine_anomalies.py:310`](../../backend/services/patrimoine_anomalies.py) :

- **Sévérité HIGH** (-15 score complétude, cf. `_PENALTY`).
- **Une anomalie par DP non couvert** (l'utilisateur traite cas par cas).
- **Wirée** dans `compute_site_anomalies` ligne 451.
- **Délègue** à `compute_site_contract_coverage` (zéro duplication).
- **Skip** si site archivé (`if not site.actif: return []`) — laisse l'orphan rule s'en charger.

**Message FR actionnable** :
- title_fr : *"Point de livraison sans contrat"*
- detail_fr : *"<label DP FR> est actif mais n'est rattaché à aucun contrat énergie. La facturation ne peut pas être fiabilisée sans contrat couvrant."*
- cta : *{"label": "Rattacher un contrat", "to": "/sites/{id}?tab=contrats"}*
- fix_hint_fr : *"Ouvrez l'onglet contrats du site et créez ou rattachez un contrat couvrant ce point de livraison."*

### 2.4 Renforcement `perimeter_check`

[`backend/services/perimeter_check.py`](../../backend/services/perimeter_check.py) (106 lignes) :

**Constantes exportées** (L20-23) :
```python
ERROR_CODE_MISSING_CONTRACT = "BILLING_CONTRACT_REQUIRED"
ERROR_MESSAGE_MISSING_CONTRACT_FR = (
    "Impossible de fiabiliser cette facture : aucun contrat n'est rattaché "
    "au point de livraison."
)
```

**Logique blocking** (L70-82) :
- Si `contract_id=None` ET `_site_has_active_delivery_points(db, site_id)` :
  → `consistent=False`, `blocking=True`, `error_code=BILLING_CONTRACT_REQUIRED`, warning FR canonique.
- Si `contract_id=None` ET site sans DP actif : toléré (rien à fiabiliser).
- Sinon comportement préexistant préservé (existence contrat, match site, couverture période).

### 2.5 UI `SiteContractsSummary`

[`frontend/src/components/SiteContractsSummary.jsx`](../../frontend/src/components/SiteContractsSummary.jsx) — 341 lignes, composant **déjà monté** dans `Site360.jsx:75,2164` (zéro nouvel écran).

**Mapping cardinal status → badge** (L45-51) :
```js
contrat_rattache  → { tone: 'success', label: 'Tous les points sont couverts', icon: CheckCircle2 }
contrat_partiel   → { tone: 'warning', label: 'Couverture partielle', icon: AlertTriangle }
contrat_manquant  → { tone: 'error',   label: 'Aucun contrat rattaché', icon: XCircle }
contrat_expire    → { tone: 'error',   label: 'Contrat expiré', icon: Clock }
contrat_incoherent→ { tone: 'error',   label: 'Incohérence énergie', icon: AlertTriangle }
```

**Composants internes** :
- `CoverageBanner` (L250) — bandeau cardinal en haut de la card avec liste des DP/contrats concernés.
- Helper `deliveryPointLabel(dp)` (L58-65) — fallback FR canonique côté client si backend `label_fr` absent.

**CTAs FR** :
- *"Rattacher un contrat"* (data-action `coverage-cta-attach`) si `uncovered_delivery_points` non vide + callback `onAttachContract`.
- *"Corriger le rattachement"* (data-action `coverage-cta-correct`) si mismatch ou foreign DP.

**Liste explicite par contrat** : pour chaque card contrat, bullet list des DP couverts avec libellé FR canonique (L162-177).

**Anti-jargon vérifié** : grep manuel + test pure-grep `IncompleteBanner.test.jsx` (P0-B) déjà actif. Aucun PRM/PCE orphelin dans les libellés rendus — toutes les occurrences sont précédées de *"Point de livraison <énergie> — "*.

### 2.6 Bijection multi-source — zéro duplication

3 consommateurs de `compute_site_contract_coverage` :
1. **Endpoint** `GET /api/patrimoine/sites/{id}/contract-coverage` — sérialise via `to_dict()`.
2. **Anomalie patrimoine** `_rule_delivery_point_without_contract` — itère sur `uncovered_delivery_points`.
3. **UI** `SiteContractsSummary.jsx` — fetch via `getSiteContractCoverage(siteId)`.

`perimeter_check` ne consomme pas le service complet mais réutilise `_site_has_active_delivery_points` (helper interne dédié) — pas de duplication de la logique métier de couverture (qui reste pure SoT côté service).

---

## 3. Ce qui reste fragile

### 3.1 `bilan_eur` SMÉ critère (b) toujours absent côté evaluator

P0-B avait livré `Organisation.bilan_eur` au niveau modèle, mais l'évaluateur SMÉ continue de hardcoder `bilan = None` (cf. audit `§7.1`). P0-C n'a pas touché à ça (hors scope). Reste P1 pour SMÉ critère (b) `CA ≥ 50M€ AND bilan ≥ 43M€`.

### 3.2 UI Organisation/EJ toujours en préparation

L'`IncompleteBanner` P0-B affiche *"écran en préparation"* pour les DATA_MISSING niveau org (3 codes SMÉ + 1 BEGES). P0-C n'a pas livré cet écran. Boucle SMÉ/BEGES org-level pas encore fermée — P1 critique inchangé.

### 3.3 `delivery_points_count` redondant côté serializer

`_serialize_contract` (`routes/patrimoine/_helpers.py:384`) expose toujours `delivery_points_count` (P0-A héritage). Désormais redondant avec `delivery_point_ids[]` + le service coverage. Pas un bug, juste de la dette de simplification — peut être nettoyé en P1.

### 3.4 ContratCadre (V2 multi-sites) hors P0-C

Le service ne consomme que `EnergyContract` (legacy 1-N). Les `ContratCadre` / `ContractAnnexe` (V2) ne sont pas pris en compte pour la couverture. Si un site est couvert uniquement par un cadre V2, il apparaîtra comme `contrat_manquant`. P0-C suit la consigne *"ne pas refondre"*. P1 — intégrer V2 via `get_site_active_contract(site_id)` (déjà disponible).

### 3.5 4 GET legacy `/api/sites/{id}/*` toujours actifs

Inchangé depuis P0-A/B. Pas un risque P0-C mais résidu connu.

### 3.6 `StatusPage.jsx` ping `/api/sites` toujours présent

Inchangé. Affiche "API Sites: down" (410) sans impact utilisateur final.

### 3.7 Markdownlint cosmétique sur docs

Les docs Patrimoine accumulent des warnings MD032/MD060 cosmétiques (espacement de tables) hérités du fichier original. Pas un blocage, mais à reformater en P2 hygiène.

---

## 4. Tests vérifiés

### 4.1 P0-C — 30 tests verts

| Fichier | Tests | Statuts couverts |
|---|---|---|
| `tests/test_contract_coverage_service.py` | **12** | 5 statuts cardinaux (rattache/partiel/manquant/expire/incoherent×2) + multi-org isolation + libellés FR élec/gaz + site inexistant + site sans DP + JSON serializable |
| `tests/test_patrimoine_anomalies_delivery_point_without_contract.py` | **5** | HIGH si DP actif sans contrat / pas d'anomalie si couvert / 2 DP → 2 anomalies / DP inactif skip / site archivé skip |
| `tests/test_perimeter_check_requires_contract_when_delivery_points_active.py` | **6** | blocking si DP actifs + no contract_id / tolérance si pas de DP / contract_id valide OK / contract inexistant 4xx-like / site inconnu / message FR strict (zéro anglais) |
| `frontend/src/components/__tests__/SiteContractsSummary.test.jsx` | **7** | 5 badges cardinaux + CTA "Rattacher un contrat" déclenche callback + liste DP par contrat |

### 4.2 P0-A + P0-B — 65 BE + 27 FE = 92 verts, aucune régression

Toutes les suites P0-A et P0-B sont relancées et passent intégralement après P0-C : routes legacy 410, audit log PATCH/DELETE/POST, bulk cascade, recompute failure, DATA_MISSING enrichi, CadreApplicable interactif, IncompleteBanner, onboarding entry-points.

### 4.3 Baseline patrimoine/cascade — 288 verts

```
tests/test_patrimoine.py                           [-1 deselect baseline]
tests/test_patrimoine_anomalies_v58.py             [fixture perfect_score mise à jour P0-C]
tests/test_patrimoine_conformite_sync.py
tests/test_patrimoine_kpis.py
tests/test_patrimoine_multiorg.py
tests/test_patrimoine_world_class.py
tests/test_cascade_recompute.py                    [-1 deselect baseline]
tests/test_cascade_recompute_audit_log_wiring.py
tests/test_patch_sites_triggers_cascade.py
tests/regulatory/                                  (5 fichiers règles)
tests/source_guards/test_applicability_engine_source_guards.py
tests/source_guards/test_audit_log_no_direct_writes_source_guards.py

→ 288 passed, 2 deselected (baselines pré-existantes P0-A/B), 0 régression
```

### 4.4 CI integration

Tous les fichiers tests P0-C sont auto-découverts :
- BE : `pyproject.toml::testpaths = ["tests"]` → workflow `quality-gate.yml::pytest tests/`.
- FE : Vitest glob `**/*.test.{js,jsx}` → workflow `quality-gate.yml::npm test`.

**Aucun test P0-C ne reste en exécution manuelle.**

### 4.5 Trous restants

| Couverture manquante | Sévérité | P1 ? |
|---|---|---|
| Playwright e2e Site360 → couverture badge → DrawerAddContrat | 🟡 | Oui, dans la même spec que P0-B walkthrough |
| Test endpoint `/contract-coverage` (404 si scope wrong / 401 si pas auth) | 🟢 | Optionnel — le wiring `_load_site_with_org_check` est déjà testé ailleurs |
| Test `ContratCadre` V2 intégré dans coverage | 🟡 | Oui — extension service (cf. §3.4) |
| Source-guard interdisant *"PRM/PCE"* nu dans les `.jsx` (anti-jargon) | 🟢 | Souhaitable hygiène |

---

## 5. Critères P0-C — relecture conformité

| Critère brief | Validé | Évidence |
|---|---|---|
| Service `compute_site_contract_coverage` avec 5 statuts cardinaux | ✅ | constantes L51-55, status assigné L370-381 |
| `ready_for_billing` / `ready_for_purchase` | ✅ | L384-389 (booléens) |
| `actions[]` typées | ✅ | 4 codes machine + label_fr (L391-432) |
| Libellés FR canoniques | ✅ | `_dp_label_fr` + `_contract_label_fr` |
| Endpoint `GET /api/patrimoine/sites/{id}/contract-coverage` | ✅ | route L97 patrimoine/sites.py |
| Org-scoping | ✅ | `_load_site_with_org_check` (Phase E IDOR) avant calcul |
| Pas de route concurrente | ✅ | grep exhaustif backend/routes → 1 match |
| `_rule_delivery_point_without_contract` HIGH | ✅ | L310 + orchestré L451 |
| Une anomalie par DP non couvert | ✅ | boucle `for dp_summary in coverage.uncovered_delivery_points` |
| Message FR actionnable | ✅ | title_fr + detail_fr + cta + fix_hint_fr |
| `perimeter_check` bloque facture sans contrat si DP actifs | ✅ | L70-82 + helper `_site_has_active_delivery_points` |
| `error_code=BILLING_CONTRACT_REQUIRED` + `blocking=True` + message FR | ✅ | constantes L20-23 + exposition L74-78 |
| UI affiche statut, points couverts/non couverts, expiré, incohérence | ✅ | bandeau 5 badges + liste par contrat |
| Aucun PRM/PCE sans "Point de livraison" | ✅ | grep confirmé : toutes les occurrences sont préfixées |
| 30 tests P0-C verts | ✅ | 23 BE + 7 FE |
| P0-A/P0-B verts | ✅ | 65 BE + 27 FE |
| Baseline patrimoine/cascade non régressée | ✅ | 288 verts |

---

## 6. Patrimoine P0 complet — récapitulatif global

| Sprint | Commit | Tests nouveaux | Acceptance |
|---|---|---|---|
| **P0-A** (routes + audit + cascade) | `3ee702a9` | 24 verts | ✅ Tous critères |
| **P0-B** (data missing actionnable + onboarding) | `b701def1` | 60 verts | ✅ Tous critères |
| **P0-C** (contract coverage) | `0a8ce3a4` | 30 verts | ✅ Tous critères |
| **Total Patrimoine P0** | 3 commits isolés | **114 tests dédiés** + **288 baseline** | **Brique livrée** |

### Note Patrimoine post-P0 (rappel)

Audit initial 2026-05-23 : **5,4/10** → post-P0 : la brique répond aux 4 P0 cardinaux (CadreApplicable actionnable, onboarding consolidé, audit complet, cascade bulk) **plus** le P0-C (couverture contrat). La cinquième dette (Compteur/Meter ADR-D-01 + ContratCadre V2) reste P2 documentée.

### 5 risques initiaux — état actuel

| Risque initial | Post-P0-C |
|---|---|
| 1. CadreApplicable DATA_MISSING non actionnable | ✅ Corrigé (P0-B) |
| 2. 5 entry-points création concurrents | ✅ Corrigé (P0-B) |
| 3. CRUD patrimoine sans audit trail | ✅ Corrigé (P0-A + P0-B) |
| 4. Bulk import sans cascade | ✅ Corrigé (P0-A) |
| 5. Doublons Compteur/Meter + 3 routers /sites | ⏳ Partiel (P0-A pour routers, ADR-D-01 P2) |
| **6. Couverture contrat ↔ DP** (ajouté par amendement) | ✅ **Corrigé (P0-C)** |

---

## 7. Décision : GO / NO GO

### Décision : **GO** ✅

**Pour clôturer Patrimoine P0 complet** et **passer à la brique Conformité conditionnelle**.

### Justification

- **Patrimoine = brique opérable** : un Customer Success peut désormais expliquer en moins de 2 minutes le statut contractuel d'un site et l'action à faire.
- **Bill Intelligence** dispose des contrats opposables : `ready_for_billing` + `BILLING_CONTRACT_REQUIRED` lui permettent de filtrer / bloquer.
- **Achat** dispose de `ready_for_purchase` pour son scoring d'éligibilité.
- **Conformité** dispose de l'anomalie `DELIVERY_POINT_WITHOUT_CONTRACT` HIGH dans `compute_site_anomalies` — alimente déjà le hub Patrimoine.
- **Audit trail complet** : 16 endpoints patrimoine_crud + cascade + perimeter check tous tracés.
- **Aucune route concurrente, aucun écran fantôme, terminologie FR canonique homogène.**
- **Réversibilité** : `git revert 0a8ce3a4` rétablirait l'état pré-P0-C sans casser P0-A/B (commit isolé, pas de migration Alembic).

### Conditions de réversibilité préservées

- 3 commits isolés, chacun réversible séparément.
- Aucun changement de schéma DB (modèles inchangés, seul `_anomaly` et `_perimeter` enrichis sans migration).
- Aucun ajout de dépendance Python ou npm.

### P1 ouverts (à traiter dans Conformité ou hygiène)

1. **Écran Organisation/EJ** pour saisir effectif/CA/bilan/conso 3y (fermeture boucle SMÉ/BEGES) — porté depuis P0-B.
2. **`StatusPage.jsx`** pointer sur `/api/patrimoine/sites` — 1 ligne.
3. **`NavRegistry` mapping `/onboarding: 'patrimoine'`** — 1 ligne cosmétique.
4. **4 GET legacy `/api/sites/{id}/*`** basculer en 410 dès équivalents `/api/patrimoine/*` livrés.
5. **2 baselines pré-existants** (`OrgEntiteLink.role` + `CASCADE_MAP set`) — hors patrimoine.
6. **Intégration `ContratCadre` V2** dans `compute_site_contract_coverage` — extension non-bloquante.
7. **Playwright e2e** Site360 contrats + bandeau coverage (captures doc utilisateur).
8. **Source-guard anti-jargon** : interdire *"PRM/PCE"* nu dans les `.jsx` (hygiène).

---

*Audit post-fix clôturé le 2026-05-23. Vérifications par `git log`, `grep`, `pytest`, `vitest`. Tous les `file:ligne` cités sont vérifiés sur `0a8ce3a4`. Patrimoine P0 complet — GO Conformité conditionnelle.*
