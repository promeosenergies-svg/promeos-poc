# ADR-F-04 — Hard-cut `supplier_name` → `fournisseur_id` (Phase F2 → Phase J2)

**Statut** : 🟢 ACCEPTED — Phase J2 cardinal post Phase I (commit `3473730e` sur `claude/refonte-sol2`)
**Date** : 2026-05-09
**Sprint** : Phase J2 (~1 h granulaires)
**Décideurs** : architect-helios + bill-intelligence + qa-guardian
**Lié** : ADR-F-01 (Fournisseur entité) · ADR-F-02 (Parser PDF facture) · ADR-F-03 (Parser contrat)

## Contexte

ADR-F-01 D2 retenait un **miroir transitoire** : `EnergyContract.supplier_name`
(String) coexiste avec `fournisseur_id` (FK) durant la phase de migration F1.
Phase F2 backfill complété (commit `f72dafea`) : 6 contrats backfillés sur 8 PDLs
seedés (75 % couverture) + 2 unmapped (`Eni`, `Vattenfall` — non-canoniques).

Phase J2 = hard-cut prévu : durcir le contrat de données pour empêcher la
création de nouveaux `EnergyContract` sans `fournisseur_id` résolu.

## Décision

**Soft hard-cut Phase J2** : ajouter une **contrainte applicative** (pas SQL)
qui force `fournisseur_id NOT NULL` sur les nouveaux EnergyContract créés
post-J2. La colonne `supplier_name` reste pour rétro-compatibilité historique
(8 PDLs seedés, dont 2 non-canoniques) — DROP différé Phase K.

### Décisions granulaires

| ID | Décision | Choix retenu |
|---|---|---|
| **D1** | Hard-cut DDL (`fournisseur_id NOT NULL` migration) | **NON** Phase J2 — risque casser data legacy |
| **D2** | Hard-cut applicatif via `__init__` override (vs @validates) | **OUI** — `EnergyContract.__init__` override choisi car @validates ne fire que sur SET explicite, alors que `__init__` couvre aussi les cas où `fournisseur_id` n'est pas fourni du tout (cas le plus fréquent du bug). Mode soft (warn) par défaut + `PROMEOS_J2_HARDCUT=1` strict. Override legacy via `metadata_json["phase_j2_legacy"]=true` |
| **D3** | DROP `supplier_name` colonne | **NON** — reporté Phase K (pattern Phase D-4 anti-DROP discipline 19 épisodes) |
| **D4** | Test source-guard anti-régression | **OUI** — `test_j2_no_new_energy_contract_without_fournisseur_id` |

## Implémentation Phase J2

1. **Validator `@validates("fournisseur_id")` sur EnergyContract** :
   - Si nouvelle ligne (state transient) ET `fournisseur_id is None` ET pas de flag legacy → ValueError
   - Permet override via `metadata_json={"phase_j2_legacy": true}` pour data import historique

2. **Helper `services/billing_engine/energy_contract_factory.py`** : créer ou
   réutiliser une factory function qui force la résolution Fournisseur avant
   instanciation EnergyContract.

3. **Test source-guard** : tentative de créer EnergyContract sans `fournisseur_id`
   raise ValueError avec message explicit Phase J2.

## Conséquences

**Positives** :
- Contrat data hardened : impossible de créer EnergyContract orphelin post-J2
- Nettoyage progressif : `supplier_name` reste pour 8 PDLs legacy historiques
- Migration douce : pas de risque de casser tests existants ou data seed

**Négatives** :
- 2 unmapped historiques (`Eni`, `Vattenfall`) non couverts par canoniques —
  besoin d'ajouter au seed ou créer privés tenant
- Validator applicatif moins strict que NOT NULL DDL — risque bypass via
  raw SQL ou bulk insert (acceptable car PROMEOS n'utilise que ORM)

**Neutres** :
- DROP supplier_name reporté Phase K (pattern Phase D-4 anti-DROP cohérent)

## Tests cardinaux (3)

| ID | Description |
|---|---|
| T-J2-01 | EnergyContract sans fournisseur_id + sans flag legacy → ValueError Phase J2 |
| T-J2-02 | EnergyContract avec fournisseur_id valide → OK |
| T-J2-03 | EnergyContract avec metadata_json["phase_j2_legacy"]=true sans fournisseur_id → OK (override import historique) |

## Liens

- ADR-F-01 D2 (miroir transitoire)
- ADR-F-02 (parser PDF facture résolution Fournisseur)
- `models/billing_models.py:61` (supplier_name field)
- `models/billing_models.py:160` (fournisseur_id FK Phase F1)
- `services/fournisseur_resolver_service.py` (résolution composite SIREN + name)
