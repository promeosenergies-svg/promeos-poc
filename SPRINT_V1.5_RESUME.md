# SPRINT V1.5 — q_gtb → BACS + q_operat → DT + Top 30 Audit

**Date** : 2026-03-14
**Scope** : Enrichissement questionnaire → conformite + correctifs audit global
**Tests** : 5 608/5 608 ALL PASSED (6 skipped CEE)
**Lint** : 0 erreurs

---

## 1. RESUME EXECUTIF

La V1.5 etend l'impact du questionnaire de segmentation sur la conformite :
- **q_gtb** influence desormais la carte BACS (GTB = infrastructure de base pour BACS)
- **q_operat** influence la carte Decret Tertiaire (statut de declaration OPERAT)

En parallele, un audit Playwright complet (27 pages + 8 interactions) a identifie 30 issues dont 6 corrigees dans cette session.

**Doctrine produit strictement respectee** :
- Ne JAMAIS masquer une obligation — seulement deprioriser, qualifier ou contextualiser
- Boost clamp [-3, +3] pour eviter les extremes avec cumul de regles
- Tri overdue > statut > boost (inchange depuis V1.4)
- Fiabilite "Declare" uniquement si l'obligation utilise une reponse utilisateur

---

## 2. TOP 30 ISSUES AUDIT

### Issues corrigees (6/30)

| # | Prio | Page | Issue | Fix |
|---|------|------|-------|-----|
| 1 | **P0** | energy-copilot | 404 "Page introuvable" | Redirect → cockpit |
| 2 | **P0** | kb | "KB locale chargee" warning alarmant | Stats fallback silencieux |
| 10 | **P1** | segmentation | q_cee visible malgre CEE masque partout | `hidden: True` + filtre `get_questions` |
| 21 | **P2** | usages-horaires | Badge confidence "high" en anglais | Traduit → "Elevee" / "Moyenne" / "Faible" |
| 28a | **P2** | status | Version "PROMEOS v1.0" obsolete | → "PROMEOS v1.4" |
| 28b | **P2** | monitoring | Version "Moteur Monitoring v1.0" | → "Moteur Monitoring v1.4" |

### Issues non-bugs (diagnostiquees)

| # | Page | Diagnostic |
|---|------|------------|
| 3 | consommations | Skeleton = timing screenshot (`.finally` fonctionne) |
| 11 | notifications | Badge "4" = filtrage critique/haute (attendu) |
| 25 | admin-users | "3 Sans connexion" = amber, pas rouge (correct) |

### Issues restantes (cosmetic/data, non bloquantes)

| # | Prio | Page | Issue |
|---|------|------|-------|
| 4 | P1 | cockpit | Score 54/100 vs 71% — metriques differentes |
| 5 | P1 | cockpit | "Tout va bien" + spinner — misleading |
| 6 | P1 | conformite | 23 constats mais 3 obligations visibles |
| 7 | P1 | conformite-tertiaire | OPERAT 0 anomalies / 0 declares |
| 8 | P1 | monitoring | "Non detecte" source anomalie |
| 9 | P1 | bill-intel | Export CSV/PDF manquant sur anomalies |
| 12 | P1 | billing-timeline | "85% factures importees" |
| 13 | P1 | patrimoine | Score/badge incoherent sur certains sites |
| 14 | P1 | portfolio-conso | "Connexion 98%" |
| 15 | P1 | activation | Usine Toulouse sans conformite |
| 16 | P2 | cockpit | "Univers" section sans affordance nav |
| 17 | P2 | actions | Format EUR variable dans Impact estime |
| 18 | P2 | conformite | Frise reglementaire difficile a lire |
| 19 | P2 | explorer | Chart flat, mauvais y-axis scaling |
| 20 | P2 | diagnostic | 6x duplicates "Talon eleve" Hotel Nice |
| 22 | P2 | achat-energie | "FUIRE" tag jargon sur scenarios |
| 23 | P2 | assistant-achat | Wizard 8 etapes sans indication |
| 24 | P2 | renouvellements | Contrat 89j sans CTA renouveler |
| 26 | P2 | onboarding | "Felicitations 100%" toujours visible |
| 27 | P2 | connectors | Auth requise sans moyen de s'auth en demo |
| 29 | P2 | patrimoine-detail | Drawer sparse "Non renseigne" |
| 30 | P2 | search-palette | Pas de resultats de recherche |

---

## 3. V1.5 — REGLES METIER

### R4 — BACS x q_gtb

| Reponse | Tag | Couleur | Boost | Fiabilite |
|---------|-----|---------|-------|-----------|
| oui_centralisee | GTB centralisee — BACS facilite | vert | +1 | Declare |
| oui_partielle | GTB partielle — BACS a verifier par site | bleu | 0 | Declare |
| non | Sans GTB — mise en conformite BACS a planifier | amber | +1 | Declare |
| ne_sait_pas | A qualifier | amber | 0 | A confirmer |

### R5 — DT x q_operat

| Reponse | Tag | Couleur | Boost | Fiabilite |
|---------|-----|---------|-------|-----------|
| oui_a_jour | Declaration OPERAT a jour | vert | 0 | Declare |
| oui_retard | Declaration OPERAT en retard | amber | +1 | Declare |
| non | OPERAT non declare | amber | +1 | Declare |
| non_concerne | Non concerne OPERAT selon votre profil | gris | -1 | Declare |

### Garde-fous

| Regle | Description |
|-------|-------------|
| Boost clamp | priorityBoost clamp a [-3, +3] apres cumul R1+R5 |
| Tri strict | overdue > statut metier > boost > code (JAMAIS override) |
| Fiabilite | "Declare" uniquement si usesUserAnswer pour CETTE obligation |
| Pertinence | Badge "Pertinent" uniquement pour relevance === 'high' |
| Pas de masquage | Aucun `.filter()` ni `.splice()` dans computeObligationProfileTags |

---

## 4. FICHIERS MODIFIES

### Commit 1 — Top 30 fixes (`1f811cb`)

| Fichier | Action |
|---------|--------|
| `frontend/src/App.jsx` | Route redirect `/energy-copilot` → `/` |
| `frontend/src/pages/KBExplorerPage.jsx` | Stats fallback silencieux |
| `frontend/src/pages/StatusPage.jsx` | Version → v1.4 |
| `frontend/src/pages/MonitoringPage.jsx` | Version → v1.4 |
| `frontend/src/pages/consumption/ProfileHeatmapTab.jsx` | Confidence badge FR |
| `backend/services/segmentation_service.py` | q_cee hidden + filtre get_questions |
| `backend/tests/test_segmentation.py` | q_cee retire des expected_ids |
| `SPRINT_V1.4_QUESTIONNAIRE_CONFORMITE.md` | Documentation V1.4 |

### Commit 2 — V1.5 (`ba235b6`)

| Fichier | Action |
|---------|--------|
| `frontend/src/models/complianceProfileRules.js` | BACS_GTB_RULES + DT_OPERAT_RULES + applyRule + clamp |
| `frontend/src/__tests__/v14_questionnaire_conformite.test.js` | 9 tests V1.5 ajoutes (29 total) |

---

## 5. TESTS

| Suite | Resultat |
|-------|----------|
| Frontend (vitest) | 5 608 passed, 6 skipped (CEE) |
| Backend (pytest segmentation) | 23/23 passed |
| Lint (eslint) | 0 erreurs |
| Lint (ruff) | 0 erreurs |

### Tests V1.5 ajoutes (9)

1. `BACS_GTB_RULES` exporte avec 4 reponses GTB
2. `DT_OPERAT_RULES` exporte avec 4 reponses OPERAT
3. Labels GTB prudents (GTB centralisee, Sans GTB, BACS)
4. Labels OPERAT prudents (OPERAT, jour, retard)
5. Lecture `answers.q_gtb` et `answers.q_operat`
6. `BACS_GTB_RULES` applique uniquement aux obligations BACS
7. `DT_OPERAT_RULES` applique uniquement aux obligations tertiaire
8. Boost clamp [-3, +3]
9. Pas de masquage (no `.filter()` ni `.splice()`)

---

## 6. CRITERES D'ACCEPTATION

| # | Critere | Statut |
|---|---------|--------|
| CA1 | q_gtb=oui_centralisee : tag vert "GTB centralisee — BACS facilite" sur BACS | **FAIT** |
| CA2 | q_gtb=non : tag amber "Sans GTB — BACS a planifier" sur BACS | **FAIT** |
| CA3 | q_operat=oui_retard : tag amber "OPERAT en retard" sur DT | **FAIT** |
| CA4 | q_operat=non_concerne : tag gris, boost -1, JAMAIS masque | **FAIT** |
| CA5 | Boost clamp [-3, +3] | **FAIT** |
| CA6 | Tri overdue > statut > boost inchange | **FAIT** |
| CA7 | Fiabilite "Declare" uniquement si usesUserAnswer | **FAIT** |
| CA8 | Sans profil : affichage identique V1.3 | **FAIT** |
| CA9 | /energy-copilot ne renvoie plus 404 | **FAIT** |
| CA10 | q_cee masque dans le questionnaire | **FAIT** |
| CA11 | Tous les tests passent | **FAIT** (5608/5608) |

---

## 7. PROCHAINES ETAPES

| # | Action | Priorite |
|---|--------|----------|
| 1 | Corriger les 24 issues restantes du Top 30 | P1-P2 |
| 2 | Export PDF dossier conformite avec tags profil | P2 |
| 3 | Connecter q_surface_seuil au filtrage backend (deprioriser, pas masquer) | P2 |
| 4 | Ajouter q_horaires → impact sur monitoring/usages | P2 |
| 5 | Ajouter q_chauffage → impact sur recommandations energie | P3 |
