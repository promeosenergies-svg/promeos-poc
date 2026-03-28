# FIX PROMEOS — Sprint XS P0 — 24 mars 2026

## 1. Résumé exécutif

4 corrections XS appliquées en un sprint ciblé. Impact estimé : **+0.8 points** (7.5 → 8.3).

| # | Correction | Effort | Impact |
|---|---|---|---|
| 1 | Câblage `update_site_avancement()` dans `recompute_site_full()` | 1 bloc | +0.4 |
| 2 | Deadline BACS 70kW : 2027 → 2030 (décret n°2025-1343) | 1 ligne | +0.2 |
| 3 | DPE/CSRD marqués `implemented: false` dans regs.yaml | 2 commentaires | +0.1 |
| 4 | CVC estimation déterministe (médiane au lieu de random) | 1 ligne | +0.1 |

---

## 2. Modifications réalisées

### Fix 1 — KPI DT dynamique

**Avant** : `update_site_avancement()` existait dans `dt_trajectory_service.py:181` mais avait **0 appelant**. Le KPI `avancement_decret_pct` restait au champ plat seedé.

**Après** : `recompute_site_full()` appelle `update_site_avancement()` en étape 1b, entre le snapshot legacy (étape 1) et le RegAssessment (étape 2).

**Logique** :
- Si la trajectoire est calculable (conso référence + conso actuelle disponibles) → persiste `avancement_2030` sur `Site.avancement_decret_pct`
- Si incalculable → log debug, pas de crash (le champ garde sa valeur snapshot)
- Si erreur → log warning, skip (comme étapes 2 et 3)

**Fichier** : `backend/services/compliance_coordinator.py:40-57`

### Fix 2 — Deadline BACS 70kW

**Avant** : `regs.yaml:66` → `above_70: "2027-01-01"` avec commentaire inversé "avancé de 2030 à 2027"

**Après** : `above_70: "2030-01-01"` avec commentaire exact "décret n°2025-1343 du 26/12/2025 reporte de 2027 à 2030 (alignement EPBD)"

**Sources vérifiées** :
| Source | Date | Valeur |
|---|---|---|
| [Légifrance — Décret n°2025-1343](https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000053175245) | 26/12/2025 | Remplace "2027" par "2030" dans art. R175-2 |
| [Légifrance — Art. R175-2 consolidé](https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000053216492) | En vigueur | Confirme 2030 |
| **Retenue** | | **2030-01-01** — Confirmé primaire ×2 |

**Cohérence vérifiée** :
- `compliance_engine.py:53` → déjà à 2030 ✅
- `regulations/bacs/v2.yaml:12` → déjà à 2030 ✅
- `regs.yaml:66` → corrigé ✅

### Fix 3 — DPE/CSRD explicitement non implémentés

**Avant** : `regs.yaml:140-145` déclare 5 frameworks avec poids mais sans indication que DPE et CSRD n'ont pas d'évaluateur.

**Après** : Commentaires `# implemented: false` ajoutés sur les lignes DPE et CSRD. Le code `compliance_score_service.py` les exclut déjà du dénominateur (le score est correct par construction), mais le YAML est maintenant explicite.

### Fix 4 — CVC estimation déterministe

**Avant** : `onboarding_service.py:59` → `random.uniform(lo, hi)`. Même site créé 2 fois = puissance CVC différente = obligation BACS potentiellement différente.

**Après** : `(lo + hi) / 2` (médiane du range). Même site créé 2 fois = même puissance CVC = même obligation BACS.

**Valeurs par type de site** (médiane W/m²) :

| Type | lo | hi | Médiane W/m² | Exemple 2000m² |
|---|---|---|---|---|
| Bureau | 40 | 70 | 55 | 110 kW |
| Hôtel | 60 | 100 | 80 | 160 kW |
| Commerce | 70 | 110 | 90 | 180 kW |
| Entrepôt | 20 | 40 | 30 | 60 kW |
| Usine | 30 | 60 | 45 | 90 kW |

---

## 3. Fichiers touchés

| Fichier | Modification |
|---|---|
| `backend/services/compliance_coordinator.py` | Ajout étape 1b (appel `update_site_avancement`) |
| `backend/regops/config/regs.yaml` | Deadline BACS 70kW 2027→2030 + commentaires DPE/CSRD |
| `backend/services/onboarding_service.py` | `random.uniform` → médiane, `import random` supprimé |

---

## 4. Tests

| Suite | Résultat |
|---|---|
| `test_compliance_v68.py` | 41/41 ✅ |
| `test_emissions.py` | ✅ |
| `test_billing.py` | 40/40 ✅ |
| Import `compliance_coordinator` | OK ✅ |
| CVC déterminisme (assertion p1 == p2) | OK ✅ |
| regs.yaml parse (BACS = 2030) | OK ✅ |

---

## 5. Risques de régression

| Risque | Probabilité | Mitigation |
|---|---|---|
| `update_site_avancement()` échoue sur un site sans conso de référence | Faible | Try/except avec log warning, skip gracieux |
| CVC médiane change les obligations BACS pour les sites existants seedés | Faible | Ne s'applique qu'aux NOUVEAUX sites créés via onboarding |
| Tests pré-existants qui vérifient des valeurs CVC aléatoires | Faible | Aucun test trouvé vérifiant une valeur CVC spécifique |

---

## 6. Points non traités

| Point | Raison |
|---|---|
| P0-2 : Conformité ↔ Facture (bandeau + CTA) | Effort S, hors sprint XS |
| P1-1 : Scénarios achat dynamiques | Effort L |
| P1-6 : `risque_breakdown.billing_anomalies_eur` hardcodé 0 | Effort S |
| `alert_engine.py` HORS_HORAIRES seuil fixe 7h-19h | Périmètre Yannick |

---

## 7. Definition of Done

- [x] `update_site_avancement()` appelé dans `recompute_site_full()`
- [x] `regs.yaml:66` corrigé à 2030 (source : décret n°2025-1343)
- [x] DPE/CSRD marqués non implémentés
- [x] CVC estimation déterministe
- [x] `import random` supprimé
- [x] 81+ tests passent
- [x] Aucun fichier Yannick touché
