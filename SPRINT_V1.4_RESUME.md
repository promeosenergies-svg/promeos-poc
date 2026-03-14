# SPRINT V1.4 — Questionnaire x Conformite : effet produit reel

**Date** : 2026-03-14
**Scope** : Reponses questionnaire impactent l'affichage conformite
**Tests** : 5 599/5 599 ALL PASSED (6 skipped CEE)
**Lint** : 0 erreurs

---

## 1. RESUME EXECUTIF

La V1.4 rend le questionnaire **utile** : les reponses (q_surface_seuil, typologie) modifient reellement la priorisation et le balisage des obligations sur la page Conformite. Logique prudente, sobre, credible, 100% frontend.

**Garde-fous respectes** :
- Le boost profil ne casse JAMAIS le tri metier (overdue > statut > boost)
- "Declare" uniquement si l'obligation depend d'une reponse utilisateur
- Pertinence affichee uniquement en cas de correspondance forte (high)
- Jamais trop affirmatif juridiquement
- Fallback propre si pas de profil = affichage V1.3 identique

---

## 2. FAITS

| # | Fait |
|---|------|
| F1 | `segProfile` deja fetche dans ConformitePage (L749, L816-819) |
| F2 | 3 obligations affichees : DT, BACS, APER |
| F3 | `sortedObligations` triait par overdue puis statut, sans profil |
| F4 | q_surface_seuil a 4 reponses possibles |
| F5 | Audit Playwright confirme : score 54/100, tags visibles, tri correct |

---

## 3. HYPOTHESES

| # | Hypothese |
|---|-----------|
| H1 | Le boost profil est un tie-breaker dans le meme groupe, jamais un override |
| H2 | "Declare" = l'obligation utilise une reponse utilisateur pertinente |
| H3 | Pertinence forte (high) = badge visible ; medium/check_context = rien |

---

## 4. DECISIONS

| # | Decision |
|---|----------|
| D1 | Tri : overdue > statut > boost profil > code (stable) |
| D2 | Boost petit (-2 a +2), pas de valeurs extremes |
| D3 | Labels sobres : "Prioritaire selon votre profil", "Moins prioritaire selon votre profil" |
| D4 | Fiabilite par obligation, pas globale |
| D5 | Matrice pertinence avec 3 niveaux : high, medium, check_context |

---

## 5. REGLES METIER CORRIGEES

### R1 — Decret Tertiaire x q_surface_seuil

| Reponse | Tag | Boost | Fiabilite |
|---------|-----|-------|-----------|
| oui_majorite | Prioritaire selon votre profil (vert) | +2 | Declare |
| oui_certains | Applicable sur une partie du perimetre (bleu) | +1 | Declare |
| non | Moins prioritaire selon votre profil (gris) | -2 | Declare |
| ne_sait_pas | A qualifier (orange) | 0 | A confirmer |
| (pas de reponse) | (rien) | 0 | (rien) |

### R2 — Pertinence par typologie

Matrices DT_RELEVANCE et BACS_RELEVANCE avec 3 niveaux :
- `high` : badge "Pertinent pour votre profil" visible
- `medium` : pas de badge
- `check_context` : pas de badge

### R3 — Fiabilite par obligation

| Etat | Condition | Badge |
|------|-----------|-------|
| Declare | L'obligation utilise une reponse utilisateur pertinente | Bleu |
| Detecte | Pas de reponse pertinente, donnees patrimoine | Gris |
| A confirmer | Reponse "ne_sait_pas" ou info insuffisante | Orange |

### R4 — Micro-texte explicatif

Sous le score : "Certaines obligations et priorites sont ajustees selon votre profil declare ou detecte."

### R5 — Tri des obligations

```
1. overdue first (JAMAIS override par profil)
2. statut metier : non_conforme > a_risque > a_qualifier > conforme (JAMAIS override)
3. boost profil DANS LE MEME GROUPE seulement
4. code alphabetique (stable)
```

---

## 6. FICHIERS MODIFIES

| Fichier | Action |
|---------|--------|
| `frontend/src/models/complianceProfileRules.js` | **CREE** — logique pure, garde-fous, matrices pertinence |
| `frontend/src/pages/ConformitePage.jsx` | MODIFIE — import, profileTags useMemo, tri corrige, texte explicatif, props |
| `frontend/src/pages/conformite-tabs/ObligationsTab.jsx` | MODIFIE — profileTags prop, profileEntry sur ObligationCard, tags + fiabilite |
| `frontend/src/__tests__/v14_questionnaire_conformite.test.js` | **CREE** — 20 tests source-guard |

---

## 7. CRITERES D'ACCEPTATION

| # | Critere | Statut |
|---|---------|--------|
| CA1 | q_surface_seuil=non : DT deprioritise DANS son groupe, pas en absolu | **FAIT** |
| CA2 | q_surface_seuil=oui_majorite : tag vert "Prioritaire selon votre profil" | **FAIT** |
| CA3 | q_surface_seuil=ne_sait_pas : tag orange "A qualifier" | **FAIT** |
| CA4 | Micro-texte explicatif visible sous le score | **FAIT** |
| CA5 | Badge "Pertinent" uniquement pour cas high | **FAIT** |
| CA6 | Badge fiabilite depend de la source reellement utilisee | **FAIT** |
| CA7 | Sans profil : affichage identique V1.3 | **FAIT** |
| CA8 | Filtres et recherche preserves | **FAIT** |
| CA9 | Tri overdue > statut > boost > code | **FAIT** |
| CA10 | Tous les tests passent | **FAIT** (5599/5599) |

---

## 8. CAS DE TEST MANUELS

| # | Scenario | Resultat attendu |
|---|----------|------------------|
| T1 | Tertiaire prive, q_surface=oui_majorite | DT: tag vert + "Pertinent" + "Declare" |
| T2 | q_surface=oui_certains | DT: tag bleu "Applicable sur une partie" + "Declare" |
| T3 | q_surface=non | DT: tag gris "Moins prioritaire" + deprioritise dans son groupe |
| T4 | q_surface=ne_sait_pas | DT: tag orange "A qualifier" + "A confirmer" |
| T5 | Sans reponse | Aucun tag, affichage V1.3 |
| T6 | Industrie | DT: pas de badge "Pertinent" (check_context) |
| T7 | Bailleur/copro | DT et BACS: pas de badge "Pertinent" |
| T8 | Filtre par statut | Tags visibles sur resultats filtres |
| T9 | Recherche texte | Tags preserves |
| T10 | DT non-conforme + BACS conforme | DT reste au-dessus meme si boost negatif |

---

## 9. TOP 5 ACTIONS

| # | Action | Effort | Statut |
|---|--------|--------|--------|
| 1 | Creer complianceProfileRules.js | 0.5j | **FAIT** |
| 2 | Modifier ConformitePage.jsx (tri + texte + props) | 0.5j | **FAIT** |
| 3 | Modifier ObligationsTab.jsx (tags + fiabilite) | 0.5j | **FAIT** |
| 4 | Tests source-guard V1.4 | 0.5j | **FAIT** |
| 5 | Validation (lint + tests + audit Playwright) | 0.5j | **FAIT** |

---

## 10. PROCHAINES ETAPES

| # | Action | Priorite |
|---|--------|----------|
| 1 | Commit + push V1.4 | P0 |
| 2 | Ajouter q_gtb → impact sur carte BACS | P1 |
| 3 | Ajouter q_operat → impact sur carte DT (declaration OPERAT) | P1 |
| 4 | Export PDF dossier conformite avec tags profil | P2 |
| 5 | Connecter q_surface_seuil au filtrage backend (masquer DT si < 1000m2) | P2 |
