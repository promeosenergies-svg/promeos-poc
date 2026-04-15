# SPRINT V1.6 — Credibilite Demo : 5 Corrections P1

**Date** : 2026-03-14
**Scope** : Corriger les 5 irritants les plus visibles en demonstration
**Prerequis** : V1.5 validee (5 608/5 608 tests, 0 erreurs lint)
**Doctrine** : Sprint court, maitrise, demontrable — pas de refonte lourde

---

## 1. RESUME EXECUTIF

La V1.5 a consolide le lien questionnaire → conformite (q_surface_seuil, q_gtb, q_operat). Le produit fonctionne, mais 5 irritants P1 erosent la credibilite en demo. Ce sprint corrige uniquement ce qui fait perdre confiance quand un prospect regarde le cockpit et la conformite.

**Pas de nouvelle feature. Pas de refonte backend. Pas de cosmétique sans effet produit.**

---

## 2. FAITS

| # | Fait | Source |
|---|------|--------|
| F1 | Le cockpit affiche "54 / 100" (score pondere backend : DT 45% + BACS 30% + APER 25%) ET "71% conformes" (ratio brut sites conformes / total) | `dashboardEssentials.js:455` vs `ModuleLaunchers.jsx:31` |
| F2 | `WatchlistCard` n'a pas de prop `loading` — affiche "Tout va bien" des que `watchlist === []`, y compris pendant le chargement | `WatchlistCard.jsx:94-111` |
| F3 | ObligationsTab affiche "23 constats" (count total) mais filtre la liste sur `status === 'NOK' \|\| 'UNKNOWN'` — seuls 3 sont rendus | `ObligationsTab.jsx:735` vs `:739` |
| F4 | OPERAT "0 anomalies / 0 declares" = seed data absence — aucun EFA seede pour le scope | `gen_tertiaire.py`, `TertiaireDashboardPage.jsx:146` |
| F5 | Monitoring "Non detecte" = `totalWasteEur === 0` car seuils seed non atteints + `weekend_anomaly` sans `estimated_impact_eur` | `MonitoringPage.jsx:584`, `gen_monitoring.py:254` |
| F6 | "85% factures importees" = valeur calculee correctement (`covered/total`), pas hardcodee | `BillingPage.jsx:477`, `billing_coverage.py` |
| F7 | Patrimoine badges incoherents = 3 scores independants (`statut_conformite` snapshot, `anomalies_count` absent de l'API, `DataQualityBadge` separe) | `patrimoine.py:1340`, `Patrimoine.jsx:1460` |

---

## 3. HYPOTHESES

| # | Hypothese |
|---|-----------|
| H1 | Le score "71% conformes" dans ModuleLaunchers cree une contradiction percue avec "54/100" — un prospect en demo y verra une incoherence |
| H2 | "Tout va bien" pendant le chargement donne l'impression d'un produit qui ment ou qui ne fonctionne pas |
| H3 | "23 constats / 3 visibles" donne l'impression d'un bug (ou sont passes les 20 autres ?) |
| H4 | Les issues seed data (OPERAT, monitoring) sont corrigeables en ajustant le seed generator sans toucher au front |
| H5 | Le fix patrimoine (#7) est trop complexe pour ce sprint (3 scores independants a reconcilier) |

---

## 4. DECISIONS

### Retenues (5 fixes)

| # | Issue | Pourquoi retenue |
|---|-------|-----------------|
| **V1.6-1** | Cockpit 54/100 vs 71% | Impact max : premiere chose vue en demo. Fix front-only, risque faible |
| **V1.6-2** | "Tout va bien" + spinner | Impact max : message trompeur, erosion de confiance immediate. Fix front-only, 15 lignes |
| **V1.6-3** | 23 constats / 3 visibles | Impact fort sur conformite (page critique en demo). Fix front-only, 1 ligne |
| **V1.6-4** | OPERAT 0/0 | Fix seed data + garde-fou frontend. Credibilite tertiaire |
| **V1.6-5** | Monitoring "Non detecte" | Fix seed data. Credibilite monitoring |

### Repoussees

| # | Issue | Pourquoi repoussee |
|---|-------|--------------------|
| #6 | "85% factures importees" | Pas un bug — valeur calculee correctement. Ameliorer le label serait cosmetique |
| #7 | Patrimoine score/badge | Trop complexe — necessite reconciliation de 3 sources de donnees independantes. Sprint dedie V1.7 |

---

## 5. PLAN D'IMPLEMENTATION PAR FIX

### V1.6-1 — Unifier les metriques cockpit

**Probleme exact** : Le cockpit affiche deux metriques de conformite differentes cote a cote. "54 / 100" dans le KPI principal (score pondere multi-reglementation) et "71% conformes" dans le launcher Operations (ratio brut sites conformes / total). Un prospect percoit une incoherence.

**Cause probable** : `ModuleLaunchers.jsx` ligne 31 calcule `Math.round((kpis.conformes / kpis.total) * 100)` independamment du score backend `kpis.compliance_score`.

**Correction cible** : Dans `ModuleLaunchers.jsx`, utiliser `kpis.compliance_score` quand disponible. Reformuler le label pour lever l'ambiguite :
- Si `compliance_score` disponible : afficher `XX / 100` (meme format que le KPI principal)
- Sinon fallback : afficher `X / Y sites conformes` (label explicite, pas de pourcentage)

**Fichiers a modifier** :
- `frontend/src/pages/cockpit/ModuleLaunchers.jsx` — ligne 31

**Snippet propose** :
```jsx
// Avant
metric: kpis.total > 0
  ? `${formatPercentFR(Math.round((kpis.conformes / kpis.total) * 100))} conformes`
  : null,

// Apres
metric: kpis.compliance_score != null
  ? `${Math.round(kpis.compliance_score)} / 100`
  : kpis.total > 0
    ? `${kpis.conformes} / ${kpis.total} sites conformes`
    : null,
```

**Risque** : Faible — affichage uniquement, pas de logique metier touchee.

**Test demo** : Ouvrir le cockpit → verifier que le launcher Operations affiche le meme score que le KPI Conformite.

---

### V1.6-2 — Supprimer "Tout va bien" pendant le chargement

**Probleme exact** : `WatchlistCard` affiche "Tout va bien" et un bouton "Importer des donnees" avant meme que les donnees ne soient chargees. Un prospect en demo voit "Tout va bien" + un spinner ailleurs = contradiction.

**Cause probable** : Le composant n'a pas de prop `loading`. Quand `watchlist === []` (pendant le fetch), il affiche directement l'empty state "Tout va bien".

**Correction cible** : Ajouter prop `loading` a `WatchlistCard`. Afficher un skeleton/spinner pendant le chargement. Passer `sitesLoading` depuis `Cockpit.jsx`.

**Fichiers a modifier** :
- `frontend/src/pages/cockpit/WatchlistCard.jsx` — signature + empty state
- `frontend/src/pages/Cockpit.jsx` — passer `loading={sitesLoading}`

**Snippet propose** :

WatchlistCard.jsx :
```jsx
// Signature
export default function WatchlistCard({
  watchlist = [],
  consistency = { ok: true, issues: [] },
  loading = false,  // NEW
  onNavigate,
})

// Dans le JSX, avant l'empty state "Tout va bien"
{watchlist.length > 0 ? (
  <ul>...</ul>
) : loading ? (
  <div className="flex items-center justify-center py-8 text-gray-400">
    <Loader2 size={18} className="animate-spin mr-2" />
    <span className="text-sm">Analyse en cours...</span>
  </div>
) : (
  /* Empty state — all good (existant) */
)}
```

Cockpit.jsx :
```jsx
<WatchlistCard
  watchlist={watchlist}
  consistency={consistency}
  loading={sitesLoading}   // NEW
  onNavigate={navigate}
/>
```

**Risque** : Faible — ajout d'un etat intermediaire, pas de logique metier touchee.

**Test demo** : Hard-refresh cockpit → verifier que les cartes montrent un spinner/skeleton, JAMAIS "Tout va bien" avant resolution des donnees.

---

### V1.6-3 — Corriger le compteur de constats conformite

**Probleme exact** : Le header d'une obligation depliee affiche "Constats par site (23)" mais seuls 3 items sont rendus (filtre `NOK || UNKNOWN`). Le prospect pense que le produit a un bug.

**Cause probable** : `ObligationsTab.jsx` ligne 735 affiche `obligation.findings.length` (count total toutes statuts confondus) mais la liste rendue en ligne 739 filtre sur `f.status === 'NOK' || f.status === 'UNKNOWN'`.

**Correction cible** : Afficher un compteur coherent avec ce qui est visible. Format propose : "X non conformes / Y constats" pour rester transparent.

**Fichiers a modifier** :
- `frontend/src/pages/conformite-tabs/ObligationsTab.jsx` — ligne 735

**Snippet propose** :
```jsx
// Avant
Constats par site ({obligation.findings.length})

// Apres
const nonConformeFindings = obligation.findings.filter(
  (f) => f.status === 'NOK' || f.status === 'UNKNOWN'
);
// ...
Constats par site ({nonConformeFindings.length} non conforme{nonConformeFindings.length !== 1 ? 's' : ''} / {obligation.findings.length})
```

**Risque** : Tres faible — 1 ligne de template.

**Test demo** : Ouvrir conformite → deplier une obligation → verifier que le compteur correspond aux lignes visibles.

---

### V1.6-4 — Corriger seed OPERAT / Decret Tertiaire

**Probleme exact** : La page tertiaire affiche "0 anomalies / 0 declares" en demo. Aucun EFA n'est seede pour le scope actuel.

**Cause probable** : Le seed `gen_tertiaire.py` ne genere pas d'EFA pour les sites du pack helios S, ou les sites ne sont pas flagges comme tertiaire-eligibles.

**Correction cible** :
1. Dans `gen_tertiaire.py` : garantir au minimum 2-3 EFA avec declarations et quelques anomalies pour le pack demo
2. Dans `TertiaireDashboardPage.jsx` : ameliorer l'empty state pour expliquer "Aucun EFA detecte — importez vos declarations OPERAT" au lieu de montrer des 0 muets

**Fichiers a modifier** :
- `backend/services/demo_seed/gen_tertiaire.py` — generation EFA
- `frontend/src/pages/tertiaire/TertiaireDashboardPage.jsx` — empty state

**Risque** : Moyen — touche le seed, verifier non-regression sur les tests seed existants.

**Test demo** : Reseed (`python -m services.demo_seed --pack helios --size S --reset`) → ouvrir tertiaire → verifier EFA > 0 et declarations visibles.

---

### V1.6-5 — Corriger seed monitoring "Non detecte"

**Probleme exact** : Le KPI "Gaspillage estime" affiche "Non detecte" en demo. Aucun montant EUR n'est calcule.

**Cause probable** :
1. `weekend_anomaly` seedee sans `estimated_impact_eur` (`gen_monitoring.py` lignes 254-266)
2. Le seuil `off_hours` est a `> 0.4` — trop strict pour les sites demo

**Correction cible** :
1. Ajouter `estimated_impact_eur` a `weekend_anomaly` dans le seed :
   ```python
   estimated_impact_eur=round(kpis.get("total_kwh", 0) * we_ratio * 0.1 * 0.15, 0)
   ```
2. Abaisser le seuil `off_hours` de `0.4` a `0.3`

**Fichiers a modifier** :
- `backend/services/demo_seed/gen_monitoring.py` — lignes 233 et 254-266

**Risque** : Faible — seed data uniquement, pas de logique front touchee.

**Test demo** : Reseed → ouvrir monitoring → verifier que "Gaspillage estime" affiche un montant > 0 EUR/an.

---

## 6. FICHIERS A MODIFIER

| Fichier | Fix | Action |
|---------|-----|--------|
| `frontend/src/pages/cockpit/ModuleLaunchers.jsx` | V1.6-1 | Utiliser `kpis.compliance_score` au lieu du ratio brut |
| `frontend/src/pages/cockpit/WatchlistCard.jsx` | V1.6-2 | Ajouter prop `loading`, etat intermediaire spinner |
| `frontend/src/pages/Cockpit.jsx` | V1.6-2 | Passer `loading={sitesLoading}` a WatchlistCard |
| `frontend/src/pages/conformite-tabs/ObligationsTab.jsx` | V1.6-3 | Aligner compteur constats sur filtre |
| `backend/services/demo_seed/gen_tertiaire.py` | V1.6-4 | Garantir EFA + declarations en demo |
| `frontend/src/pages/tertiaire/TertiaireDashboardPage.jsx` | V1.6-4 | Empty state explicatif |
| `backend/services/demo_seed/gen_monitoring.py` | V1.6-5 | Ajouter impact EUR + baisser seuil off_hours |

---

## 7. CRITERES D'ACCEPTATION

| # | Fix | Critere | Statut |
|---|-----|---------|--------|
| CA1 | V1.6-1 | Le launcher Operations affiche `XX / 100` identique au KPI Conformite | A FAIRE |
| CA2 | V1.6-2 | En hard-refresh, WatchlistCard affiche un spinner, JAMAIS "Tout va bien" avant resolution | A FAIRE |
| CA3 | V1.6-3 | Le compteur "Constats" = nombre de lignes visibles dans la liste | A FAIRE |
| CA4 | V1.6-4 | Page tertiaire montre au moins 2 EFA avec anomalies > 0 apres reseed | A FAIRE |
| CA5 | V1.6-5 | KPI "Gaspillage estime" affiche un montant > 0 EUR apres reseed | A FAIRE |
| CA6 | GARDE-FOU | Tous les tests passent (5 608+) | A FAIRE |
| CA7 | GARDE-FOU | Logique V1.5 (questionnaire, tri, fiabilite, boost clamp) intacte | A FAIRE |

---

## 8. CAS DE TEST MANUELS

| # | Scenario | Resultat attendu |
|---|----------|-----------------|
| T1 | Ouvrir cockpit, comparer KPI Conformite et launcher Operations | Meme score XX / 100 |
| T2 | Hard-refresh cockpit (Ctrl+Shift+R) | WatchlistCard montre spinner, puis contenu ou "Tout va bien" |
| T3 | Ouvrir conformite → deplier DT → lire compteur | "X non conformes / Y constats" avec X = lignes visibles |
| T4 | Ouvrir conformite tertiaire apres reseed | EFA > 0, declarations > 0, anomalies > 0 |
| T5 | Ouvrir monitoring apres reseed | "Gaspillage estime : XXX EUR/an" (pas "Non detecte") |
| T6 | Ouvrir conformite avec profil questionnaire rempli | Tags V1.5 toujours presents, tri overdue > statut > boost intact |
| T7 | `cd frontend && npx vitest run` | 5 608+ passed, 6 skipped (CEE), 0 failed |

---

## 9. GARDE-FOUS — PROTECTIONS EXPLICITES

| Element protege | Fichier | Verification |
|----------------|---------|-------------|
| Logique questionnaire V1.5 | `complianceProfileRules.js` | NE PAS TOUCHER — aucune modification |
| Tri conformite V1.4/V1.5 | `ConformitePage.jsx` (sortedObligations) | NE PAS MODIFIER le useMemo de tri |
| Badges de fiabilite | `RELIABILITY_CONFIG`, `TAG_COLORS` | NE PAS MODIFIER |
| Boost clamp [-3, +3] | `complianceProfileRules.js:233` | NE PAS MODIFIER |
| Route /energy-copilot redirect | `App.jsx` | NE PAS TOUCHER |
| q_cee hidden | `segmentation_service.py` | NE PAS TOUCHER |
| Tests V1.5 (29 tests) | `v14_questionnaire_conformite.test.js` | Doivent rester ALL PASSED |
| Corrections V1.5 Top 30 | `StatusPage`, `MonitoringPage` version, `ProfileHeatmapTab` FR | NE PAS REVERTER |

---

## 10. RISQUES / REGRESSIONS A EVITER

| Risque | Mitigation |
|--------|-----------|
| V1.6-1 : `compliance_score` null au premier render | Fallback explicite `X / Y sites conformes` (pas de pourcentage ambigu) |
| V1.6-2 : `sitesLoading` ne couvre pas `complianceApi` | Accepter — le spinner WatchlistCard couvre le cas principal. Amelioration future possible |
| V1.6-3 : Le total 23 disparait du header | Non — on garde les deux : "X non conformes / Y constats" |
| V1.6-4 : Seed casse d'autres pages | Verifier que le reseed ne modifie pas les metriques billing/patrimoine |
| V1.6-5 : Impact EUR trop eleve en demo | Calibrer avec des valeurs realistes (ex: 2 000 - 8 000 EUR/an) |

---

## 11. TOP 5 ACTIONS

| # | Action | Effort | Owner | Deadline |
|---|--------|--------|-------|----------|
| 1 | V1.6-1 : Unifier metriques cockpit (ModuleLaunchers.jsx) | 30 min | Dev | J+0 |
| 2 | V1.6-2 : Loading state WatchlistCard + Cockpit.jsx | 30 min | Dev | J+0 |
| 3 | V1.6-3 : Compteur constats ObligationsTab.jsx | 15 min | Dev | J+0 |
| 4 | V1.6-4 : Seed OPERAT gen_tertiaire.py + empty state | 1h | Dev | J+1 |
| 5 | V1.6-5 : Seed monitoring gen_monitoring.py impact EUR | 30 min | Dev | J+1 |

**Total estime : ~3h de dev, 1h de test manuel, demontrable en J+1.**

---

## 12. BILAN CORRECTIONS ANTERIEURES (V1.5 Top 30)

Pour memoire, 11 corrections ont ete appliquees dans cette session (hors V1.6) :

| # | Issue | Fix | Fichier |
|---|-------|-----|---------|
| P1 #4 | Score format "54/100" → "54 / 100" | Espacement lisible | `dashboardEssentials.js` |
| P1 #5 | "Synchroniser les donnees" trompeur | → "Importer des donnees" | `WatchlistCard.jsx` |
| P1 #15 | Conformite vide string non detectee | Check `!== ''` ajoute | `ActivationPage.jsx` |
| P1 #17 | EUR format variable (toLocaleString) | → `fmtEur()` partout | `ActionsPage.jsx` |
| P1 #19 | Y-axis flat chart trop serre | Padding near-flat 10% avg | `ExplorerChart.jsx` |
| P2 #18 | Frise reglementaire illisible | `text-[9px]` → `text-[11px]`, `text-[10px]` → `text-xs` | `RegulatoryTimeline.jsx` |
| P2 #23 | Wizard 8 etapes sans progression | Barre de progression visuelle ajoutee | `PurchaseAssistantPage.jsx` |
| P2 #24 | Contrats expirants sans CTA | Lien "Voir le radar renouvellements →" | `Patrimoine.jsx` |
| P2 #26 | Onboarding 100% sans auto-dismiss | Redirect cockpit apres 3s | `OnboardingPage.jsx` |
| P2 #27 | Auth requise sans moyen en demo | Message "donnees simulees" | `ConnectorsPage.jsx` |
| P2 #30 | Recherche sans resultats muette | Suggestions affichees | `CommandPalette.jsx` |

**Tests : 5 608 / 5 608 ALL PASSED (6 skipped CEE) — 0 erreurs lint.**
