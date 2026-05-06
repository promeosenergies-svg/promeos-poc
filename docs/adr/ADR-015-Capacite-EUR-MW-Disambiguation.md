# ADR-015 — Capacité EUR/MW disambiguation (clarification documentaire)

**Statut** : Accepté
**Date** : 2026-05-05
**Sprint** : C-5 Phase 0 (build Phase 5.2)
**Personnes impliquées** : Amine (founder), Claude architect-helios + bill-intelligence
**Tracking dette** : `D-Phase4-2-Capacite-EUR-MW-Disambiguation-001` (P0 reclassif Phase 4.2d) → CLÔTURÉE Phase 5.2

---

## Contexte

L'audit multi-agents Sprint C-4 Phase 4.2d (commit `d131205d`) a flaggé une **disambiguation EUR/MW** entre 2 valeurs apparemment incohérentes utilisées dans le code billing/revenue PROMEOS :

- `config/sources_reglementaires.yaml` : `CAPACITE_RTE_TARIF_2026_EUR_PER_MW: 3.15` (Sprint C-4 Phase 4.2)
- `services/billing_engine/catalog.py:878-882` : `"3.15 EUR/MW × coeff 1.2 / 8760h ≈ 0.43 EUR/MWh"` (catalogue tarifs)
- `services/purchase/cost_simulator_2026.py:60-64` : `CAPACITE_UNITAIRE_EUR_MWH = 0.43` (constante calculée)
- `services/purchase/revenue.py` (référencé) : `PRIX_MOYEN_MW_AN PL1` = **3 150 EUR/MW.an** (3 zéros différents)

Risque audit / consultant énergie : "3.15 vs 3 150 = facteur × 1 000 d'erreur, lequel est correct ?"

### Audit Phase 0 Sprint C-5 — diagnostic terrain

**Code actuel = MATHÉMATIQUEMENT CORRECT** mais **documentation insuffisante** :

- **3.15 EUR/MW** = prix unitaire **enchère capacité RTE 06/03/2025** (livraison 2026, 1 certificat = 1 MW pendant période d'obligation)
- **3 150 EUR/MW.an** = prix moyen indicatif PL1 (Plage 1 obligation = 20-50k EUR/MW.an indicatif fourchette CRE/RTE — placeholder revenue.py historique avant enchères 2025)

**Clarification mathématique** :

```
Tarif RTE livraison 2026 = 3.15 EUR/MW × coeff 1.2 (obligation 2026) / 8760 h ≈ 0.43 EUR/MWh
                         ≈ 0.00043 EUR/kWh × 1 000 MWh = 0.43 EUR/MWh ✓

Placeholder revenue.py PL1 = 3 150 EUR/MW.an (obsolète 2026 — fourchette indicative pré-enchères)
                           ≈ 1 000 × tarif RTE 2026 réel
                           → divergence = unité différente (EUR/MW.an vs EUR/MW livraison)
```

→ **Pas de bug runtime**. Disambiguation = **clarification documentaire** dans 3 emplacements :

1. YAML `sources_reglementaires.yaml` : enrichir notes (déjà partiellement présent — Sprint C-4 Phase 4.2)
2. Catalog `services/billing_engine/catalog.py` : docstring source précise enchère RTE 06/03/2025
3. Code `services/purchase/revenue.py` : commentaire `PRIX_MOYEN_MW_AN PL1 = 3150` placeholder historique (à reconcilier ou supprimer Sprint C-7)

### Diagnostic catalog actuel

```python
# backend/services/billing_engine/catalog.py:878-882
{
    # → 3.15 × 1.2 / 8760 ≈ 0.00043 EUR/kWh × 1000 = 0.43 EUR/MWh
    ...
    "source": "Enchères capacité RTE 06/03/2025 — 3.15 EUR/MW × coeff 1.2 / 8760h ≈ 0.43 EUR/MWh",
}
```

Bonne pratique déjà en place. Manque : référence YAML (`CAPACITE_RTE_TARIF_2026_EUR_PER_MW`) pour traçabilité TraceTooltip R10.

### Diagnostic cost_simulator_2026 actuel

```python
# backend/services/purchase/cost_simulator_2026.py:60-64
# (enchère 06/03/2025 : 3.15 EUR/MW × coeff obligation 1.2 / 8760h ≈ 0.43 EUR/MWh).
CAPACITE_UNITAIRE_EUR_MWH = 0.43
```

Bonne pratique aussi. Manque : import depuis YAML loader (cohérence pattern Sprint C-3 — pas de hard-code).

---

## Décision

### Option retenue : **Clarification documentaire MVP — pas de refactor structural**

3 options arbitrées Phase 0 Sprint C-5 :

| Option | Périmètre | Effort | Verdict |
|---|---|---|---|
| **A** | **Clarification documentaire (notes YAML + docstring code + retour vers YAML loader)** | ~30 min | ✅ **RETENUE** |
| B | Refactor `cost_simulator_2026.py` + `catalog.py` pour consommer YAML loader directement | ~1.5-2 h | Reportée Sprint C-7 polish |
| C | Suppression placeholder `PRIX_MOYEN_MW_AN PL1 = 3150` dans `revenue.py` | ~30 min | Reportée Sprint C-7 (audit usages) |

### Justifications Option A

1. **Pas de bug runtime** — code mathématiquement correct (0.43 EUR/MWh = 3.15 × 1.2 / 8760 vérifié)
2. **Effort proportionné** — Sprint C-5 ~3-5 j-h budget, ne pas surdépenser sur clarif documentaire
3. **Refactor B reporté Sprint C-7 polish** — pattern `tarif_loader.py` Sprint C-3 (Phase 3.2) à étendre `capacite_loader.py` cohérence ; pas urgence MVP pré-pilote
4. **Suppression C reportée** — `revenue.py PRIX_MOYEN_MW_AN` peut avoir consumers actifs (audit Sprint C-7 requis avant suppression destructive)
5. **TraceTooltip R10 cohérence** — clarif YAML `notes:` enrichi suffit MVP frontend (CFO peut lire "3.15 EUR/MW × 1.2 / 8760 = 0.43 EUR/MWh — enchère RTE 06/03/2025")

---

## Conséquences

### Positives

- **Disambiguation auditable** — toute revue code/legal trouve la formule + référence enchère RTE 06/03/2025
- **Effort minimal** — ~30 min Sprint C-5 Phase 5.2, pas d'impact baseline tests
- **TraceTooltip enrichi** — `notes:` YAML lisible CFO via R10 différenciateur
- **Pas de risque régression** — pure documentation, code intouché

### Négatives

- **Hard-code constant `0.43` reste dans `cost_simulator_2026.py`** — pas de single source of truth runtime YAML (dette `D-Sprint-C7-Capacite-Loader-Refactor-001` P2 à créer)
- **Placeholder `3 150` dans `revenue.py` reste** — confusion potentielle reportée Sprint C-7 (dette `D-Sprint-C7-Revenue-Capacite-Placeholder-Cleanup-001` P2 à créer)
- **Pas de source-guard cohérence YAML ↔ catalog/cost_simulator** — manuel pour Sprint C-5, automatisable Sprint C-7

### Mitigation

- **Note YAML enrichie** explicit : "Disambiguation : 3.15 EUR/MW (livraison 2026 enchère RTE 06/03/2025) ≠ 3 150 EUR/MW.an (placeholder PL1 obsolète revenue.py — Sprint C-7 cleanup)"
- **2 dettes P2 ouvertes Sprint C-7** pour traçabilité refactor futur
- **Audit `regulatory-expert` validation** — Sprint C-7 polish multi-agents pour valider cohérence finale

---

## Implémentation Sprint C-5 Phase 5.2

### Modifications (~30 min, P0 reclassif)

#### 1. `config/sources_reglementaires.yaml` — enrichir `notes` (déjà partiellement présent)

```yaml
CAPACITE_RTE_TARIF_2026_EUR_PER_MW:
  value: 3.15
  unit: "EUR/MW"
  effective_date: "2026-01-01"
  legal_reference: "Enchères RTE 06/03/2025 livraison 2026"
  source: "https://www.services-rte.com/files/live/sites/services-rte/files/documentsLibrary/2025-03-06_Enchères_capacité_2026"
  notes: |
    Tarif unitaire enchère RTE 06/03/2025 pour livraison 2026.
    Conversion EUR/MWh : 3.15 × coeff_obligation_2026 (1.2) / 8760 h ≈ 0.43 EUR/MWh.
    
    DISAMBIGUATION CRITIQUE :
    - 3.15 EUR/MW (cette valeur) = prix enchère 2026 livraison
    - 3 150 EUR/MW.an = placeholder PL1 obsolète dans services/purchase/revenue.py
      (fourchette indicative pré-enchères, à supprimer Sprint C-7 cleanup)
    
    Consommateurs runtime :
    - services/billing_engine/catalog.py:878-882 (catalog tarifs)
    - services/purchase/cost_simulator_2026.py:60-64 (CAPACITE_UNITAIRE_EUR_MWH = 0.43)
  status: "active"
  confidence: "high"
```

#### 2. `services/billing_engine/catalog.py:878-882` — ajouter référence YAML

```python
{
    # → 3.15 × 1.2 / 8760 ≈ 0.00043 EUR/kWh × 1000 = 0.43 EUR/MWh
    # Source YAML : CAPACITE_RTE_TARIF_2026_EUR_PER_MW (config/sources_reglementaires.yaml)
    ...
    "source": "Enchères capacité RTE 06/03/2025 — 3.15 EUR/MW × coeff 1.2 / 8760h ≈ 0.43 EUR/MWh",
    "yaml_ref": "CAPACITE_RTE_TARIF_2026_EUR_PER_MW",  # NEW : traçabilité TraceTooltip R10
}
```

#### 3. `services/purchase/cost_simulator_2026.py:60-64` — docstring enrichi

```python
# Tarif capacité RTE 2026 — calcul depuis enchère 06/03/2025 :
#   3.15 EUR/MW × coeff_obligation_2026 (1.2) / 8760 h ≈ 0.43 EUR/MWh
#
# YAML SoT : CAPACITE_RTE_TARIF_2026_EUR_PER_MW (config/sources_reglementaires.yaml)
# Refactor vers loader prévu Sprint C-7 (D-Sprint-C7-Capacite-Loader-Refactor-001 P2).
#
# DISAMBIGUATION : ne pas confondre avec PRIX_MOYEN_MW_AN PL1 (3 150 EUR/MW.an)
# dans revenue.py qui est un placeholder obsolète pré-enchères 2025.
CAPACITE_UNITAIRE_EUR_MWH = 0.43
```

#### 4. Tests (zéro nouveau test — clarif documentaire)

Aucun test ajouté. Modifications = pure documentation (commentaires + YAML notes). Source-guards existants `SG_REG_CONST_CAPACITE_*` Sprint C-4 Phase 4.2 inchangés.

### Livrables Phase 5.2 (estimation détaillée)

| Composant | Effort | Tests |
|---|---|---|
| YAML notes enrichi | ~10 min | 0 |
| catalog.py docstring + yaml_ref | ~10 min | 0 |
| cost_simulator_2026.py docstring | ~10 min | 0 |
| **Total** | **~30 min** | **0** |

### Dettes ouvertes Sprint C-7

- `D-Sprint-C7-Capacite-Loader-Refactor-001` P2 — refactor `cost_simulator_2026.py` + `catalog.py` vers `capacite_loader.py` pattern
- `D-Sprint-C7-Revenue-Capacite-Placeholder-Cleanup-001` P2 — audit usages `PRIX_MOYEN_MW_AN PL1 = 3150` + suppression si non-consumer

---

## Implémentation Phase 5.2 actée (2026-05-06)

### Découverte cardinale Étape 5.2.1 (diagnostic)

La note YAML Sprint C-4 Phase 4.2 (ligne 984) référençait par erreur **"3150 EUR/MW placeholder revenue.py PRIX_MOYEN_MW_AN PL1 20-50k EUR/MW"**. Diagnostic Phase 5.2 confirme :

- **AUCUN `3150` littéral** dans `services/capacity/revenue.py` (vérifié via grep)
- `PRIX_MOYEN_MW_AN` réel : `PL4 = (25_000, 35_000, 45_000)` et `PL1 = (20_000, 30_000, 50_000)` EUR/MW.an
- Source : KB `CAPACITE-ELIGIBILITE-ACTIFS` (~30 k€/MW/an observé 2025, fourchette 2026+ 20-50 k€)

→ Le "3150" était une **mention erronée** dans la note YAML. Pas de bug runtime, juste une erreur de documentation à corriger.

### Disambiguation correcte cardinale (3 dimensions)

| Dimension | Valeur | Sens |
|---|---|---|
| Prix CERTIFICAT capacité enchère 2026 | **3.15 EUR/MW** | YAML SoT — prix unitaire RTE 06/03/2025 |
| Tarif facture CLIENT B2B (composante TURPE) | **0.43 EUR/MWh** | Calculé `3.15 × 1.2 / 8760` (catalog.py + cost_simulator_2026.py) |
| Fourchette REVENU PRODUCTEUR certifié | **20-50 k€/MW.an** | KB `CAPACITE-ELIGIBILITE-ACTIFS`, revenue.py (PL1/PL4) |

Les 2 dimensions économiques (côté client tarif vs côté producteur revenu) sont **distinctes** — pas de rapport mathématique direct.

### Modifications effectives

1. **`config/sources_reglementaires.yaml`** lignes 971-984 :
   - Note YAML réécrite (multiline `notes:`) avec disambiguation 3 dimensions explicites
   - `formula:` ajoutée : `tarif_eur_per_mwh = 3.15 × CAPACITE_RTE_COEFF_2026 (1.2) / 8760 ≈ 0.43 EUR/MWh`
   - Mention erreur historique "3150" corrigée

2. **`services/capacity/revenue.py`** docstring module :
   - Section ⚠️ DISAMBIGUATION CARDINAL ajoutée
   - Clarification PRIX_MOYEN_MW_AN = revenu gross producteur (≠ 3.15 prix client)
   - Référence Sprint C-7 refactor loader YAML

3. **`services/purchase/cost_simulator_2026.py`** lignes 60-64 :
   - Commentaire enrichi avec référence YAML SoT explicite
   - Mention dette refactor Sprint C-7

4. **`services/billing_engine/catalog.py`** lignes 871-885 :
   - Bloc commentaire enrichi
   - `yaml_ref: "CAPACITE_RTE_TARIF_2026_EUR_PER_MW"` ajouté à la ligne `CAPACITE_ELEC` (traçabilité TraceTooltip R10)

### Effort réel Phase 5.2

~30 min (cible tenue). Pure documentation, 0 logique métier touchée. 0 nouveau test.

### Dettes Sprint C-7 reportées (P2)

- `D-Sprint-C7-Capacite-Loader-Refactor-001` P2 — refactor `cost_simulator_2026.py` + `catalog.py` vers `capacite_loader.py` pattern Sprint C-3
- `D-Sprint-C7-Capacite-Revenue-Refactor-Yaml-001` P2 — refactor `services/capacity/revenue.py` pour consommer `get_term_value` (loader YAML cohérent Sprint C-3)

---

## Références

- Tracking dette : `docs/audits/DETTE_TECHNIQUE_TRACKER.md` (`D-Phase4-2-Capacite-EUR-MW-Disambiguation-001`)
- Bilan Sprint C-4 : `docs/audits/BILAN_SPRINT_C4_2026_05_05.md` (Phase 4.2 + 4.2d audit multi-agents)
- Pattern YAML loader Sprint C-3 : `services/regulatory_sources_loader.py` + `config/sources_reglementaires.yaml`
- Source enchère RTE : <https://www.services-rte.com/> (lien à vérifier Sprint C-7 audit allow-list)
