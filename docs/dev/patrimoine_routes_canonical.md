# Routes Patrimoine — Référence canonique

> **Auteur** : Sprint P0-A `claude/patrimoine-p0a-clean-routes-audit-cascade` (2026-05-23)
> **Statut** : source de vérité pour toutes les routes patrimoine. Toute nouvelle route patrimoine doit être ajoutée ici **avant** d'être implémentée.
> **Référence audit amont** : `docs/audits/audit_brique_patrimoine_deep_readonly_2026_05_23.md`.

Ce document encode 4 règles non-négociables pour toute mutation patrimoine :
1. **Route canonique unique** (pas de doublon, pas de route mortes).
2. **Audit log obligatoire** sur toute mutation (PATCH/DELETE/POST création).
3. **Cascade conformité obligatoire** sur mutation de champ amont (surface, parking, code_postal, etc.) — soit recompute immédiat soit statut `pending_recompute` explicite.
4. **Aucune erreur silencieuse** : un échec de recompute → HTTP 500 + rollback (jamais de try/except qui avale).

---

## 1. Cartographie canonique

### 1.1 Création / quick-create

| Verbe | Route canonique | Module | Audit | Cascade |
|---|---|---|---|---|
| `POST` | `/api/patrimoine/crud/sites/quick-create` | `routes/patrimoine_crud.py:quick_create_site_crud` | ✅ `site.create` | ✅ `batch_cascade_recompute_sites([id])` |
| `POST` | `/api/patrimoine/crud/sites` | `routes/patrimoine_crud.py:create_site_crud` | ✅ `site.create` | — (création explicite avec `portefeuille_id` requis) |
| `POST` | `/api/patrimoine/crud/organisations` | `routes/patrimoine_crud.py:create_organisation` | ⚠️ TODO Sprint P0-B | — |
| `POST` | `/api/patrimoine/crud/entites` | `routes/patrimoine_crud.py:create_entite` | ⚠️ TODO Sprint P0-B | — |
| `POST` | `/api/patrimoine/crud/portefeuilles` | `routes/patrimoine_crud.py:create_portefeuille` | ⚠️ TODO Sprint P0-B | — |
| `POST` | `/api/patrimoine/crud/batiments` | `routes/patrimoine_crud.py:create_batiment` | ⚠️ TODO Sprint P0-B | ✅ `recompute_site_bacs_aggregate` |
| `POST` | `/api/import/sites` (CSV bulk) | `routes/import_sites.py:import_sites_csv` | ✅ via `batch_cascade_recompute_sites` (audit `site.cascade_recompute` ou `site.cascade_pending`) | ✅ idempotent |

### 1.2 Édition / archivage

| Verbe | Route canonique | Module | Audit | Cascade |
|---|---|---|---|---|
| `PATCH` | `/api/patrimoine/crud/organisations/{id}` | `update_organisation` | ✅ `organisation.update` | ✅ consent fields → cascade_recompute_on_change |
| `PATCH` | `/api/patrimoine/crud/entites/{id}` | `update_entite` | ✅ `entite_juridique.update` | — |
| `PATCH` | `/api/patrimoine/crud/portefeuilles/{id}` | `update_portefeuille` | ✅ `portefeuille.update` | — |
| `PATCH` | `/api/patrimoine/crud/sites/{id}` | `update_site_crud` | ✅ `site.update` | ✅ recompute compliance ; **échec → 500 PATRIMOINE_RECOMPUTE_FAILED + rollback** |
| `PATCH` | `/api/patrimoine/crud/batiments/{id}` | `update_batiment` | ✅ `batiment.update` | ✅ cascade BACS si `cvc_power_kw` |
| `PATCH` | `/api/patrimoine/sites/{id}` (premium) | `routes/patrimoine/sites.py:update_site` | ✅ `site.update` + `log_cascade` | ✅ `cascade_recompute_on_change` sur fields CASCADE_MAP |
| `DELETE` | `/api/patrimoine/crud/organisations/{id}` | `archive_organisation` | ✅ `organisation.archive` | — |
| `DELETE` | `/api/patrimoine/crud/entites/{id}` | `archive_entite` | ✅ `entite_juridique.archive` | — |
| `DELETE` | `/api/patrimoine/crud/portefeuilles/{id}` | `archive_portefeuille` | ✅ `portefeuille.archive` | — |
| `DELETE` | `/api/patrimoine/crud/sites/{id}` | `archive_site_crud` | ✅ `site.archive` | ✅ `cascade_site_archive` |
| `DELETE` | `/api/patrimoine/crud/batiments/{id}` | `delete_batiment` | ✅ `batiment.delete` | ✅ `recompute_site_bacs_aggregate` |

### 1.3 Lecture (sans audit log nécessaire)

| Verbe | Route canonique | Module |
|---|---|---|
| `GET` | `/api/patrimoine/sites` (premium, paginé) | `routes/patrimoine/sites.py:list_sites` |
| `GET` | `/api/patrimoine/sites/{id}` | `routes/patrimoine/sites.py:get_site` |
| `GET` | `/api/patrimoine/crud/sites` (CRUD léger) | `routes/patrimoine_crud.py:list_sites_crud` |
| `GET` | `/api/patrimoine/sites/{id}/snapshot` / `/anomalies` / `/completeness` | `routes/patrimoine/sites.py` |
| `GET` | `/api/patrimoine/kpis`, `/api/patrimoine/portfolio-summary`, etc. | `routes/patrimoine/*` |

---

## 2. Routes legacy GONE (HTTP 410)

P0-A 2026-05-23 — relocalisation propre (sans concurrence) :

| Verbe | Route legacy | HTTP | Remplacement canonique |
|---|---|---|---|
| `POST` | `/api/sites/quick-create` | **410** | `POST /api/patrimoine/crud/sites/quick-create` |
| `POST` | `/api/sites` | **410** | `POST /api/patrimoine/crud/sites` |
| `GET` | `/api/sites` | **410** | `GET /api/patrimoine/sites` |

**Format de la réponse 410** :

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

### Fichier mort supprimé

- `backend/routes/patrimoine.py` (0 octets — collision potentielle avec le package `routes/patrimoine/`). Le package canonique reste `routes/patrimoine/__init__.py`.

### Routes encore deprecated mais opérationnelles (P0-B futur)

Routes `GET /api/sites/{site_id}/stats`, `/guardrails`, `/compliance` : non utilisées par le frontend, pas de remplacement direct. Migration différée — basculement en 410 dès que les équivalents `/api/patrimoine/sites/{id}/...` sont livrés.

---

## 3. Règle audit log — pattern obligatoire

Tout endpoint PATCH/DELETE/POST mutant patrimoine doit appeler `services.audit_log_service.log_patrimoine_change` :

```python
from services.audit_log_service import log_patrimoine_change

@router.patch("/.../{id}")
def update_x(...):
    ...
    headers = _audit_headers(request, auth)
    before = _capture_before(entity, list(payload.keys()))
    for field, value in payload.items():
        setattr(entity, field, value)
    db.flush()
    diff = _diff_after(entity, before)
    if diff:
        log_patrimoine_change(
            db,
            user_id=headers["user_id"],
            org_id=org_id,
            entity_type="<entity_type>",
            entity_id=id,
            action="<entity_type>.update",
            field_modified=",".join(diff.keys()) if len(diff) > 1 else next(iter(diff)),
            old_value={k: v["before"] for k, v in diff.items()},
            new_value={k: v["after"] for k, v in diff.items()},
            correlation_id=headers["correlation_id"],
            ip_address=headers["ip_address"],
            user_agent=headers["user_agent"],
            detail=diff,
        )
    db.commit()
```

**Action canoniques** :
- `<entity>.create` / `<entity>.update` / `<entity>.archive` / `<entity>.delete`
- `site.cascade_recompute` (cascade idempotente)
- `site.cascade_pending` (données amont manquantes, signal stale)

**Source-guard AST** : `tests/source_guards/test_patrimoine_crud_audit_log_wiring_source_guards.py` — verrouille la présence de l'appel `log_patrimoine_change` sur chaque PATCH/DELETE de `patrimoine_crud.py`.

---

## 4. Règle cascade — `batch_cascade_recompute_sites`

Toute création / import / mutation amont de site doit déclencher la cascade canonique :

```python
from regops.services.cascade_recompute_service import batch_cascade_recompute_sites

cascade_summary = batch_cascade_recompute_sites(
    db,
    site_ids=[...],
    org_id=org_id,
    user_id=user_id,
    correlation_id=correlation_id,
    ip_address=ip_address,
    user_agent=user_agent,
)
```

Sortie :

```python
{
    "processed": 3,
    "recomputed": 2,           # sites avec output différent → setattr + audit
    "pending_recompute": 1,    # sites sans surface → audit cascade_pending
    "up_to_date": 0,           # sites déjà à jour → silent
    "errors": 0,
    "sites": [
        {"site_id": 1, "status": "recomputed", "fields_updated": ["cabs_kwh_m2_an", "compliance_score_composite"]},
        {"site_id": 2, "status": "pending_recompute", "missing": ["surface_m2|tertiaire_area_m2"]},
        {"site_id": 3, "status": "up_to_date"},
    ],
}
```

**Idempotence garantie** : re-jouer la fonction sur les mêmes site_ids sans changement amont → `up_to_date` partout, aucune écriture, aucun audit log superflu.

**Wirings actuels** :
- `routes/import_sites.py:import_sites_csv` (bulk)
- `routes/patrimoine_crud.py:quick_create_site_crud` (création individuelle)

---

## 5. Règle anti-erreur silencieuse

Un échec de recompute conformité **doit** :
- soit rollback + HTTP 500 standardisé (préféré MVP) ;
- soit mutation persistée mais statut `pending_recompute` audit (uniquement pour cascades en file d'attente différée — Sprint P1+).

**Erreur standard** (MVP) :

```json
{
  "detail": {
    "code": "PATRIMOINE_RECOMPUTE_FAILED",
    "message": "Le site a été modifié mais le recalcul réglementaire a échoué.",
    "hint": "Réessayez ou vérifiez les données du site.",
    "correlation_id": "uuid-...",
    "blocking": true
  }
}
```

**Source-guard AST** : `test_patrimoine_crud_audit_log_wiring_source_guards.py:test_no_swallow_recompute_in_crud_sites` — interdit tout `try/except` qui log un `warning` sans `raise` dans `update_site_crud`.

---

## 6. Frontend canonique

Fichier de référence : `frontend/src/services/api/patrimoine.js`. P0-A 2026-05-23 — toutes les fonctions exportées pointent désormais sur le namespace `/api/patrimoine/*` :

| Fonction JS | URL | Statut |
|---|---|---|
| `getSites(params)` | `GET /patrimoine/sites` | ✅ canonique |
| `getSite(id)` | `GET /patrimoine/sites/{id}` | ✅ |
| `createSite(data)` | `POST /patrimoine/crud/sites` | ✅ |
| `quickCreateSite(data)` | `POST /patrimoine/crud/sites/quick-create` | ✅ |
| `crudCreateSite/Update/Delete*` | `POST/PATCH/DELETE /patrimoine/crud/*` | ✅ |
| `patrimoineSites*` (premium) | `/patrimoine/sites/*` | ✅ |

Le composant `frontend/src/components/QuickCreateSite.jsx` importe `quickCreateSite` depuis `services/api` (shim) — aucun changement nécessaire après migration de l'URL côté service.

---

## 7. Tests verrous

| Test | Verrou |
|---|---|
| `tests/test_legacy_sites_route_gone.py` | 3 endpoints legacy retournent 410 + payload FR + replacement pointer |
| `tests/test_patrimoine_crud_audit_log_wiring.py` | 9 endpoints CRUD écrivent un AuditLog (Org/EJ/PF/Site/Batiment × PATCH+DELETE) |
| `tests/test_bulk_import_triggers_cascade.py` | Import CSV → cascade summary + audit log par site |
| `tests/test_patch_crud_site_raises_on_recompute_failure.py` | Échec recompute → 500 + rollback + payload standard |
| `tests/source_guards/test_patrimoine_crud_audit_log_wiring_source_guards.py` | AST : chaque PATCH/DELETE contient `log_patrimoine_change` ; aucun try/except swallow dans `update_site_crud` |

---

## 8. Roadmap (post P0-A/P0-B)

### Livré P0-B (2026-05-23)

- ✅ **Audit log sur les 4 endpoints POST création** (organisations, entites, portefeuilles, batiments) — pattern uniforme avec `_audit_headers` + `log_patrimoine_change(action="<entity>.create")`. Verrouillé par source-guard AST `test_patrimoine_crud_post_audit_log_source_guards.py`.
- ✅ **DATA_MISSING enrichi** : `RuleApplicability.to_dict()` auto-injecte `remediation_field`, `remediation_level`, `remediation_label_fr`, `remediation_hint_fr`, `cta_label_fr`, `affected_site_ids` quand `status == DATA_MISSING`. SoT : `backend/regulatory/remediation.py:REASON_CODE_TO_REMEDIATION`. Verrouillé par source-guard `test_data_missing_remediation_source_guards.py`.
- ✅ **CadreApplicable interactif** : clic sur tuile DATA_MISSING ouvre un panneau interne listant les sites concernés + leur champ manquant + CTA `Compléter dans Patrimoine` qui navigue vers `/patrimoine?incomplete=<RULE>`.
- ✅ **Patrimoine filtré** : URL `?incomplete=<RULE>` déclenche un bandeau FR + filtre la table sur les sites incomplets pour cette règle (fetch `/api/regulatory/applicability`).
- ✅ **Onboarding consolidé** : `/onboarding` redirige désormais vers `/onboarding/sirene` (parcours canonique) au lieu de l'impasse `/cockpit/jour`. Décision produit dans §9.

### Reste à faire (P1+)

- **P1** : basculer en 410 les `GET /api/sites/{id}/stats|guardrails|compliance` une fois les équivalents `/api/patrimoine/...` livrés.
- **P1** : écran de saisie au niveau Organisation/EJ (champs effectif, CA, bilan, conso) — actuellement `IncompleteBanner` affiche "écran en préparation" pour les `remediation_level=organisation|entite_juridique`.
- **P2** : unifier `Compteur` ↔ `Meter` (ADR-D-01) et `EnergyContract` ↔ `ContratCadre`.
- **P2** : audit log sur POST création des sous-entités plus marginales (Compteur, DeliveryPoint) — pattern uniforme à étendre.

---

## 9. Onboarding patrimoine — entrées canoniques (P0-B 2026-05-23)

> Décision produit applicable depuis 2026-05-23. Avant P0-B, 5 entry-points coexistaient sans hiérarchie claire et `/onboarding` redirigeait vers une impasse fonctionnelle.

| Cas d'usage | Composant canonique | Accès |
|---|---|---|
| **Création initiale** (premier patrimoine, depuis zéro) | `pages/SireneOnboardingPage` | Route `/onboarding/sirene`. `/onboarding` redirige automatiquement ici. |
| **Import massif** (CSV/Excel multi-sites) | `components/PatrimoineWizard` | Bouton "Importer" dans Patrimoine + empty-state "Importer CSV". |
| **Création manuelle d'un site** (cas par cas) | `components/QuickCreateSite` | Bouton "Nouveau site" dans Patrimoine + empty-state "Nouveau site manuel". |
| **Création détaillée 7 étapes** (option avancée) | `components/SiteCreationWizard` | Sous-composant interne de `QuickCreateSite` (option "Avancé"). **N'est plus une entrée principale.** |
| **Édition incrémentale** | `components/DrawerEditSite` | Clic sur une ligne dans la table Patrimoine. |

### Composants neutralisés

- `pages/OnboardingPage` : **plus aucune route active**. Le fichier est conservé pour réutilisation Phase 4 (refonte premier pas COMEX) mais n'est ni importé, ni monté. Aucune URL ne le rend.

### Empty-state Patrimoine = écran d'aiguillage

Quand l'utilisateur arrive sur `/patrimoine` sans aucun site dans le scope, l'écran propose les 3 chemins canoniques en français :

1. **Depuis Sirene (recommandé)** → `/onboarding/sirene`
2. **Nouveau site manuel** → ouvre `QuickCreateSite`
3. **Importer CSV** → ouvre `PatrimoineWizard`

C'est l'aiguillage canonique. Aucun écran d'aiguillage séparé n'est nécessaire.

### Source-guard

`frontend/src/__tests__/onboarding_entrypoints.test.jsx` verrouille :
- `/onboarding` redirige vers `/onboarding/sirene` (pas vers `/cockpit/jour`).
- `OnboardingPage` n'est plus montée en route active.
- `SiteCreationWizard` n'est pas attaché à une `<Route>` (sous-composant uniquement).
- Patrimoine empty-state propose les 3 chemins FR.

---

## 10. DATA_MISSING — contrat de remédiation (P0-B)

### Sortie API enrichie

Toute entrée `RuleApplicability` avec `status="data_missing"` expose dans `to_dict()` :

```json
{
  "rule_code": "DT",
  "status": "data_missing",
  "reason_code": "DT.DATA_MISSING.SURFACE",
  "scope_level": "site",
  "scope_id": 42,
  "scope_label": "Site Paris 15e",
  "missing_inputs": ["site.tertiaire_area_m2"],
  "remediation_field": "site.tertiaire_area_m2",
  "remediation_level": "site",
  "remediation_label_fr": "Surface tertiaire",
  "remediation_hint_fr": "Renseignez la surface tertiaire pour confirmer si le site est soumis au Décret Tertiaire.",
  "cta_label_fr": "Compléter la surface",
  "affected_site_ids": [42]
}
```

### Bijection reason_code ↔ remediation

| reason_code | remediation_field | level | label FR |
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

SoT : `backend/regulatory/remediation.py`. Verrou : `test_data_missing_remediation_source_guards.py` impose qu'aucun code DATA_MISSING ne soit ajouté à `reason_codes.py` sans entrée correspondante ici.

### Parcours UI Cockpit → Patrimoine

```
CadreApplicable (Cockpit Stratégique)
  → clic sur tuile "DT · Données manquantes · 4 sites"
  → ouvre panneau interne avec liste des 4 sites + champ manquant FR
  → CTA "Compléter la surface"
  → navigate('/patrimoine?incomplete=DT')

Patrimoine.jsx
  → bandeau FR "Sites à compléter pour le Décret Tertiaire — 4 sites"
  → table filtrée sur les 4 sites concernés
  → bouton "Effacer le filtre" pour revenir à la vue complète
  → clic sur une ligne → DrawerEditSite (édition existante)
```
