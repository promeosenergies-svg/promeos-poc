# Audit Sprint 3 — 3 follow-ups Patrimoine

> Date : 2026-03-15
> Objectif : Cadrage precis avant implementation
> Statut : Audit termine, pret a coder

---

## FAITS

### Follow-up 1 — Contrat sans end_date = actif

**Fichier :** `backend/routes/patrimoine.py`
**Fonction :** `_compute_site_completeness` (lignes 2530-2573)
**Ligne exacte :** 2557

```python
nb_ct = (
    db.query(EnergyContract)
    .filter(
        EnergyContract.site_id == site.id,
        EnergyContract.end_date >= today,     # ← PROBLEME : NULL exclus
    )
    .count()
)
checks["contrat_actif"] = nb_ct > 0
```

**Probleme :** Un contrat avec `end_date = NULL` (pas de date de fin = contrat en cours) n'est pas compte comme actif.

**Fix :** `(EnergyContract.end_date >= today) | (EnergyContract.end_date.is_(None))`

**Effort :** 1 ligne a modifier.

---

### Follow-up 2 — window.location.reload()

**Fichier :** `frontend/src/pages/Patrimoine.jsx`
**3 occurrences :**

| Ligne | Contexte | Declencheur |
|-------|----------|-------------|
| 1578 | `onSiteUpdated` dans SiteDrawerContent | Apres edit site dans le drawer |
| 1588 | `onSuccess` dans QuickCreateSite | Apres creation rapide |
| 1595 | `onSuccess` dans SiteCreationWizard | Apres creation avancee |

**Mecanisme de remplacement deja existant :**

```javascript
// ScopeContext.jsx ligne 98
const refreshSites = useCallback(() => {
  setFetchTrigger((t) => t + 1);
}, []);

// Expose via useScope() ligne 321
refreshSites, // V19: trigger re-fetch without full page reload
```

**Fix :**
1. Ajouter `refreshSites` au destructuring de `useScope()` (ligne 154)
2. Remplacer les 3 `window.location.reload()` par `refreshSites()`

**Effort :** 4 lignes a modifier.

**Autres occurrences dans le frontend :**
- `ConsumptionExplorerPage.jsx:733` — retry error handler (hors perimetre)
- `TimeseriesPanel.jsx:299` — retry error handler (hors perimetre)

---

### Follow-up 3 — Import UX simplifie

**Fichier :** `frontend/src/components/PatrimoineWizard.jsx`
**4 modes actuels (lignes 54-87) :**

| Mode | Label | Temps | Etat reel |
|------|-------|-------|-----------|
| `express` | Express | 2 min | Fonctionnel |
| `import` | Import complet | 5 min | Fonctionnel |
| `assiste` | Assiste | 10 min | Non implemente (IA) |
| `demo` | Demo | 10 sec | Fonctionnel |

**UI actuelle (lignes 407-451) :** Grille 2x2 de boutons, l'utilisateur choisit un mode avant d'uploader.

**Points d'entree dans Patrimoine.jsx :**
- Ligne 693 : bouton "Importer" (toolbar)
- Ligne 706 : CTA "Importer mon patrimoine" (empty state)
- Ligne 714 : bouton "Demo" (empty state) — ouvre le meme wizard

**Logique apres selection (ligne 286-291) :**
- Demo → execute immediatement `doDemo()`
- Autres → avance a Step 1 (Upload)

**Simplification recommandee :**
1. Retirer "Assiste" du menu (non implemente)
2. Sortir "Demo" du wizard → bouton separe (deja fait dans empty state Sprint 1, mais le wizard le propose encore)
3. Fusionner Express et Import complet en 1 seule entree : upload direct, auto-detection QA

---

## HYPOTHESES

| # | Hypothese | Confiance |
|---|-----------|-----------|
| H1 | Un contrat sans end_date est un contrat en cours (tacite reconduction) | Haute |
| H2 | `refreshSites()` du ScopeContext recharge les sites sans flash blanc | Haute |
| H3 | Retirer "Assiste" et "Demo" du wizard import ne casse aucun parcours actif | Haute |
| H4 | Fusionner Express et Import complet est faisable sans refonte backend | Moyenne |

---

## DECISIONS RECOMMANDEES

| # | Decision | Justification |
|---|----------|---------------|
| D1 | Contrat sans end_date = actif | Convention B2B France : pas d'echeance = contrat en cours |
| D2 | Remplacer les 3 `window.location.reload()` par `refreshSites()` | Mecanisme deja pret dans ScopeContext |
| D3 | Retirer "Assiste" du wizard import (pas implemente) | Evite la confusion |
| D4 | Sortir "Demo" du wizard import (deja dans empty state) | Simplifie le choix a 2 modes |
| D5 | Fusionner Express + Import complet en 1 seule entree : l'utilisateur uploade, le systeme detecte la qualite | Supprime le choix initial inutile |

---

## FICHIERS A MODIFIER

### Follow-up 1 (contrat actif)

| Fichier | Ligne | Modification | Effort |
|---------|-------|-------------|--------|
| `backend/routes/patrimoine.py` | 2557 | Ajouter `\| end_date.is_(None)` | S |

### Follow-up 2 (refresh cible)

| Fichier | Ligne(s) | Modification | Effort |
|---------|----------|-------------|--------|
| `frontend/src/pages/Patrimoine.jsx` | 154 | Ajouter `refreshSites` au destructuring `useScope()` | S |
| `frontend/src/pages/Patrimoine.jsx` | 1578, 1588, 1595 | `window.location.reload()` → `refreshSites()` | S |

### Follow-up 3 (import simplifie)

| Fichier | Ligne(s) | Modification | Effort |
|---------|----------|-------------|--------|
| `frontend/src/components/PatrimoineWizard.jsx` | 54-87 | Retirer modes `assiste` et `demo` du tableau MODES | S |
| `frontend/src/components/PatrimoineWizard.jsx` | 286-291 | Adapter `handleNext()` — plus de cas `demo` dans le wizard | S |
| `frontend/src/components/PatrimoineWizard.jsx` | 407-451 | Adapter l'UI — 2 modes au lieu de 4, ou upload direct sans choix | M |
| `frontend/src/pages/Patrimoine.jsx` | 714 | Le bouton Demo dans l'empty state ouvre le seed directement (pas le wizard) | S |

### A ne pas toucher

| Fichier | Raison |
|---------|--------|
| `QuickCreateSite.jsx` | Sprint 1 — proteger |
| `DrawerEditSite.jsx`, `DrawerAddCompteur.jsx`, `DrawerAddContrat.jsx` | Sprint 2 — proteger |
| Backend import/staging | Pas de refonte backend import |

---

## RISQUES

| # | Risque | Severite | Mitigation |
|---|--------|----------|-----------|
| R1 | `refreshSites()` ne recharge pas les KPIs/heatmap (seulement les sites) | Moyenne | Verifier si registreKpis depend de scopedSites ou d'un fetch separe |
| R2 | Retirer Demo du wizard casse le bouton "Demo" de l'empty state | Faible | Le bouton appelle directement le seed, pas le wizard |
| R3 | Fusionner les 2 modes import change le comportement pour les utilisateurs existants | Faible | POC — peu d'utilisateurs existants |

---

## PLAN DE PATCH SPRINT 3

| Step | Patch | Fichier(s) | Effort | Impact |
|------|-------|-----------|--------|--------|
| **S3-1** | Contrat sans end_date = actif | `patrimoine.py` L2557 | S | Completude plus juste |
| **S3-2** | Refresh cible (3 reload → refreshSites) | `Patrimoine.jsx` L154, 1578, 1588, 1595 | S | UX fluide, pas de flash blanc |
| **S3-3** | Import simplifie (retirer Assiste + Demo du wizard) | `PatrimoineWizard.jsx` | M | Choix clair, moins de confusion |
| **S3-4** | Validation finale Sprint 3 | Tests + build + push | S | Stabilisation |

**Ordre recommande :** S3-1 → S3-2 → S3-3 → S3-4
