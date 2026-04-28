# ADR-005 — ParameterStore tier-2 (mitigation_defaults.yaml)

**Statut** : Accepté
**Date** : 2026-04-28
**Sprint** : S2 Vague C ét14 (post-audit consolidé 9.4/10 + Tier 1 93%)
**Personnes impliquées** : Amine (founder), Claude architect-helios

## Contexte

Sprint 2 Vague C a externalisé progressivement les constantes métier
hardcoded des détecteurs `event_bus` (`_DT_AUDIT_PROXY_CAPEX_EUR=8000`,
`_CAPACITY_COST_PER_MWH_EUR=12.0`, `_DT_NPV_HORIZON_YEAR=2030`…) vers
un fichier YAML versionné `backend/config/mitigation_defaults.yaml`.

Lors de l'audit consolidé post-ét13f (commit `0cf34224`), trois P0
résiduels ont été signalés par 2+ personas :

1. **CFO+Marie** : `contract_renewal.impact.value=None` bloque la
   data-room CFO ; `asset_registry_issue.impact.unit="kWh"` proxy
   ambigu — convertir en € risque.
2. **Architecture** : ADR à formaliser pour figer la convention
   versioning + sources avant d'ajouter un 4ᵉ YAML métier (cohérence
   avec `tarif_loader` / `pricing_lead_score` / `mitigation_defaults`).
3. **Sarah Sequoia** : source `Décret n°2024-XXX` placeholder — un
   partenaire CRE-savvy challengera (résolu : Décret n°2025-1441).

Le repo a déjà 3 fichiers YAML versionnés à des fins différentes :
- `tarifs_reglementaires.yaml` — TURPE 7, ATRD gaz, accises (réglementé strict)
- `pricing_lead_score.yaml` — barèmes scoring lead conversion (commercial)
- `mitigation_defaults.yaml` — proxies CFO/EM pour `EventMitigation` §10

Sans convention formelle, le risque est de :
- Dupliquer des constantes entre fichiers (ex : taux d'actualisation NPV)
- Perdre la traçabilité source (chiffres orphelins anti-pattern §6.5)
- Casser silencieusement les détecteurs au prochain ajout de section
- Multiplier les loaders sans interface commune

## Décision

### Tier 1 vs Tier 2

| Tier | Périmètre | Fichiers | Versioning | Loader |
|---|---|---|---|---|
| **Tier 1 — Réglementaire strict** | Constantes officielles JO/CRE/ADEME | `tarifs_reglementaires.yaml`, `emission_factors.py` (Python figé) | Sémantique stricte (1.0.0 = grilles 2026) | `tarif_loader.py`, `config.emission_factors` |
| **Tier 2 — Proxies métier** | Hypothèses CFO/EM/marché documentées (médianes mid-market, sources Observatoire CRE, retours marketplace) | `mitigation_defaults.yaml`, `pricing_lead_score.yaml` | Sémantique souple (1.0.0 = défauts initiaux, x.y patch sans rupture API) | `mitigation_loader.py`, `pricing_lead_score_loader.py` |

### Conventions tier-2 obligatoires

1. **Header YAML** :
   ```yaml
   version: "1.0.0"
   last_updated: "YYYY-MM-DD"
   ```

2. **Source citée par champ** : tout chiffre `X` doit être accompagné
   d'un champ jumeau `X_source: "..."` mentionnant :
   - Référence officielle (CRE délibération, Décret JO, ADEME guide)
   - OU « Observatoire » + période (ex : « Observatoire CRE T4 2025 »)
   - OU « Retours marketplace » + millésime
   - OU « Estimation interne » + raison

3. **DTO frozen typé** : chaque section YAML expose une dataclass
   `@dataclass(frozen=True)` dans le loader Python. Le caller ne lit
   jamais le YAML brut — uniquement via le DTO typé.

4. **`@lru_cache` + `reload()`** : performance lecture + capacité de
   patch en test (pattern `tarif_loader.py`).

5. **Tests obligatoires** :
   - `test_<section>_yaml_loader_returns_typed_defaults` (chargement)
   - Validation des plages raisonnables (taux 0-20 %, € > 0…)
   - Validation présence des champs `*_source`

6. **Pas de duplication cross-tier** : si un chiffre doit vivre dans
   plusieurs YAML, le placer en tier-1 (réglementaire) et le tier-2 le
   référence par chemin (`tarifs.turpe.c5_bt.energie_eur_kwh`).

### Convention versioning

- **`1.0.0`** : version initiale livrée
- **`1.x.0`** : ajout d'une nouvelle section (compatible ascendant)
- **`1.0.x`** : modification d'une valeur existante (sources mises à jour)
- **`2.0.0`** : refonte structure / renommage section / suppression champ

Le champ `version:` du YAML doit toujours être incrémenté quand un
champ structurel change. Le `last_updated:` à la date courante.

### Sections actuelles `mitigation_defaults.yaml` (état Vague C ét14)

| Section | Détecteur consommateur | DTO loader |
|---|---|---|
| `discount_rate` (root) | tous (NPV) | `get_discount_rate()` |
| `dt_compliance` | `compliance_deadline_detector` | `DtComplianceDefaults` |
| `consumption_drift` | `consumption_drift_detector` | `ConsumptionDriftDefaults` |
| `contract_renewal` | `contract_renewal_detector` | `ContractRenewalDefaults` |
| `asset_registry` | `asset_registry_issue_detector` | `AssetRegistryDefaults` |
| `market_capacity_2026` | `market_window_detector` | `MarketCapacity2026Defaults` |

## Conséquences

### Positives

- **Defensibility CFO** : tout chiffre exposé en UI a une source citée
  inline (tooltip methodology) — règle d'or chiffres 27/04 respectée
  100 % sur les 9 détecteurs.
- **Patch sans déploiement** : le CFO d'une org peut écraser
  `discount_rate` en post-prod via simple commit YAML versionné, sans
  touche code Python.
- **Audit data-room** : un investisseur CRE-savvy peut auditer en
  ouvrant un seul fichier YAML (vs grep multi-fichiers).
- **Cohérence cross-détecteur** : `proxy_volume_per_annex_mwh` et
  `proxy_consumption_mwh_per_site` peuvent être harmonisés (même proxy
  100 MWh) avec une source commune ADEME.

### Négatives

- **Coût ajout détecteur** : un nouveau détecteur requiert désormais
  3 fichiers (détecteur Python + section YAML + DTO loader + test) au
  lieu de 2. Compensé par la traçabilité.
- **Risque dérive** : sans test mutation YAML (P1 backlog), un patch
  non-régressif n'est pas garanti déterministe. À ajouter Vague D.
- **Pas de hot-reload** : modification YAML en prod nécessite restart
  process (cache `@lru_cache`). Acceptable en démo, à corriger pour
  production multi-tenant.

## Plan suivi

- **Vague D ét15** : test mutation YAML (`reload()` post-patch + assert
  NPV recalculé) pour garantir cache invalidation.
- **Vague E** : étendre tier-2 aux 4 détecteurs sans YAML actuel
  (`billing_anomaly` lit `losses_service`, `consumption_drift` partiel,
  `data_quality_issue`, `action_overdue`).
- **Vague F (post-démo)** : migrer vers ParameterStore DB-backed avec
  override per-org (cohérent stratégie Marketplace audits multi-clients).

## Références

- ADR-001 — Grammaire éditoriale Sol industrialisée (cite §10 contract data)
- ADR-002 — Chantier α moteur d'événements (consommateur principal tier-2)
- `backend/config/tarif_loader.py` — pattern `@lru_cache + reload()` réutilisé
- `memory/feedback_chiffres_fiables_verifiables.md` — règle d'or 27/04
- `memory/feedback_kb_naming_convention.md` — conventions YAML projet
- Décret n°2025-1441 (mécanisme capacité 1/11/2026)
