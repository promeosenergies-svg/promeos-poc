# Shadow Billing — Refactor V112

**Branche** : `feat/billing-engine-refactor`
**Commits** : `5be66788` (PR1 fondations), `638d78d7` (PR2 câblage)

## Objectif

Remplacer l'architecture en fallback cascadé du moteur shadow billing
(DB → YAML → hardcodé, avec divergences silencieuses entre sources) par
une **source unique de vérité versionnée** : `ParameterStore`.

## Ce qui a changé

### 1. Nouvelle couche : `ParameterStore`

Fichier : [`services/billing_engine/parameter_store.py`](parameter_store.py)

- Interface unique : `ParameterStore.get(code, at_date, scope) -> ParameterResolution`
- Résolution interne : DB regulated_tariffs → YAML tarifs_reglementaires → `missing`
- **Versioning temporel strict** par `valid_from` / `valid_to` avec sélection
  du candidat dont `valid_from` est le plus récent couvrant `at_date`.
- Audit trail sur chaque lookup : `source`, `source_ref`, `valid_from`,
  `valid_to`, `scope`.
- Codes connus listés explicitement (`KNOWN_CODES`) — lookup d'un code inconnu
  déclenche un warning + retourne `source="missing"` au lieu de `0.0` silencieux.

Cas testés (24 tests, `tests/test_parameter_store.py`) :
- TURPE 6 → TURPE 7 césure 1/08/2025 (avant : 0.0282, après : 0.0453 EUR/kWh)
- Accise gaz 3 périodes (jan-jul 2025, aout 2025 – jan 2026, fév 2026+)
- TVA réduite supprimée au 1/08/2025 (5,5% → 20%)
- CTA gaz distribution (20,80% stable)
- CTA élec distribution 15% à partir de fév 2026
- Code inconnu → missing + warning
- Audit trail sérialisable

### 2. Nouvelle brique : `compute_cta`

Fichier : [`services/billing_engine/bricks/cta.py`](bricks/cta.py)

Remplace le stub historique (taux 15% hardcodé ligne 720 de `billing_shadow_v2.py`)
par un calcul conforme à la doctrine :

```
CTA = assiette_fixe_proratisée × taux_versionné
```

- `assiette_fixe` = part fixe annuelle du tarif d'acheminement (TURPE gestion
  pour l'élec, ATRD abonnement T1-T4 pour le gaz — actuellement 0 pour le gaz
  en attendant PR3).
- `taux_versionné` = valeur par (energy, network_level, date) via
  `ParameterStore.get("CTA_ELEC_DIST_RATE", at_date)`, etc.
- Supports élec/gaz × distribution/transport.
- `CtaResult` porte l'audit trail complet.

Cas testés (10 tests, `tests/test_billing_cta_brick.py`) :
- CTA gaz distribution 20,80% (plein an + prorata mensuel)
- CTA élec distribution 15% depuis fév 2026
- CTA élec transport 5% depuis fév 2026
- Audit trail + `to_dict()` serialization
- Bornes de période + edge cases (période négative, assiette 0)

### 3. Câblage dans `billing_shadow_v2.py`

- `_safe_rate(code, at_date, db)` route d'abord par `ParameterStore` avant
  de retomber sur la cascade legacy (rétrocompat).
- `compute_shadow_breakdown()` instancie un `ParameterStore` local et appelle
  `compute_cta(store, energy, fixed_component_annual_eur, period_days, at_date)`
  en passant explicitement `at_date = invoice.period_start`.
- Le résultat dict porte désormais `"calc_version": "v2_parameter_store"`
  pour permettre aux consommateurs de détecter la génération du breakdown.
- Docstring du module documente l'ordre de calcul obligatoire :
  `énergie → fourniture → acheminement → CTA → CEE → accise → TVA`.

### 4. Fix YAML — continuité CTA 21,93%

Fichier : `referentials/market_tariffs_2026.yaml`

Le taux CTA historique 21,93% (`cta_2021`) s'arrêtait au 31/12/2025, alors
que la nouvelle grille CRE 2026-14 ne prend effet qu'au 1/02/2026. Le mois
de janvier 2026 tombait dans un trou → `price_decomposition_service` retournait
`cta_eur_mwh=0` avec warning "taux non trouvé". `valid_to` étendu au 31/01/2026.

### 5. Tests ajoutés

- `tests/test_parameter_store.py` — 24 tests, couvre le versioning temporel
- `tests/test_billing_cta_brick.py` — 10 tests, couvre la brique CTA
- `tests/test_billing_pipeline_v112.py` — 13 tests, invariants de sortie +
  versioning temporel + CTA réelle + audit trail

## Compatibilité ascendante

- Toutes les signatures publiques sont préservées :
  `shadow_billing_v2(invoice, lines, contract, db=None)` reste identique.
- `config.tarif_loader.get_cta_taux` accepte maintenant un paramètre optionnel
  `at_date` (défaut = `date.today()`) — les appelants existants ne sont pas
  impactés.
- Le dict retourné par `shadow_billing_v2` contient toujours les mêmes clés,
  avec en plus `calc_version`.
- Les tests pré-existants passent sans modification (1 ajustement de
  rounding tolerance dans `test_shadow_v2_elec_components` + 1 ajustement
  de guard source dans `test_step28_shadow_breakdown::test_cta_taux_used`).

## Impact sur les factures existantes

- Les factures pré-V112 ont été calculées via le stub CTA 15% + fallback
  accise non versionné. Les nouvelles factures utilisent les taux réels
  versionnés par date d'effet.
- Le champ `calc_version` permet à l'UI ou à un batch de re-calcul de
  distinguer les breakdowns anciens (`absent` ou `"v2_catalog"`) des nouveaux
  (`"v2_parameter_store"`).
- Aucune migration de données — la réconciliation se fait à la volée à chaque
  appel de `compute_shadow_breakdown`.

## PR3 — backlog restant

Cette PR ne couvre pas (à traiter dans un refactor ultérieur) :

1. **Découpage automatique des périodes à cheval** sur un changement
   réglementaire (facture 15/07/2025 → 15/08/2025 doit être splittée en
   deux sous-périodes pour appliquer TURPE 6 sur la première et TURPE 7
   sur la seconde). Aujourd'hui on utilise `period_start` comme date unique.

2. **Éclatement modulaire de `billing_shadow_v2.py`** (954 lignes) en
   modules `bricks/fourniture.py`, `bricks/reseau.py`, `bricks/cee.py`,
   `bricks/accise.py`, `bricks/tva.py` pour symétrie avec `bricks/cta.py`.

3. **ATRD gaz par option T1-T4** — l'assiette fixe CTA gaz est actuellement
   à 0 car le modèle `EnergyContract` n'expose pas encore l'option ATRD.
   Ajouter un champ `atrd_option` (enum T1/T2/T3/T4) sur `SiteContextGas`
   et lire la grille ATRD7 depuis le YAML.

4. **CEE réel** (coefficient P5/P6 × prix CEE) au lieu du stub informatif
   5 EUR/MWh.

5. **ATS** (Accès aux Stockages) en ligne dédiée dans le breakdown gaz.

6. **Prestations annexes** (catalogues GRD/GRT) — actuellement absentes.

## Comment vérifier manuellement

```bash
cd backend
python -m pytest tests/test_parameter_store.py tests/test_billing_cta_brick.py \
                 tests/test_billing_pipeline_v112.py tests/test_billing_v68.py \
                 tests/test_shadow_billing_gas.py tests/test_shadow_billing_bridge.py \
                 tests/test_step28_shadow_breakdown.py tests/test_price_decomposition.py
# 170/170 passed
```

Quick smoke test ParameterStore :

```python
from datetime import date
from services.billing_engine.parameter_store import ParameterStore

store = ParameterStore()
print(store.get("TURPE_ENERGIE_C5_BT", date(2025, 6, 1)).value)   # 0.0282 (TURPE 6)
print(store.get("TURPE_ENERGIE_C5_BT", date(2025, 10, 1)).value)  # 0.0453 (TURPE 7)
print(store.get("ACCISE_GAZ", date(2026, 4, 1)).value)            # 0.01073
print(store.get("CTA_ELEC_DIST_RATE", date(2026, 4, 1)).value)    # 0.15
```
