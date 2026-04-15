# FIX PROMEOS — ÉTAPE 3B : PURCHASE ASSISTANT TRANSPARENCE

> **Date** : 2026-03-23
> **Référence** : `VERIFY_PROMEOS_ETAPE_03_BILL_INTELLIGENCE_ACHAT_2026-03-23.md` (P1-1 résiduel)
> **Scope** : Rendre visible la note de computation source dans PurchaseAssistant
> **Contrainte** : Structures backend (4 scénarios discrets) et client (corridor Monte Carlo) incompatibles — pas de remplacement du moteur

---

## 1. Résumé exécutif

Le PurchaseAssistant affiche maintenant un **bandeau explicite** sur 2 écrans (Résultats et Décision) indiquant que les calculs sont des **estimations locales** (navigateur), avec un lien vers le simulateur serveur. Le flag `USE_BACKEND_PRICING = true` n'est pas câblé dans `runEngine()` car les structures de sortie sont fondamentalement incompatibles (corridor Monte Carlo vs scénarios discrets). L'approche retenue est la **transparence honnête**.

---

## 2. Modifications réalisées

### 2.1 Bandeau dans StepResults (step 6)

**Ajout** : Bandeau ambre "Estimation locale" entre le titre et les KPIs, avec :
- Icône `Info` (lucide, déjà importé)
- Texte : "Estimation locale — Résultat indicatif calculé dans votre navigateur."
- Lien : "Simulateur serveur" → `/achat-energie`
- `data-testid="computation-source-banner"`
- Conditionnel : affiché uniquement si `engineOutput._computation_source === 'client_engine'`

### 2.2 Bandeau dans StepDecision (step 8)

**Ajout** : Bandeau ambre "Estimation locale" entre le titre et le badge de confiance, avec :
- Texte : "Les montants ci-dessous sont indicatifs (calcul navigateur)."
- Lien : "Valider avec le simulateur serveur"
- `data-testid="decision-computation-source-banner"`

### 2.3 Tests de transparence

**Ajout** : 4 tests dans `purchaseP1Hardening.test.js` :
- `StepResults renders computation-source-banner for client engine`
- `StepDecision renders decision-computation-source-banner`
- `handleCompute sets _computation_source and _computation_note on output`
- `links to server simulator /achat-energie` (≥ 2 liens)

---

## 3. Fichiers touchés

| Fichier | Modification |
| --- | --- |
| `frontend/src/pages/PurchaseAssistantPage.jsx` | 2 bandeaux ajoutés (StepResults + StepDecision) |
| `frontend/src/pages/__tests__/purchaseP1Hardening.test.js` | 4 tests ajoutés |

---

## 4. Tests ajoutés

| Test | Vérifie |
| --- | --- |
| `computation-source-banner` dans StepResults | Bandeau visible avec `_computation_source`, texte "Estimation locale" |
| `decision-computation-source-banner` dans StepDecision | Bandeau visible avec CTA "Valider avec le simulateur serveur" |
| `_computation_source` et `_computation_note` dans handleCompute | Metadata définie sur output |
| Liens `/achat-energie` (≥ 2) | CTA vers simulateur serveur dans les 2 steps |

**Résultat** : 23/23 tests passent.

---

## 5. Risques de régression

| Risque | Probabilité | Mitigation |
| --- | --- | --- |
| Bandeau ambre gêne visuellement en démo | Faible | Discret (text-xs, amber-50), informatif pas alarmiste |
| `Info` icon manquant | Nul | Déjà importé (ligne 41) |
| Bandeau affiché même quand pas pertinent | Nul | Conditionnel sur `_computation_source === 'client_engine'` |

---

## 6. Points non traités (volontairement)

| Point | Raison |
| --- | --- |
| Câblage de `USE_BACKEND_PRICING` dans `runEngine()` | Structures incompatibles (corridor MC vs scénarios discrets). Scope L, pas S |
| Remplacement de `runEngine()` par appel API | Même raison — nécessite refonte du wizard + nouveau endpoint backend retournant un corridor |
| Fallback dégradé si API échoue | Le wizard ne fait pas d'appel API — tout est local. Le fallback n'a pas de sens sans appel API |
| Alignement wording serveur/local conditionnel | Pas pertinent tant que le wizard n'appelle pas le serveur |

---

## 7. Definition of Done

| Critère | Statut |
| --- | --- |
| `_computation_note` visible dans StepResults | ✅ Bandeau ambre avec `data-testid` |
| `_computation_note` visible dans StepDecision | ✅ Bandeau ambre avec CTA serveur |
| CTA vers simulateur serveur | ✅ Lien `/achat-energie` dans les 2 bandeaux |
| Tests prouvant l'affichage | ✅ 4 tests passent (23/23 total) |
| Aucun résultat local présenté comme serveur | ✅ Bandeau explicite "Estimation locale" |
| `USE_BACKEND_PRICING` câblé | NON TRAITÉ (scope L, documenté) |

---

*Fix 3B réalisé le 2026-03-23. P1-1 résolu (transparence). P1-2 (câblage flag) reste hors scope (structures incompatibles).*
