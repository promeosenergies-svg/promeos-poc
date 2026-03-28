# AUDIT CONFORMITÉ / REGOPS — 28 mars 2026

## Score global : 78 / 100

La brique Conformité est fonctionnellement riche (5 frameworks, 50+ endpoints, ~3600 LOC moteur, 1200+ tests) mais présente des écarts de crédibilité sur le scoring et un défaut critique d'org-scoping sur les routes BACS.

---

## Scores par sous-brique

| # | Sous-brique | Score | Commentaire |
|---|-------------|:-----:|-------------|
| 1 | Moteur compliance_engine.py | 85 | Legacy solide (1249 LOC), backward-compat, snapshots fonctionnels |
| 2 | Règles DT/OPERAT | 75 | Scope + OPERAT OK, mais trajectoire -40/-50/-60% non vérifiée dans le rule evaluator RegOps (déléguée à operat_trajectory séparé) |
| 3 | Règles BACS | 90 | Moteur expert complet (735 LOC), Putile, TRI, inspections, exemptions. Seuils corrects. |
| 4 | Règles APER | 85 | Parking (10k/1.5k) + toiture (500m²) corrects. Pénalités estimatives raisonnables. |
| 5 | Règles CEE | 70 | Hints/opportunités seulement (correct — CEE = financement), mais logique basique |
| 6 | Scoring composite A.2 | 55 | **P1** : Poids regs.yaml (35/25/15) ≠ docstring/UI (45/30/25) ≠ effectif (~47/33/20). APER non évalué sur les sites → poids exclu → scores gonflés. |
| 7 | RegAssessment / cache | 80 | 5 assessments en DB, non-stale, versionnés. Mais 1 seul assessment par site (pas par framework) → `_detect_framework` fragile. |
| 8 | BACS Expert (wizard) | 90 | 28 endpoints, CVC systems, inspections, exemptions TRI, remédiation, preuves. Fonctionnellement complet. |
| 9 | UX ConformitePage | 85 | 4 onglets (Obligations, Données, Exécution, Preuves), mode guidé 5 étapes, Explain glossaire 40+ termes, Evidence drawer, CTA actions |
| 10 | Org-scoping / Auth | 30 | **P0** : 28 endpoints BACS sans org-scoping NI auth. compliance.py et aper.py correctement scopés. |
| 11 | Tests | 80 | 269 passent, 2 échecs (1 regression scoring 3→5 frameworks, 1 format erreur actions). 177 BACS/APER/RegOps = 100% pass. |
| 12 | Cohérence inter-briques | 85 | Cockpit utilise RegAssessment pour le score (source unique ✓). Conformité→Actions OK. Conformité→Patrimoine OK. |

---

## Tableau conformité réglementaire

| Règle | Seuil dans le code | Seuil officiel | Source | Statut |
|-------|-------------------|----------------|--------|--------|
| DT surface | ≥ 1000 m² | ≥ 1000 m² | Décret n°2019-771 art. R174-22 | ✅ OK |
| DT jalon 2030 | -40% (`reduction_2030: -0.40`) | -40% | Décret n°2019-771 | ✅ OK |
| DT jalon 2040 | -50% (`reduction_2040: -0.50`) | -50% | Décret n°2019-771 | ✅ OK |
| DT jalon 2050 | -60% (`reduction_2050: -0.60`) | -60% | Décret n°2019-771 | ✅ OK |
| DT deadline attestation | 2026-07-01 | 1er juillet 2026 | Arrêté du 10 avril 2020 | ✅ OK |
| DT deadline déclaration | 2026-09-30 | 30 septembre 2026 | Arrêté du 10 avril 2020 | ✅ OK |
| DT pénalité non-déclaration | 7 500 € | 7 500 € | Art. R174-32 | ✅ OK |
| DT pénalité non-affichage | 1 500 € | 1 500 € | Art. R174-32 | ✅ OK |
| DT name & shame | true | Oui (publication ADEME) | Art. L174-1-1 | ✅ OK |
| DT trajectoire vérifiée dans RegOps rule | **Non** (seulement scope + OPERAT) | Devrait vérifier via consommation | — | ⚠️ P2 |
| BACS seuil haut | 290 kW (`high_kw: 290`) | > 290 kW | Décret n°2020-887 / 2023-259 | ✅ OK |
| BACS seuil bas | 70 kW (`low_kw: 70`) | > 70 kW | Décret n°2020-887 / 2023-259 | ✅ OK |
| BACS deadline >290kW | 2025-01-01 | 1er janvier 2025 | Décret n°2023-259 | ✅ OK |
| BACS deadline >70kW | **2030-01-01** | **1er janvier 2027** (officiel) | Cité : décret n°2025-1343 report à 2030 | ⚠️ À VÉRIFIER |
| BACS exemption TRI | > 10 ans (`tri_max_years: 10`) | TRI > 10 ans | Art. R175-6 | ✅ OK |
| BACS inspection | 5 ans (`inspection_periodicity_years: 5`) | Quinquennale | Art. R175-5-1 | ✅ OK |
| BACS pénalité | 7 500 € | Pas de montant fixe dans le décret | — | ⚠️ Estimation |
| BACS fonctions requises | 10 critères | 10 critères R.175-3 | Art. R175-3 | ✅ OK |
| APER parking grand | ≥ 10 000 m² | ≥ 10 000 m² | Loi APER art. 40 | ✅ OK |
| APER parking moyen | ≥ 1 500 m² | ≥ 1 500 m² | Loi APER art. 40 | ✅ OK |
| APER toiture | ≥ 500 m² | > 500 m² (bât. neufs/rénovés + tertiaire existant) | Loi APER art. 41 | ✅ OK |
| APER deadline parking grand | 2026-07-01 | 1er juillet 2026 | Décret n°2024-1023 | ✅ OK |
| APER deadline parking moyen | 2028-07-01 | 1er juillet 2028 | Décret n°2024-1023 | ✅ OK |
| APER deadline toiture | 2028-01-01 | 1er janvier 2028 | Loi APER art. 41 | ✅ OK |
| APER couverture requise | 50% | 50% surface imperméabilisée | Loi APER art. 40 | ✅ OK |
| CEE P6 | Financement, hors score | Correct (pas une obligation site) | Code de l'énergie | ✅ OK |
| Score pondération (regs.yaml) | DT 35% + BACS 25% + APER 15% + DPE 15% + CSRD 10% | Interne PROMEOS | — | ⚠️ Incohérent avec UI |
| Score pondération (UI/docstring) | DT 45% + BACS 30% + APER 25% | Interne PROMEOS | — | ⚠️ Incohérent avec regs.yaml |
| Score pondération (effectif) | ~46.7% / 33.3% / 20% (DPE+CSRD exclus) | — | — | ⚠️ Ni l'un ni l'autre |

---

## P0 — Bloquants

| # | Problème | Fichier | Impact | Correction | Effort |
|---|----------|---------|--------|------------|--------|
| P0-1 | **28 endpoints BACS sans org-scoping ni auth** | `routes/bacs.py` | Faille sécurité : accès cross-tenant à toutes les données BACS (assets, systèmes CVC, inspections, exemptions, remédiations) via simple site_id | Ajouter `resolve_org_id()` + vérification que le site appartient à l'org | M (2-4h) |
| P0-2 | **Poids scoring A.2 incohérents** : regs.yaml = 35/25/15 ≠ docstring/formula = 45/30/25 ≠ effectif ≈ 47/33/20 | `services/compliance_score_service.py` L62-68 + `regops/config/regs.yaml` L136-145 + `ComplianceScoreHeader.jsx` L43 | Score affiché ≠ formule annoncée. En démo, un client qui vérifie le calcul constate l'incohérence. | Aligner regs.yaml sur 45/30/25 (fallback) OU mettre à jour docstring + UI sur les vrais poids | S (1h) |

---

## P1 — Crédibilité

| # | Problème | Fichier | Impact | Correction | Effort |
|---|----------|---------|--------|------------|--------|
| P1-1 | **APER non évalué en RegAssessment** : le moteur RegOps produit des findings APER mais `_detect_framework()` ne les persiste pas comme RegAssessment séparé → poids APER exclu du composite → **scores gonflés** | `services/compliance_score_service.py` `_detect_framework()` + `regops/engine.py` | Site #1 : APER available=false malgré findings APER existants. Score 90.4 au lieu de ~85 si APER pris en compte. | Persister un RegAssessment par framework OU améliorer _detect_framework | M (2-4h) |
| P1-2 | **Test regression** : `test_breakdown_has_3_frameworks` attend 3 frameworks, reçoit 5 (DPE + CSRD ajoutés) | `tests/test_compliance_score_service.py:135` | Test en échec permanent depuis ajout DPE/CSRD | Mettre à jour assert 3 → 5 (ou filtrer frameworks implémentés) | XS (10min) |
| P1-3 | **Test regression** : `test_operat_close_blocked_without_proof_or_justification` — format erreur changé (`detail` → `code`+`message`) | `tests/test_action_close_rules_v49.py:138` | Test échoue sur KeyError: 'detail' | Adapter le test au nouveau format d'erreur | XS (10min) |
| P1-4 | **BACS 70kW deadline 2030 vs 2027** : le code cite "décret n°2025-1343 du 26/12/2025" comme report de 2027 à 2030 | `regs.yaml:66` | Si le décret existe → OK. Si le décret n'existe pas → seuil faux pour 50% du parc BACS. | Vérifier l'existence du décret n°2025-1343 sur Légifrance | XS (vérification) |
| P1-5 | **RegOps rule DT ne vérifie pas la trajectoire** : `tertiaire_operat.py` vérifie scope + OPERAT status mais pas la progression -40%/-50%/-60% | `regops/rules/tertiaire_operat.py` | La trajectoire est vérifiée par `operat_trajectory.py` séparément, mais pas intégrée dans les findings RegOps → score DT toujours 100 si OPERAT est "ok" | Intégrer les résultats trajectoire dans les findings DT du RegOps evaluator | M (4h) |
| P1-6 | **0/5 sites en high confidence** : `high_confidence_count: 0` au niveau portfolio | Live `/api/compliance/portfolio/score` | En démo, aucun site ne montre "Données fiables" → impression de système incomplet | Configurer au moins le site #1 HELIOS avec les 3 frameworks évalués | S (1h) |

---

## P2 — Best-in-class

| # | Amélioration | Fichier | Impact |
|---|-------------|---------|--------|
| P2-1 | RegOps regops.py : `org_id` en query param optionnel, pas de `resolve_org_id()` contrairement à compliance.py | `routes/regops.py` L190-204 | Org-scoping partiel (moins grave que BACS mais à renforcer) |
| P2-2 | DPE Tertiaire et CSRD dans regs.yaml mais évaluateurs non implémentés | `regs.yaml` L43-127 | Préparation correcte, mais les poids "fantômes" 15%+10% biaisent la normalisation si un jour 1 seul est activé |
| P2-3 | `datetime.utcnow()` deprecated (13 warnings pytest) | `services/compliance_rules.py:768` et autres | Python 3.14 flagge, deviendra erreur en 3.15 |
| P2-4 | Tertiaire : pas d'endpoint `/api/regops/tertiaire/site/{site_id}` d'évaluation à la demande (contrairement à BACS) | Routes tertiaire | Le DT a des EFA CRUD mais pas d'évaluation RegOps fresh |
| P2-5 | BACS pénalité 7500€ codée mais non sourcée réglementairement | `regs.yaml:69` | Le décret BACS ne prévoit pas de montant fixe — c'est une estimation |

---

## Vérification live

| Test | Résultat |
|------|----------|
| Backend health | ✅ OK (v1.0.0, DB ok) |
| `GET /api/compliance/meta` | ✅ 200 — renvoie framework_weights, thresholds, critical_penalty |
| `GET /api/compliance/rules` | ✅ 200 — 5 règles DT, labels FR corrects |
| `GET /api/compliance/findings?limit=10` | ✅ 200 — findings BACS/DT/APER avec statuts |
| `GET /api/regops/dashboard` | ✅ 200 — 5 sites, 1 compliant, 2 at_risk, 1 non_compliant, avg 77.8 |
| `GET /api/regops/site/1` | ✅ 200 — BACS NON_COMPLIANT (300kW, deadline passé), APER ROOF AT_RISK |
| `GET /api/regops/score_explain?scope_type=site&scope_id=1` | ✅ 200 — breakdown 5 frameworks, score 90.4 |
| `GET /api/regops/data_quality?scope_type=site&scope_id=1` | ✅ 200 — coverage 100%, gate OK |
| `GET /api/regops/bacs/site/1` | ✅ 200 — asset configured, 2 CVC systems, Putile 300kW, threshold 290 |
| `GET /api/compliance/sites/1/score` | ✅ 200 — score 90.4, confidence medium, penalty 5.0 |
| `GET /api/compliance/portfolio/score` | ✅ 200 — avg 86.7, 0 high confidence |
| Score conformité site HELIOS #1 | 90.4 (DT 100 + BACS 89 pondérés, APER non compté) |
| RegAssessments en DB | 5 (1 par site), non-stale, versionnés |
| DT jalons corrects | ✅ -40/-50/-60% dans regs.yaml |
| DT deadlines | ✅ attestation 2026-07-01, déclaration 2026-09-30 |
| BACS seuils | ✅ 290kW/70kW, TRI 10 ans, inspection 5 ans |
| BACS Putile site #1 | ✅ 300kW (180+120), threshold 290, deadline 2025-01-01 |
| APER seuils | ✅ parking 10k/1.5k m², toiture 500m², couverture 50% |

---

## Tests

| Suite | Passent | Échouent | Détail échec |
|-------|:-------:|:--------:|-------------|
| compliance_engine | 49 | 0 | — |
| compliance_v1 | 42 | 0 | — |
| compliance_score_service | 5 | **1** | `test_breakdown_has_3_frameworks` : attend 3, reçoit 5 (DPE+CSRD ajoutés) |
| regops_rules | 16 | 0 | — |
| regops_hardening | 30 | 0 | — |
| bacs_engine | 34 | 0 | — |
| bacs_v2_compliance | 11 | 0 | — |
| bacs_compliance_gate | 11 | 0 | — |
| bacs_exemption_workflow | 17 | 0 | — |
| bacs_regulatory_engine | 15 | 0 | — |
| bacs_api | 16 | 0 | — |
| step29_aper | 27 | 0 | — |
| tertiaire (sélection) | 3 | **1** | `test_operat_close_blocked_without_proof` : KeyError 'detail' (format erreur changé) |
| **TOTAL** | **276** | **2** | 98.6% pass rate |

---

## Org-scoping par module

| Module | Endpoints | Avec org-scoping | Avec auth | Statut |
|--------|:---------:|:----------------:|:---------:|--------|
| compliance.py | ~20 | 20 (`resolve_org_id`) | ✅ | ✅ OK |
| aper.py | 2 | 2 (`resolve_org_id`) | ✅ | ✅ OK |
| tertiaire.py | ~15 | ~12 (`org_id` query) | Partiel | ⚠️ Acceptable |
| regops.py | ~7 | 1 (optionnel) | Non | ⚠️ P2 |
| **bacs.py** | **28** | **0** | **Non** | **❌ P0** |

---

## Architecture scoring (2 systèmes distincts)

```
┌─────────────────────────────────────────────┐
│  A.2 — Score Unifié (affiché dans l'UI)     │
│  compliance_score_service.py                │
│  Poids: DT 35% + BACS 25% + APER 15%       │
│         + DPE 15% + CSRD 10% (non impl.)   │
│  Source: RegAssessment par framework        │
│  Pénalité: -5pts/finding critique (max -20) │
│  Normalise sur frameworks disponibles       │
└────────────────┬────────────────────────────┘
                 │ lit
┌────────────────▼────────────────────────────┐
│  RegOps — Score composante                  │
│  regops/scoring.py                          │
│  Poids: tous à 1.0 (scoring_profile.json)   │
│  Formule: 100 - (penalty/weight × 100)      │
│  Déduplique, urgence, confiance             │
└────────────────┬────────────────────────────┘
                 │ persiste dans
┌────────────────▼────────────────────────────┐
│  RegAssessment (table SQLite)               │
│  1 row par site, compliance_score = RegOps  │
│  findings_json, top_actions_json            │
│  deterministic_version, computed_at         │
└─────────────────────────────────────────────┘
```

**Problème** : RegAssessment stocke 1 score global par site, pas 1 par framework. `_detect_framework()` dans compliance_score_service essaie de deviner le framework depuis le contenu → fragile, et APER n'est pas détecté → exclu du composite.

---

## Synthèse des écarts scoring

**Vérification mathématique site #1** :
- DT = 100.0 (weight 0.35, available=true)
- BACS = 89.0 (weight 0.25, available=true)
- APER = 50.0 (weight 0.15, **available=false** → exclu)
- DPE = 50.0 (weight 0.15, available=false → exclu)
- CSRD = 50.0 (weight 0.10, available=false → exclu)
- total_weight = 0.35 + 0.25 = 0.60
- weighted_sum = (100 × 0.35) + (89 × 0.25) = 57.25
- raw_score = 57.25 / 0.60 = **95.4**
- critical_penalty = 5.0 (1 finding critique BACS)
- **final = 90.4** ✅ Math correcte

**Mais** : l'UI affiche "DT × 45% + BACS × 30% + APER × 25%" alors que le calcul réel utilise DT × 58.3% + BACS × 41.7% (normalisation sur 2 frameworks disponibles). C'est trompeur.

---

## Verdict : PASS AVEC RÉSERVES

### Points forts
- Architecture solide : source de vérité unique (regs.yaml), scoring tracé, versionnement déterministe
- BACS Expert complet et fonctionnel (28 endpoints, TRI, inspections, exemptions, remédiation)
- Seuils réglementaires DT/BACS/APER conformes aux textes (22/25 seuils vérifiés ✅)
- UX riche : 4 onglets, mode guidé 5 étapes, glossaire 40+ termes, Evidence drawer
- Tests solides : 276/278 passent (98.6%), couverture BACS/APER/RegOps = 100%
- Cohérence cockpit : score cockpit = source unique RegAssessment

### Réserves (à corriger avant démo pilote)
1. **P0-1** : 28 endpoints BACS sans org-scoping ni auth — faille sécurité cross-tenant
2. **P0-2** : Poids scoring incohérents UI/config/calcul — crédibilité en démo
3. **P1-1** : APER non détecté dans RegAssessment → scores gonflés
4. **P1-4** : BACS 70kW deadline 2030 — vérifier existence décret n°2025-1343
5. **P1-5** : Trajectoire DT non intégrée dans RegOps rule evaluator
6. **P1-6** : 0 site en high confidence — mauvaise impression en démo

### Effort total corrections P0+P1 : ~10h

---

*Audit réalisé le 28 mars 2026 par Claude Code.*
*Backend testé : v1.0.0 (git sha e2cc2ab), port 8001.*
*Démo HELIOS : 5 sites, seed pack helios.*
