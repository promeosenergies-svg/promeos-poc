# RAPPORT AUDIT — Conformite / RegOps
**Date** : 2026-03-29
**Branche** : `audit/conformite-regops`
**Score global** : 82/100

---

## 1. Executive Summary

L'audit end-to-end de la brique Conformite/RegOps de PROMEOS revele un module **globalement solide** :
- **424/424 tests backend passes** (0 fail, 0 skip)
- **3610/3610 tests frontend passes** (2 skipped non-conformite)
- **Score A.2 unifie operationnel** : source unique depuis `compliance_score_service.py`, poids DT(45%)+BACS(30%)+APER(25%) lus depuis `regs.yaml`
- **Cockpit ↔ Portfolio coherents** : 82.2 = 82.2 (spread 0)

Cependant, **1 P0**, **4 P1** et **5 P2** sont identifies.

---

## 2. Architecture

| Question | Reponse | Verdict |
|----------|---------|---------|
| Nombre de systemes de scoring | 2 actifs (A.2 source unique + RegOps scoring pour detail) + 1 legacy | OK |
| Score unifie A.2 en place ? | OUI — `compliance_score_service.py` (483 lignes) | OK |
| Poids lus depuis regs.yaml ? | OUI — ligne 44, fallback hardcode | OK |
| CompliancePage legacy supprimee ? | NON — fichier present, mais redirect `/compliance` → `/conformite` actif | P2 |
| Echelle coherente (higher=better) ? | OUI — docstring L4, dataclass L82, L92 | OK |
| Constantes risque alignees ? | OUI — `BASE_PENALTY_EURO=7500`, `A_RISQUE_PENALTY_EURO=3750` | OK |
| `regops/engine.py` utilise A.2 ? | OUI — L115: `compute_site_compliance_score(db, site_id)` | OK |
| `compute_regops_score` encore appele ? | Uniquement pour `score_explain` detail (L35 comment) | OK |

### Chaine d'appels
```
ConformitePage.jsx
  → /api/compliance/bundle (compliance_rules.py)
  → /api/compliance/sites/{id}/score (compliance_score_service.py A.2)

Cockpit.jsx
  → /api/cockpit (kpi_service → compliance_score_service)

regops/engine.py
  → evaluate_site() → 4 rules (DT, BACS, APER, CEE)
  → compute_site_compliance_score() → A.2 result
  → persist_assessment() → RegAssessment cache

compliance_coordinator.py
  → orchestrate full recompute (3 etapes)
```

---

## 3. Coherence score

### 3.1 Cross-briques

| Source | Score | Verdict |
|--------|-------|---------|
| Cockpit (`/api/cockpit`) | 82.2 | OK |
| Portfolio A.2 (`/api/compliance/portfolio/score`) | 82.2 | OK |
| **Spread** | **0.0 pts** | **OK** |

### 3.2 Par site (apres evaluation fraiche)

| Site | A.2 /score | RegOps fresh | RegOps cached | score_explain | Spread | Verdict |
|------|-----------|-------------|---------------|---------------|--------|---------|
| 1 - Siege HELIOS Paris | 68.0 | 68.0 | **60.0** | 68.0 | **8.0** | **WARN** |
| 2 - Bureau Lyon | 50.0 | 50.0 | 50.0 | 50.0 | 0.0 | OK |
| 3 - Hotel HELIOS Toulouse | 100.0 | 100.0 | 100.0 | 100.0 | 0.0 | OK |
| 4 - Hotel Mercure Nice | 100.0 | 100.0 | 100.0 | 100.0 | 0.0 | OK |
| 5 - Ecole Jules Ferry Marseille | 50.0 | 50.0 | 50.0 | 50.0 | 0.0 | OK |

**Note** : Le cache du site 1 (60.0 vs 68.0 fresh) est stale (`is_stale=False` malgre la divergence). La divergence s'explique par l'evaluation fraiche qui a mis a jour le RegAssessment sans synchroniser le cache. Voir P1-02.

### 3.3 Breakdown site 1 (score_explain)

| Framework | Score | Poids | Source |
|-----------|-------|-------|--------|
| Tertiaire OPERAT | 100.0 | 0.45 | snapshot |
| BACS | 60.0 | 0.30 | regops |
| APER | 60.0 | 0.25 | regops |
| **Penalite critique** | **-10.0** | | 2 findings critiques |
| **Score composite** | **68.0** | | `100*0.45 + 60*0.30 + 60*0.25 - 10 = 68.0` |

---

## 4. Donnees demo

### 4.1 Findings

| Dimension | Valeur |
|-----------|--------|
| Total findings | 15 |
| Par regulation | BACS: 5, DT: 5, APER: 5 |
| Par severite | critical: 1, high: 2, medium: 5, low: 7 |
| Par statut | OK: 4, UNKNOWN: 7, NOK: 1, OUT_OF_SCOPE: 3 |

### 4.2 Seed data

| Categorie | Quantite |
|-----------|----------|
| Organisations | 1 (Groupe HELIOS) |
| Sites | 5 |
| Compliance findings | 15 |
| Obligations | 8 |
| Evidences | 5 |
| BACS assets | 5 |
| BACS systems CVC | 9 |
| BACS assessments | 5 |
| BACS inspections | 3 |
| Tertiaire EFAs | 7 |
| Score history entries | 30 (6 mois) |

### 4.3 Risque financier

| Metrique | Valeur |
|----------|--------|
| Cockpit risque_financier_euro | 22 500 EUR |
| Calcul attendu (3 NON_CONFORME × 7500) | 22 500 EUR |
| Coherent ? | OUI |

---

## 5. Tests

| Suite | Total | Passed | Failed | Skip | Temps |
|-------|-------|--------|--------|------|-------|
| Backend Conformite (10 fichiers) | 209 | 209 | 0 | 0 | 161s |
| Backend BACS (11 fichiers) | 143 | 143 | 0 | 0 | 52s |
| Backend RegOps/Scoring (3 fichiers) | 60 | 60 | 0 | 0 | 22s |
| Backend Tertiaire (1 fichier) | 12 | 12 | 0 | 0 | 17s |
| **Backend total** | **424** | **424** | **0** | **0** | **252s** |
| Frontend (144 fichiers) | 3610 | 3610 | 0 | 2 | 88s |
| **E2E e4-patrimoine-conformite** | **24** | **18** | **6** | **0** | **228s** |

**E2E 6 fails** : tous causes par `"NaN"` detecte dans le body HTML de la page Patrimoine. Les tests Conformite (score, tabs, tertiaire, pipeline) passent. Voir P0-01.

---

## 6. UX/UI (screenshots Playwright)

35 captures analysees dans `artifacts/audits/captures/deep-v11/`.

| Page | Score | Points cles |
|------|-------|-------------|
| ConformitePage (entree) | 9/10 | Score 82/100 affiche, banner constats, 4 onglets, frise reglementaire, sidebar correcte |
| ConformitePage (obligations) | 8/10 | Obligations listees, detail expandable, mode expert disponible |
| ConformitePage (preuves) | 8/10 | Preuves par obligation, timeline, statuts colores |
| ConformitePage (execution) | 7/10 | Plan d'actions visible, mais navigation semble rediriger vers ActionsPage dans certains cas |
| ConformitePage (donnees) | 7/10 | Screenshot montre la page Actions au lieu de l'onglet Donnees (confusion possible) |
| Tertiaire/OPERAT | 9/10 | 7 EFAs assignees, 6 sites a traiter, statuts clairs, filtre assujetti/non concerne |
| Dossier print (drawer) | 8/10 | Drawer BACS visible, score 82/100, urgences prioritaires, actions listees |
| Legacy /compliance redirect | 10/10 | Redirige correctement vers /conformite |
| Cockpit (widget conformite) | 8/10 | Score 82.2 affiche, source RegAssessment confirmee |

---

## 7. Findings

### P0 — Bloquants

#### P0-01 : "NaN" affiche sur la page Patrimoine
- **Evidence** : E2E `e4-patrimoine-conformite.spec.js` — `assertCleanBody()` detecte "NaN" dans le HTML
- **Impact** : 6/24 tests E2E en echec (3 viewports × 2 tests). Probleme de calcul ou d'affichage d'un champ numerique retournant NaN. Visible par l'utilisateur final.
- **Reproduction** : Naviguer vers `/patrimoine` apres seed helios S
- **Fix recommande** : Identifier le champ NaN dans PatrimoinePage.jsx (probablement un ratio ou pourcentage calcule avec `0/0` ou un champ manquant dans le seed). Ajouter un guard `isNaN(x) ? '—' : x`.

---

### P1 — Credibilite

#### P1-01 : RegOps dashboard retourne `total_sites: 0`
- **Evidence** : `GET /api/regops/dashboard` → `{"total_sites": 0, "sites_compliant": 0, "avg_compliance_score": 0.0}`
- **Impact** : Le dashboard RegOps org-level est vide malgre 5 sites avec RegAssessments. Le cockpit utilise un autre chemin (kpi_service) et fonctionne, mais le dashboard RegOps dedie est inexploitable.
- **Fix recommande** : Verifier le filtre `org_id` dans la query RegAssessment du dashboard. Le seed cree probablement des RegAssessments sans `org_id` correctement propage.

#### P1-02 : Cache RegAssessment stale non detecte (site 1 : 60 vs 68)
- **Evidence** : `GET /api/regops/site/1/cached` → `compliance_score=60.0, is_stale=False` vs fresh → `68.0`
- **Impact** : Le cache dit "pas stale" alors que le score a diverge de 8 points. Un client qui consulte le cache obtient une information erronee.
- **Fix recommande** : Le flag `is_stale` doit etre remis a True apres chaque evaluation fraiche qui produit un score different. Ou synchroniser le cache dans `evaluate_site()`.

#### P1-03 : Score A.2 instable selon le chemin d'acces
- **Evidence** : Premiere requete `GET /api/compliance/sites/1/score` → 74.8 (bacs=72.4, aper=72.4). Apres `GET /api/regops/site/1` (fresh eval) → score passe a 68.0 (bacs=60, aper=60).
- **Impact** : Le score depend de l'ordre d'appel des endpoints. La source "snapshot" (fallback legacy) donne un score different de "regops" (RegAssessment). En production, le score affiche peut varier selon que l'utilisateur a visite /regops avant ou pas.
- **Fix recommande** : Forcer un `recompute` lors du seed demo pour que tous les RegAssessments soient initialises. Ou bien s'assurer que le fallback snapshot donne le meme resultat que le RegAssessment.

#### P1-04 : `avancement_decret_pct` = 0.0 dans le cockpit
- **Evidence** : `GET /api/cockpit` → `avancement_decret_pct = 0.0`
- **Impact** : Le KPI d'avancement Decret Tertiaire affiche 0% malgre des obligations DT seedees avec avancement 20-80%. Indicateur non credible en demo.
- **Fix recommande** : Verifier que `kpi_service` calcule correctement la moyenne d'avancement des obligations DT. Le champ `avancement_pct` existe dans le seed (gen_compliance.py).

---

### P2 — Polish

#### P2-01 : CompliancePage.jsx legacy non supprimee
- **Evidence** : `frontend/src/pages/CompliancePage.jsx` existe (337 lignes), marque "DEPRECATED V92+"
- **Impact** : Code mort. Le redirect fonctionne, mais le fichier alourdit le bundle.
- **Fix recommande** : Supprimer `CompliancePage.jsx` et la reference dans App.jsx. Remplacer par un redirect pur.

#### P2-02 : `score_explain` INTERNAL_ERROR avant premiere eval fraiche
- **Evidence** : Premier appel `GET /api/regops/score_explain?scope_type=site&scope_id=1` → `INTERNAL_ERROR`. Fonctionne apres `GET /api/regops/site/1` (fresh eval).
- **Impact** : Si l'utilisateur accede au score_explain avant qu'un recompute ait eu lieu, il obtient une erreur 500.
- **Fix recommande** : Ajouter un try/catch avec fallback "donnees insuffisantes" ou declencher un recompute lazy dans l'endpoint.

#### P2-03 : SAWarning identity map dans compliance_rules.py
- **Evidence** : 254 warnings SQLAlchemy lors des tests conformite : `Identity map already had an identity for ComplianceFinding`
- **Impact** : Pas de regression fonctionnelle, mais bruit dans les logs. Risque de masquer de vrais warnings.
- **Fix recommande** : Utiliser `db.merge()` au lieu de `db.add()` dans `compliance_rules.py:412` ou vider l'identity map entre evaluations.

#### P2-04 : `datetime.utcnow()` deprecated (9 warnings BACS, 6 warnings RegOps)
- **Evidence** : `compliance_rules.py:768`, `schema.py` — `DeprecationWarning: datetime.datetime.utcnow() is deprecated`
- **Impact** : Warning Python 3.14+. Sera supprime dans une future version.
- **Fix recommande** : Remplacer par `datetime.now(datetime.UTC)`.

#### P2-05 : Duplicate Operation ID dans OpenAPI (`kb_ping`)
- **Evidence** : Warning Swagger lors du mount des routes : `Duplicate Operation ID kb_ping_api_kb_ping_get`
- **Impact** : Mineur — l'OpenAPI spec a un doublon.
- **Fix recommande** : Renommer une des routes kb_ping ou utiliser `operation_id=` explicite.

---

## 8. API Endpoints — Statut

| # | Endpoint | Statut | Remarque |
|---|----------|--------|----------|
| 1 | `GET /api/compliance/meta` | OK | Poids corrects, scoring_version=A.2 |
| 2 | `GET /api/compliance/bundle` | OK | 5 sites, 15 findings |
| 3 | `GET /api/compliance/findings` | OK | 15 findings, severites distribuees |
| 4 | `GET /api/compliance/sites/{id}/score` | OK | Score + breakdown + confidence |
| 5 | `GET /api/compliance/portfolio/score` | OK | avg_score=82.2, worst_sites listees |
| 6 | `GET /api/regops/site/{id}` | OK | Evaluation fraiche, 3 findings |
| 7 | `GET /api/regops/site/{id}/cached` | **WARN** | Score stale (60 vs 68) |
| 8 | `GET /api/regops/score_explain` | **WARN** | INTERNAL_ERROR avant 1er recompute |
| 9 | `GET /api/regops/data_quality` | OK | coverage=100%, gate=OK |
| 10 | `GET /api/regops/dashboard` | **FAIL** | total_sites=0, avg_score=0 |
| 11 | `GET /api/cockpit` | OK | compliance_score=82.2, source=RegAssessment |
| 12 | `GET /api/compliance/score-trend` | OK | 6 mois d'historique |
| 13 | `GET /api/compliance/timeline` | OK | 7 echeances reglementaires |
| 14 | `GET /api/regops/bacs/site/{id}` | OK | Asset, systemes, assessment |
| 15 | `GET /api/compliance/sites/{id}/summary` | OK | 2 obligations, 3 findings, 1 evidence |

---

## 9. Screenshots Index

| Zone | Fichier | Observation |
|------|---------|-------------|
| Z1 | Z1-conformite-entree.png | Page d'entree OK, score 82/100, banner constats |
| Z1b | Z1b-conformite-top.png | Header score + frise timeline |
| Z2a | Z2a-obligations-tab.png | Onglet obligations avec filtres |
| Z2b-c | Z2b/Z2c-obligation-*.png | Detail obligation expandee |
| Z3a-f | Z3a-Z3f-expert-*.png | Mode expert complet (6 captures) |
| Z4a-b | Z4a-Z4b-preuves-*.png | Preuves & rapports |
| Z5a-b | Z5a-Z5b-execution-*.png | Plan d'execution |
| Z6 | Z6-donnees-tab.png | Donnees & qualite (affiche Actions&Suivi) |
| Z7 | Z7-public-mode-obligations.png | Mode public obligations |
| Z8a-b | Z8a-sidebar, Z8b-legacy-check.png | Sidebar patrimoine + legacy redirect OK |
| Z9 | Z9-dossier-print.png | Drawer dossier BACS |
| Z10 | Z10-conformite-tertiaire.png | Tertiaire/OPERAT dashboard |
| OBL-* | OBL-01 a OBL-04 | Obligations par regulation (BACS, DT, APER) |
| EXPAND-* | EXPAND-01 a 03 | Toutes obligations expandees |

---

## 10. Plan de correction

### Priorite 1 (avant demo)
| ID | Titre | Effort |
|----|-------|--------|
| P0-01 | Fix NaN sur PatrimoinePage | 30 min |
| P1-03 | Forcer recompute dans seed demo | 15 min |
| P1-01 | Fix RegOps dashboard query (org_id filter) | 30 min |

### Priorite 2 (sprint suivant)
| ID | Titre | Effort |
|----|-------|--------|
| P1-02 | Synchroniser cache RegAssessment apres fresh eval | 1h |
| P1-04 | Fix avancement_decret_pct dans kpi_service | 30 min |
| P2-02 | Fallback graceful pour score_explain sans recompute | 30 min |

### Priorite 3 (nettoyage)
| ID | Titre | Effort |
|----|-------|--------|
| P2-01 | Supprimer CompliancePage.jsx legacy | 15 min |
| P2-03 | Fix SAWarning identity map | 30 min |
| P2-04 | Migrer datetime.utcnow() | 15 min |
| P2-05 | Fix OpenAPI duplicate operation ID | 5 min |
