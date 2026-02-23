# V58 — Patrimoine : Single Source of Truth & Anomalies

**Date** : 2026-02-23
**Statut** : IMPLÉMENTÉ
**Sprint** : V58

---

## Contexte

Audit patrimoine (V56) a identifié 3 problèmes critiques. Phase 1 (V57) a éliminé les `Organisation.first()`. Phase 2 (V58) définit le Single Source of Truth (SoT) pour les données patrimoine et implémente les contrôles d'intégrité.

---

## FAITS (vérifiés dans le code)

| Fait | Localisation | Détail |
|------|-------------|--------|
| `surface_m2` stocké en 4 lieux | Site, Batiment, StagingSite, TertiaireEfaBuilding | |
| `tertiaire_service.py` fait déjà `sum(b.surface_m2)` | `services/tertiaire_service.py:309` | Pattern éprouvé |
| `analytics_engine.py` utilise `site.surface_m2` | `services/analytics_engine.py:113` | Pour kWh/m²/an |
| `EnergyContract` n'a PAS de SoftDeleteMixin | `models/billing_models.py` | Seulement TimestampMixin |
| `EnergyContract.start_date` et `end_date` sont nullable | `models/billing_models.py:35-36` | Les deux |
| `Batiment` a `SoftDeleteMixin` | `models/batiment.py:10` | `deleted_at` nullable |
| Deux modèles "meter" distincts | `models/compteur.py`, `models/energy_models.py` | Rôles différents |
| `Usage` n'a PAS de SoftDeleteMixin | `models/usage.py:11` | Seulement TimestampMixin |

---

## DÉCISIONS

### D1 — Surface SoT

```
surface_sot_m2 =
  sum(b.surface_m2 for b in batiments if not b.deleted_at)  # si nb > 0
  else site.surface_m2                                        # fallback
  # sinon None
```

**Raison** : cohérent avec `tertiaire_service.py` (pattern déjà existant). Ne casse aucun service existant car `analytics_engine` et `audit_report` continuent d'utiliser `site.surface_m2` directement.

**Tolérance SURFACE_MISMATCH** : 5 % (constante `SURFACE_MISMATCH_TOLERANCE` dans `services/patrimoine_snapshot.py`).

### D2 — `contract.delivery_point_id` : REPORTÉ V59

**Décision** : Ne pas ajouter `delivery_point_id` sur `EnergyContract` en V58.

**Raisons** :
1. `EnergyContract` n'a pas de `SoftDeleteMixin` → migration Alembic non triviale
2. Valeur immédiate limitée (les contrats sont liés aux sites, pas aux compteurs individuels)
3. La règle `METER_NO_DELIVERY_POINT` couvre déjà le gap entre Compteur et DeliveryPoint

**Backlog V59** : Ajouter `EnergyContract.delivery_point_id` (nullable FK) avec migration et SoftDeleteMixin.

### D3 — Nomenclature Compteur/Meter : STATU QUO

**Deux modèles coexistent** :
- `Compteur` (`models/compteur.py`) : entité patrimoine métier (CRUD, delivery_point FK, actif, soft-delete)
- `Meter` (`models/energy_models.py`) : entité analytics (lectures, profils, anomalies KB)

**Décision** : Garder les deux. Le snapshot expose `compteurs` (métier) et pas les `Meter` analytics. Documentation dans `docs/dev/patrimoine_snapshot_contract.md`.

### D4 — Pas de table DB pour les anomalies patrimoine

**Décision** : Anomalies calculées à la demande, non persistées.

**Raisons** :
1. Zéro migration
2. Données toujours fraîches
3. Évite la complexité d'un moteur de synchronisation
4. Performance acceptable avec pagination

**Backlog V59** : Cache Redis ou table temporaire si le calcul devient lent (> 500 ms par site).

### D5 — Routes dans `routes/patrimoine.py` existant

**Décision** : Ajouter les endpoints V58 dans le fichier existant (pas de nouveau routeur).

**Endpoints ajoutés** :
- `GET /api/patrimoine/sites/{site_id}/snapshot`
- `GET /api/patrimoine/sites/{site_id}/anomalies`
- `GET /api/patrimoine/anomalies` (liste org paginée)

### D6 — Frontend : enrichir SiteDrawer existant

**Décision** : Nouveau composant `PatrimoineHealthCard.jsx` intégré dans l'onglet "Anomalies" du SiteDrawer existant. Pas de refacto de `Patrimoine.jsx` au-delà du minimum.

**Impact** : L'onglet "Anomalies" qui montrait un compteur statique (`site.anomalies_count`) affiche maintenant le score de complétude + top 3 anomalies actionnables en temps réel.

### D7 — Score de complétude

```
score = max(0, 100 - Σ penalty)

Pénalités :
  CRITICAL → 30 pts
  HIGH     → 15 pts
  MEDIUM   →  7 pts
  LOW      →  3 pts
```

---

## 8 Règles P0

| Code | Sévérité | Condition | Evidence |
|------|----------|-----------|---------|
| `SURFACE_MISSING` | HIGH | surface_sot_m2 manquante ou nulle | surface_site_m2 |
| `SURFACE_MISMATCH` | MEDIUM | \|site.surface_m2 - ∑bat\| > 5 % | ecart_pct |
| `BUILDING_MISSING` | MEDIUM | 0 bâtiment | nb_batiments |
| `BUILDING_USAGE_MISSING` | LOW | bâtiment sans usage | batiment_id, nom |
| `METER_NO_DELIVERY_POINT` | MEDIUM | compteur sans delivery_point_id | compteur_id |
| `CONTRACT_DATE_INVALID` | HIGH | start >= end (quand les deux present) | start/end dates |
| `CONTRACT_OVERLAP_SITE` | HIGH | chevauchement contrats même énergie | contract_id_1,2 |
| `ORPHANS_DETECTED` | CRITICAL | site actif=False avec enfants actifs | nb_enfants |

---

## Impact sur le code existant

| Fichier | Modification | Impact |
|---------|-------------|--------|
| `routes/patrimoine.py` | +3 endpoints | Ajout uniquement, aucune modif |
| `services/api.js` | +3 wrappers | Ajout uniquement |
| `pages/Patrimoine.jsx` | Remplacement onglet Anomalies | Amélioration, compat maintenue |
| `models/*` | Aucun | Zéro migration |

---

## Tests

- `backend/tests/test_patrimoine_snapshot_v58.py` : 10 tests (service + endpoint)
- `backend/tests/test_patrimoine_anomalies_v58.py` : 25+ tests (8 règles + score + endpoints)
- `frontend/src/pages/__tests__/patrimoineV58.test.js` : 30+ guards source
